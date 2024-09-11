from typing import Any

import pytest
from rdflib import Graph, URIRef
from rdflib.compare import to_isomorphic
from rdflib.namespace import RDF

from src.miappe_packaging.exceptions import MissingSchema
from src.miappe_packaging.graph import from_struct, sub_graph, to_builtin, to_struct
from src.miappe_packaging.schema import Schema
from src.miappe_packaging.struct import LinkedDataClass
from tests.fixture import (
    AlGore,
    Biden,
    Clinton,
    Group,
    Obama,
    ObamaDataClass,
    ObamaDict,
    ObamaNamedTuple,
    ObamaTypedDict,
    Person,
    Presidents,
    VicePresidents,
)

ObamaGraph = from_struct(struct=Obama)
BidenGraph = from_struct(struct=Biden)
ClintonGraph = from_struct(struct=Clinton)
AlGoreGraph = from_struct(struct=AlGore)
PresidentsGraph = from_struct(struct=Presidents)
VicePresidentsGraph = from_struct(struct=VicePresidents)


@pytest.mark.parametrize(
    "object, schema",
    [
        (Obama, None),
        (Clinton, Person.__schema__),
        (Biden, Person.__schema__),
        (AlGore, None),
        (Presidents, Group.__schema__),
        (VicePresidents, VicePresidents.__schema__),
    ],
)
def test_to_graph(object: LinkedDataClass, schema: Schema | None) -> None:
    obj_graph = from_struct(struct=object, schema=schema)
    ref_mapping = object.__schema__.ref_mapping
    subjects = list(obj_graph.subjects(RDF.type))
    assert len(subjects) == 1
    assert object.ID in subjects
    resource = list(obj_graph.objects(object.ID, RDF.type, unique=True))
    assert len(resource) == 1
    assert object.__schema__.__rdf_resource__ in resource
    stmts = obj_graph.predicate_objects(object.ID)
    for pred, obj in stmts:
        if pred == RDF.type:
            continue
        name = ref_mapping[pred]  # type: ignore[index]
        value = getattr(object, name)
        if hasattr(value, "__len__") and not isinstance(value, str):
            assert obj.toPython() in value  # type:ignore[attr-defined]
        else:
            assert obj.toPython() == value  # type:ignore[attr-defined]


def test_to_graph_id_provided() -> None:
    graph = from_struct(struct=Obama, identifier="./localID/ObamaGraph")
    assert graph.identifier == URIRef("./localID/ObamaGraph")


def test_to_graph_existing_graph_empty_base() -> None:
    blank_graph = Graph()
    from_struct(struct=Obama, graph=blank_graph)
    iso_blank = to_isomorphic(blank_graph)
    iso_obama = to_isomorphic(ObamaGraph)
    assert iso_blank == iso_obama


def test_to_graph_existing_graph_non_empty_base() -> None:
    base = from_struct(struct=Obama)
    from_struct(struct=Biden, graph=base)
    from_struct(struct=Clinton, graph=base)
    from_struct(struct=AlGore, graph=base)
    from_struct(struct=Presidents, graph=base)
    from_struct(struct=VicePresidents, graph=base)
    iso_base = to_isomorphic(base)
    iso_joined = to_isomorphic(
        ObamaGraph
        + BidenGraph
        + ClintonGraph
        + AlGoreGraph
        + VicePresidentsGraph
        + PresidentsGraph
    )
    assert iso_base == iso_joined


@pytest.mark.parametrize(
    "obj",
    [
        (ObamaDict),
        (ObamaDataClass),
    ],
)
def test_to_graph_on_other_dataclasses_with_schema(obj: Any) -> None:
    obama_graph = from_struct(struct=obj, schema=Person.__schema__)
    assert to_isomorphic(obama_graph) == to_isomorphic(ObamaGraph)


@pytest.mark.parametrize(
    "obj",
    [
        (ObamaDict),
        (ObamaDataClass),
        (ObamaTypedDict),
        (ObamaNamedTuple),
    ],
)
def test_to_graph_on_other_dataclasses_without_schema_raises(obj: Any) -> None:
    with pytest.raises(MissingSchema):
        from_struct(struct=obj)


def test_to_graph_on_other_dataclasses_without_id_raises() -> None:
    kwargs = {k: v for k, v in ObamaDict.items() if k not in ["id", "ID"]}
    with pytest.raises(ValueError):
        from_struct(struct=kwargs, schema=Person.__schema__)


@pytest.mark.parametrize(
    "first, second, firstGraph, secondGraph",
    [
        (Obama, Biden, ObamaGraph, BidenGraph),
        (Obama, Clinton, ObamaGraph, ClintonGraph),
        (Obama, Presidents, ObamaGraph, PresidentsGraph),
    ],
)
def test_sub_graph(
    first: LinkedDataClass,
    second: LinkedDataClass,
    firstGraph: Graph,
    secondGraph: Graph,
) -> None:
    base = Graph()
    from_struct(struct=first, graph=base)
    from_struct(struct=second, graph=base)
    assert to_isomorphic(sub_graph(base, first.ID)) == to_isomorphic(firstGraph)
    assert to_isomorphic(sub_graph(base, second.ID)) == to_isomorphic(secondGraph)


def test_subgraph_id_not_exists() -> None:
    with pytest.raises(ValueError):
        sub_graph(ObamaGraph, Biden.ID)
