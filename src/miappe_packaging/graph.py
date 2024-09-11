from __future__ import annotations

import datetime
import decimal
import uuid
from typing import TYPE_CHECKING, Any, overload
from typing import Literal as Literal

import msgspec
from rdflib import Graph, URIRef
from rdflib.extras.describer import Describer
from rdflib.graph import _ObjectType, _PredicateType
from rdflib.namespace import RDF

from src.miappe_packaging.exceptions import AnnotationError, MissingSchema
from src.miappe_packaging.json import dec_hook, enc_hook
from src.miappe_packaging.schema import FieldInfo, IDRef, Schema
from src.miappe_packaging.utils import get_key_or_attribute, make_ref, validate_schema

if TYPE_CHECKING:
    from miappe_packaging.struct import LinkedDataClass

__all__ = (
    "from_struct",
    "get_subjects",
    "sub_graph",
    "to_builtin",
    "to_struct",
    "update_attrs_from_stmt",
)


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


@overload
def get_subjects(graph: Graph) -> set[URIRef]: ...
@overload
def get_subjects(graph, *, identifier: URIRef | str) -> set[URIRef]: ...
@overload
def get_subjects(graph, *, schema: Schema) -> set[URIRef]: ...
@overload
def get_subjects(
    graph, *, identifier: URIRef | str | None = None, schema: Schema | None = None
) -> set[URIRef]: ...
def get_subjects(
    graph: Graph,
    *,
    identifier: URIRef | str | None = None,
    schema: Schema | None = None,
) -> set[URIRef]:
    """Get all subjects from a given graph.

    If identifier is provided, return the identifier if it is a subject of the graph. If schema is provided,
    return all identifiers whose RDF:type is the schema.__rdf_resource__. If both identifier and schema are
    return the identifier if the statement (identifier, RDF:type, schema.__rdf_resource__) is in the graph.
    If only graph is provided, return all subjects from the graph.

    Args:
        graph (Graph): source graph
        identifier (URIRef | str | None, optional): subject identifier. Defaults to None.
        schema (Schema | None, optional): schema. Defaults to None.

    Raises:
        ValueError: if given identifier is not in graph
        ValueError: if (identifier, RDF:type, schema.__rdf_resource__) is not in graph

    Returns:
        set[URIRef]: found subjects
    """
    if identifier:
        identifier = make_ref(identifier)
        if (identifier, None, None) not in graph:
            raise ValueError(f"Identifier: {identifier} not in graph")
        if (
            schema is not None
            and (identifier, RDF.type, schema.__rdf_resource__) not in graph
        ):
            raise ValueError(
                f"Object identified by id: {identifier} is not of type: {schema.__rdf_resource__} in graph"
            )
        return set([identifier])
    resource = schema.__rdf_resource__ if schema else None
    return set(
        [URIRef(item) for item in graph.subjects(predicate=RDF.type, object=resource)]
    )


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
    """Convert a LinkedDataClass instance to an rdflib Graph (set of rdf statements)

    Args:
        struct (LinkedDataClass): LinkedDataClass instance
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
    """Obtain a subgraph from a graph whose subjects are identifier

    Args:
        graph (Graph): parent graph
        identifier (URIRef | str): id of the subject

    Raises:
        ValueError: if the identifier is not a subject of the graph

    Returns:
        Graph: returned subgraph
    """
    identifier = make_ref(identifier)
    if (identifier, None, None) not in graph:
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
    id_pool = get_subjects(
        graph=graph,
        identifier=identifier,
        schema=schema,
    )
    # Convert to builtin
    result = []
    for item in id_pool:
        item_attrs = {"id": str(item)}
        stmts = graph.predicate_objects(item, unique=True)
        for ref, value in stmts:
            update_attrs_from_stmt(ref, value, item_attrs, schema)
        result.append(item_attrs)
    return msgspec.to_builtins(
        result,
        enc_hook=enc_hook,
        builtin_types=(
            bytes,
            bytearray,
            datetime.datetime,
            datetime.time,
            datetime.date,
            datetime.timedelta,
            uuid.UUID,
            decimal.Decimal,
        ),
    )


def update_attrs_from_stmt(
    pred: _PredicateType,
    value: _ObjectType,
    attrs: dict[str, Any],
    schema: Schema | None = None,
) -> dict[str, Any]:
    if pred == RDF.type:
        return
    if not schema:
        if pred in attrs:
            if not isinstance(attrs[pred], list):
                attrs[pred] = [attrs[pred]]
            attrs[pred].append(value)
        else:
            attrs[pred] = value
    else:
        pred = schema.ref_mapping[pred]
        if schema.attrs[pred].repeat:
            if pred in attrs:
                attrs[pred].append(value)
            else:
                attrs[pred] = [value]
        else:
            if pred in attrs:
                raise AnnotationError(
                    f"Field: {pred} not annotated with repeat, but receives collection like value"
                )
            attrs[pred] = value
    return attrs


def to_struct(
    graph: Graph,
    identifier: URIRef | str,
    model_cls: type[LinkedDataClass],
    schema: Schema | None = None,
) -> LinkedDataClass:
    """Extract a set of tuples whose subject is identifier and convert it to model_cls

    Args:
        graph (Graph): graph whose tuples contain identifier as a subject
        identifier (URIRef | str): ID of the entity of interest
        model_cls (type[LinkedDataClass]): model class - a subclass of LinkedDataClass (note different from a LinkedDataClass instance)
        schema (Schema | None, optional): model_cls schema. Defaults to None.

    Raises:
        ValueError: if the identifier is not in the graph

    Returns:
        LinkedDataClass: returned object
    """
    if not schema:
        schema = model_cls.__schema__
    data_kwargs = to_builtin(graph=graph, identifier=identifier, schema=schema)
    return msgspec.convert(
        data_kwargs[0], type=model_cls, dec_hook=dec_hook, strict=False
    )
