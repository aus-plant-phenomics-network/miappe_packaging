from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

import msgspec
from rdflib import Graph, IdentifiedNode, URIRef
from rdflib.extras.describer import Describer
from rdflib.namespace import RDF

from src.miappe_packaging.exceptions import MissingSchema
from src.miappe_packaging.json import enc_hook
from src.miappe_packaging.base import Schema, FieldInfo, IDRef
from src.miappe_packaging.utils import convert_to_ref, validate_schema

if TYPE_CHECKING:
    from src.miappe_packaging.base import Base


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
    identifier: IdentifiedNode | str | None = None,
) -> Graph: ...
def from_struct(
    *,
    struct: Any,
    schema: Schema | None = None,
    graph: Graph | None = None,
    identifier: IdentifiedNode | str | None = None,
) -> Graph:
    """Convert a semantic object instance to an rdflib Graph (set of rdf statements)

    Args:
        struct (Base): semantic class instance
        schema (Schema | None, optional): schema for conversion. If not provided, will use the object __schema__.
        graph (Graph | None, optional): if provided, will use this graph to add rdf nodes.
        identifier (IdentifiedNode | str | None, optional): graph identifier. Will use a blank node value if not provided.

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
        graph = Graph(identifier=convert_to_ref(identifier))
    describer = Describer(graph=graph, about=struct.ID)
    describer.rdftype(schema.__rdf_resource__)
    for name, info in schema.name_mapping.items():
        value = getattr(struct, name)
        _describer_add_value(describer, value, info)
    return graph


def sub_graph(graph: Graph, identifier: IdentifiedNode | str) -> Graph:
    tuples = graph.predicate_objects(subject=identifier, unique=True)
    sub = Graph()
    for pred, obj in tuples:
        sub.add((identifier, pred, obj))
    return sub


def to_struct(
    graph: Graph,
    identifier: IdentifiedNode | str,
    model_cls: type[Base],
    schema: Schema | None = None,
) -> Base:
    if not schema:
        schema = model_cls.__schema__

    stmts = graph.predicate_objects(subject=URIRef(identifier))
    kwargs = {}
    for ref, value in stmts:
        if ref != RDF.type:
            attr = schema.ref_mapping[ref]
            kwargs[attr] = value
    data_kwargs = msgspec.to_builtins(kwargs, enc_hook=enc_hook)
    return msgspec.from_builtins(data_kwargs, type=model_cls)
