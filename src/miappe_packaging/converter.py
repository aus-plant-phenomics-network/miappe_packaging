from typing import Any, overload

from rdflib import Graph, IdentifiedNode
from rdflib.extras.describer import Describer

from src.miappe_packaging.exceptions import MissingSchema
from src.miappe_packaging.types import FieldInfo, IDRef, Schema
from src.miappe_packaging.utils import convert_to_ref, validate_schema


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
def struct_to_graph(
    *,
    struct: Any,
    graph: Graph,
    schema: Schema | None = None,
) -> Graph: ...
@overload
def struct_to_graph(
    *,
    struct: Any,
    schema: Schema | None = None,
    identifier: IdentifiedNode | str | None = None,
) -> Graph: ...
def struct_to_graph(
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
    describer.rdftype(schema.rdf_resource)
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
