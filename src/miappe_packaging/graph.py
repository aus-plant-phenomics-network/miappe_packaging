from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload
from typing import Literal as Literal

import msgspec
from rdflib import Graph, URIRef
from rdflib.extras.describer import Describer
from rdflib.namespace import RDF

from src.miappe_packaging.exceptions import MissingSchema
from src.miappe_packaging.json import dec_hook, enc_hook
from src.miappe_packaging.schema import FieldInfo, IDRef, Schema
from src.miappe_packaging.utils import get_key_or_attribute, make_ref, validate_schema

if TYPE_CHECKING:
    from miappe_packaging.struct import LinkedDataClass


def _describer_add_value(describer: Describer, value: Any, info: FieldInfo) -> None:
    if value is not None:
        if hasattr(value, "__len__") and not isinstance(value, str):
            for item in value:
                _describer_add_value(describer, item, info)
        else:
            if isinstance(info.range, IDRef):
                describer.rel(info.ref, value)
            else:
                describer.value(info.ref, value, datatype=info.range)


def get_subjects(
    graph: Graph,
    identifier: URIRef | str | None = None,
    schema: Schema | None = None,
) -> set[URIRef]:
    id_pool = set()
    if identifier and not schema:
        id_pool.add(make_ref(identifier))
    elif not identifier and schema:
        id_pool.update(graph.subjects(RDF.type, schema.__rdf_resource__, unique=True))
    elif identifier and schema:
        if schema.__rdf_resource__ not in graph.objects(make_ref(identifier), RDF.type):
            raise ValueError(
                f"Object identified by id: {identifier} is not of type: {schema.__rdf_resource__} in graph"
            )
        id_pool.add(make_ref(identifier))
    else:
        id_pool.update(graph.subjects(predicate=RDF.type, unique=True))
    return id_pool


@overload
def from_struct(
    *,
    struct: Any,
    graph: Graph,
    schema: Schema | None = None,
) -> Graph: ...
@overload
def from_struct(
    *,
    struct: Any,
    schema: Schema | None = None,
    identifier: URIRef | str | None = None,
) -> Graph: ...
def from_struct(
    *,
    struct: Any,
    schema: Schema | None = None,
    graph: Graph | None = None,
    identifier: URIRef | str | None = None,
) -> Graph:
    """Convert a semantic object instance to an rdflib Graph (set of rdf statements)

    Args:
        struct (LinkedDataClass): semantic class instance
        schema (Schema | None, optional): schema for conversion. If not provided, will use the object __schema__.
        graph (Graph | None, optional): if provided, will use this graph to add rdf nodes.
        identifier (URIRef | str | None, optional): graph identifier. Will use a blank node value if not provided.

    Raises:
        MissingSchema: if struct has no attribute __schema__ and schema is not provided

    Returns:
        Graph: set of rdf tuples describing the struct object
    """
    if schema:
        validate_schema(struct, schema)
    else:
        if not hasattr(struct, "__schema__"):
            raise MissingSchema("A schema must be provided to convert struct to graph")
        schema = getattr(struct, "__schema__")
    if graph is None:
        graph = Graph(identifier=make_ref(identifier))
    instance_id = None
    # Extract ID
    if get_key_or_attribute("ID", struct) is not None:
        instance_id = get_key_or_attribute("ID", struct)
    elif get_key_or_attribute("id", struct) is not None:
        instance_id = get_key_or_attribute("id", struct)
    else:
        raise ValueError("Missing ID/id field in object in from_struct operation")
    describer = Describer(graph=graph, about=instance_id)
    describer.rdftype(schema.__rdf_resource__)
    for name, info in schema.name_mapping.items():
        value = get_key_or_attribute(name, struct, raise_error_if_missing=True)
        _describer_add_value(describer, value, info)
    return graph


def sub_graph(graph: Graph, identifier: URIRef | str) -> Graph:
    subjects = graph.subjects(RDF.type)
    identifier = make_ref(identifier)
    if identifier not in subjects:
        raise ValueError(f"Identifier {identifier} not present in graph")
    tuples = graph.predicate_objects(subject=identifier, unique=True)
    sub = Graph()
    for pred, obj in tuples:
        sub.add((identifier, pred, obj))
    return sub


@overload
def to_builtin(graph: Graph) -> list[dict[str, Any]]: ...
@overload
def to_builtin(graph: Graph, *, identifier: URIRef | str) -> list[dict[str, Any]]: ...
@overload
def to_builtin(
    graph: Graph, *, identifier: URIRef | str, schema: Schema
) -> list[dict[str, Any]]: ...
@overload
def to_builtin(graph: Graph, *, schema: Schema) -> list[dict[str, Any]]: ...
def to_builtin(
    graph: Graph,
    *,
    identifier: URIRef | str | None = None,
    schema: Schema | None = None,
) -> list[dict[str, Any]]:
    # Get subgraphs object ID
    id_pool = get_subjects(graph, identifier, schema)
    # Convert to builtin
    result = []
    for item in id_pool:
        item_attrs = {"id": str(item)}
        stmts = graph.predicate_objects(item, unique=True)
        for ref, value in stmts:
            if ref != RDF.type:
                if schema and ref in schema.attrs:
                    attr = schema.ref_mapping[ref]
                    if schema.attrs[attr].repeat:
                        if hasattr(value, "__len__") and not isinstance(value, str):
                            item_attrs[attr] = value
                        else:
                            item_attrs[attr] = [value]
                    else:
                        item_attrs[attr] = value
                else:
                    item_attrs[ref] = value
        result.append(item_attrs)
    return msgspec.to_builtins(result, enc_hook=enc_hook)


def to_struct(
    graph: Graph,
    identifier: URIRef | str,
    model_cls: type[LinkedDataClass],
    schema: Schema | None = None,
) -> LinkedDataClass:
    if not schema:
        schema = model_cls.__schema__
    data_kwargs = to_builtin(graph=graph, identifier=identifier, schema=schema)
    return msgspec.from_builtins(data_kwargs, type=model_cls, dec_hook=dec_hook)
