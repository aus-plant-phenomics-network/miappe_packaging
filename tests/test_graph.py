# from operator import itemgetter
# from typing import Any, Type

# import pytest
# from rdflib import Graph, Literal, URIRef
# from rdflib.compare import to_isomorphic
# from rdflib.graph import _ObjectType
# from rdflib.namespace import FOAF, RDF

# from appnlib.core.exceptions import AnnotationError, MissingSchema
# from appnlib.core.graph import (
#     _get_subjects,
#     _update_attrs_from_stmt,
#     from_struct,
#     sub_graph,
#     to_builtin,
#     to_struct,
# )
# from appnlib.core.schema import Schema
# from appnlib.core.struct import LinkedDataClass
# from tests.fixture import (
#     AlGore,
#     Biden,
#     Clinton,
#     Group,
#     Obama,
#     ObamaDataClass,
#     ObamaDict,
#     ObamaNamedTuple,
#     ObamaRawDict,
#     ObamaTypedDict,
#     Person,
#     Presidents,
#     PresidentsRawDict,
#     VicePresidents,
# )

# ObamaGraph = from_struct(struct=Obama)
# BidenGraph = from_struct(struct=Biden)
# ClintonGraph = from_struct(struct=Clinton)
# AlGoreGraph = from_struct(struct=AlGore)
# PresidentsGraph = from_struct(struct=Presidents)
# VicePresidentsGraph = from_struct(struct=VicePresidents)


# @pytest.mark.parametrize(
#     "object, schema",
#     [
#         (Obama, None),
#         (Clinton, Person.__schema__),
#         (Biden, Person.__schema__),
#         (AlGore, None),
#         (Presidents, Group.__schema__),
#         (VicePresidents, VicePresidents.__schema__),
#     ],
# )
# def test_from_struct(object: LinkedDataClass, schema: Schema | None) -> None:
#     obj_graph = from_struct(struct=object, schema=schema)
#     ref_mapping = object.__schema__.ref_mapping
#     subjects = list(obj_graph.subjects(RDF.type))
#     assert len(subjects) == 1
#     assert object.ID in subjects
#     resource = list(obj_graph.objects(object.ID, RDF.type, unique=True))
#     assert len(resource) == 1
#     assert object.__schema__.__rdf_resource__ in resource
#     stmts = obj_graph.predicate_objects(object.ID)
#     for pred, obj in stmts:
#         if pred == RDF.type:
#             continue
#         name = ref_mapping[pred]  # type: ignore[index]
#         value = getattr(object, name)
#         if hasattr(value, "__len__") and not isinstance(value, str):
#             assert obj.toPython() in value  # type:ignore[attr-defined]
#         else:
#             assert obj.toPython() == value  # type:ignore[attr-defined]


# def test_from_struct_id_provided() -> None:
#     graph = from_struct(struct=Obama, identifier="./localID/ObamaGraph")
#     assert graph.identifier == URIRef("./localID/ObamaGraph")


# def test_from_struct_existing_graph_empty_base() -> None:
#     blank_graph = Graph()
#     from_struct(struct=Obama, graph=blank_graph)
#     iso_blank = to_isomorphic(blank_graph)
#     iso_obama = to_isomorphic(ObamaGraph)
#     assert iso_blank == iso_obama


# def test_from_struct_existing_graph_non_empty_base() -> None:
#     base = from_struct(struct=Obama)
#     from_struct(struct=Biden, graph=base)
#     from_struct(struct=Clinton, graph=base)
#     from_struct(struct=AlGore, graph=base)
#     from_struct(struct=Presidents, graph=base)
#     from_struct(struct=VicePresidents, graph=base)
#     iso_base = to_isomorphic(base)
#     iso_joined = to_isomorphic(
#         ObamaGraph
#         + BidenGraph
#         + ClintonGraph
#         + AlGoreGraph
#         + VicePresidentsGraph
#         + PresidentsGraph
#     )
#     assert iso_base == iso_joined


# @pytest.mark.parametrize(
#     "obj",
#     [
#         (ObamaDict),
#         (ObamaDataClass),
#     ],
# )
# def test_from_struct_on_other_dataclasses_with_schema(obj: Any) -> None:
#     obama_graph = from_struct(struct=obj, schema=Person.__schema__)
#     assert to_isomorphic(obama_graph) == to_isomorphic(ObamaGraph)


# @pytest.mark.parametrize(
#     "obj",
#     [
#         (ObamaDict),
#         (ObamaDataClass),
#         (ObamaTypedDict),
#         (ObamaNamedTuple),
#     ],
# )
# def test_from_struct_on_other_dataclasses_without_schema_raises(obj: Any) -> None:
#     with pytest.raises(MissingSchema):
#         from_struct(struct=obj)


# def test_from_struct_on_other_dataclasses_without_id_raises() -> None:
#     kwargs = {k: v for k, v in ObamaDict.items() if k not in ["id", "ID"]}
#     with pytest.raises(ValueError):
#         from_struct(struct=kwargs, schema=Person.__schema__)


# @pytest.mark.parametrize(
#     "first, second, firstGraph, secondGraph",
#     [
#         (Obama, Biden, ObamaGraph, BidenGraph),
#         (Obama, Clinton, ObamaGraph, ClintonGraph),
#         (Obama, Presidents, ObamaGraph, PresidentsGraph),
#     ],
# )
# def test_sub_graph(
#     first: LinkedDataClass,
#     second: LinkedDataClass,
#     firstGraph: Graph,
#     secondGraph: Graph,
# ) -> None:
#     base = Graph()
#     from_struct(struct=first, graph=base)
#     from_struct(struct=second, graph=base)
#     assert to_isomorphic(sub_graph(base, first.ID)) == to_isomorphic(firstGraph)
#     assert to_isomorphic(sub_graph(base, second.ID)) == to_isomorphic(secondGraph)


# def test_subgraph_id_not_exist_raises() -> None:
#     with pytest.raises(ValueError):
#         sub_graph(ObamaGraph, Biden.ID)


# @pytest.mark.parametrize(
#     "graph, subject",
#     [
#         (ObamaGraph, set([Obama.ID])),
#         (ClintonGraph, set([Clinton.ID])),
#         (PresidentsGraph, set([Presidents.ID])),
#         (ClintonGraph + ObamaGraph, set([Clinton.ID, Obama.ID])),
#         (
#             ClintonGraph + ObamaGraph + PresidentsGraph + VicePresidentsGraph,
#             set([Clinton.ID, Obama.ID, Presidents.ID, VicePresidents.ID]),
#         ),
#     ],
# )
# def test_graph__get_subjects(graph: Graph, subject: set[URIRef]) -> None:
#     graph_subjects = _get_subjects(graph)
#     assert graph_subjects == subject


# @pytest.mark.parametrize(
#     "graph, identifier, subject",
#     [
#         (ObamaGraph, Obama.ID, set([Obama.ID])),
#         (ObamaGraph + ClintonGraph, Clinton.ID, set([Clinton.ID])),
#         (PresidentsGraph, Presidents.ID, set([Presidents.ID])),
#         (ClintonGraph + ObamaGraph, Obama.ID, set([Obama.ID])),
#         (
#             ClintonGraph + ObamaGraph + PresidentsGraph + VicePresidentsGraph,
#             VicePresidents.ID,
#             set([VicePresidents.ID]),
#         ),
#     ],
# )
# def test_graph__get_subjects_with_identifier(
#     graph: Graph, identifier: URIRef, subject: set[URIRef]
# ) -> None:
#     graph_subjects = _get_subjects(graph, identifier=identifier)
#     assert graph_subjects == subject


# @pytest.mark.parametrize(
#     "graph, schema, subject",
#     [
#         (ObamaGraph, Presidents.__schema__, set()),
#         (ObamaGraph, Obama.__schema__, set([Obama.ID])),
#         (ObamaGraph + ClintonGraph, Obama.__schema__, set([Clinton.ID, Obama.ID])),
#         (
#             PresidentsGraph + VicePresidentsGraph,
#             Presidents.__schema__,
#             set([Presidents.ID, VicePresidents.ID]),
#         ),
#         (
#             ClintonGraph + ObamaGraph + PresidentsGraph + VicePresidentsGraph,
#             Obama.__schema__,
#             set([Obama.ID, Clinton.ID]),
#         ),
#         (
#             ClintonGraph + ObamaGraph + PresidentsGraph + VicePresidentsGraph,
#             VicePresidents.__schema__,
#             set([Presidents.ID, VicePresidents.ID]),
#         ),
#     ],
# )
# def test_graph__get_subjects_with_schema(
#     graph: Graph, schema: Schema, subject: set[URIRef]
# ) -> None:
#     graph_subjects = _get_subjects(graph, schema=schema)
#     assert graph_subjects == subject


# @pytest.mark.parametrize(
#     "graph, identifier, schema, subject",
#     [
#         (ObamaGraph, Obama.ID, Obama.__schema__, set([Obama.ID])),
#         (ObamaGraph + ClintonGraph, Obama.ID, Obama.__schema__, set([Obama.ID])),
#         (ObamaGraph + ClintonGraph, Clinton.ID, Obama.__schema__, set([Clinton.ID])),
#         (
#             PresidentsGraph + VicePresidentsGraph,
#             Presidents.ID,
#             Presidents.__schema__,
#             set([Presidents.ID]),
#         ),
#         (
#             ClintonGraph + ObamaGraph + PresidentsGraph + VicePresidentsGraph,
#             Obama.ID,
#             Obama.__schema__,
#             set([Obama.ID]),
#         ),
#         (
#             ClintonGraph + ObamaGraph + PresidentsGraph + VicePresidentsGraph,
#             Presidents.ID,
#             VicePresidents.__schema__,
#             set([Presidents.ID]),
#         ),
#     ],
# )
# def test_graph__get_subjects_with_schema_and_identifier(
#     graph: Graph, identifier: URIRef, schema: Schema, subject: set[URIRef]
# ) -> None:
#     graph_subjects = _get_subjects(graph, schema=schema, identifier=identifier)
#     assert graph_subjects == subject


# @pytest.mark.parametrize(
#     "graph, identifier",
#     [
#         (ObamaGraph, Biden.ID),
#         (BidenGraph, Presidents.ID),
#         (ObamaGraph + BidenGraph, Clinton.ID),
#         (ObamaGraph + BidenGraph, Presidents.ID),
#     ],
# )
# def test_graph__get_subjects_with_identifier_not_in_graph_raises(
#     graph: Graph, identifier: URIRef
# ) -> None:
#     with pytest.raises(ValueError):
#         _get_subjects(graph=graph, identifier=identifier)


# @pytest.mark.parametrize(
#     "graph, identifier, schema",
#     [
#         (ObamaGraph, Biden.ID, Obama.__schema__),
#         (BidenGraph, Biden.ID, Presidents.__schema__),
#         (ObamaGraph + BidenGraph, Clinton.ID, Obama.__schema__),
#         (ObamaGraph + BidenGraph, Presidents.ID, Presidents.__schema__),
#     ],
# )
# def test_graph__get_subjects_with_identifier_schema_not_in_graph_raises(
#     graph: Graph, identifier: URIRef, schema: Schema
# ) -> None:
#     with pytest.raises(ValueError):
#         _get_subjects(graph=graph, identifier=identifier, schema=schema)


# @pytest.mark.parametrize(
#     "pred, value, attrs, schema, exp_attrs",
#     [
#         (RDF.type, Obama.__schema__.__rdf_resource__, {}, None, {}),
#         (
#             FOAF.firstName,
#             Literal(Obama.firstName),
#             {},
#             None,
#             {FOAF.firstName: Literal(Obama.firstName)},
#         ),
#         (
#             FOAF.knows,
#             Obama.ID,
#             {FOAF.knows: Biden.ID},
#             None,
#             {FOAF.knows: [Biden.ID, Obama.ID]},
#         ),
#         (
#             FOAF.birthday,
#             Literal(Obama.birthday),
#             {FOAF.knows: Biden.ID},
#             None,
#             {
#                 FOAF.knows: Biden.ID,
#                 FOAF.birthday: Literal(Obama.birthday),
#             },
#         ),
#     ],
# )
# def test_update_attrs_with_schema(
#     pred: URIRef,
#     value: _ObjectType,
#     attrs: dict[str, Any],
#     schema: Schema | None,
#     exp_attrs: dict[str, Any],
# ) -> None:
#     _update_attrs_from_stmt(pred, value, attrs, schema)
#     assert attrs == exp_attrs


# @pytest.mark.parametrize(
#     "pred, value, attrs, schema, exp_attrs",
#     [
#         (RDF.type, Obama.__schema__.__rdf_resource__, {}, Obama.__schema__, {}),
#         (
#             FOAF.firstName,
#             Literal(Obama.firstName),
#             {},
#             Obama.__schema__,
#             {"firstName": Literal(Obama.firstName)},
#         ),
#         (
#             FOAF.knows,
#             Obama.ID,
#             {},
#             Obama.__schema__,
#             {"knows": [Obama.ID]},
#         ),
#         (
#             FOAF.knows,
#             Obama.ID,
#             {"knows": [Biden.ID]},
#             Obama.__schema__,
#             {"knows": [Biden.ID, Obama.ID]},
#         ),
#         (
#             FOAF.birthday,
#             Literal(Obama.birthday),
#             {"knows": [Biden.ID]},
#             Obama.__schema__,
#             {
#                 "knows": [Biden.ID],
#                 "birthday": Literal(Obama.birthday),
#             },
#         ),
#     ],
# )
# def test_update_attrs_no_schema(
#     pred: URIRef,
#     value: _ObjectType,
#     attrs: dict[str, Any],
#     schema: Schema | None,
#     exp_attrs: dict[str, Any],
# ) -> None:
#     _update_attrs_from_stmt(pred, value, attrs, schema)
#     assert attrs == exp_attrs


# @pytest.mark.parametrize(
#     "pred, value, attrs, schema",
#     [
#         (
#             FOAF.firstName,
#             Literal(Obama.firstName),
#             {"firstName": Literal(Biden.firstName)},
#             Obama.__schema__,
#         )
#     ],
# )
# def test_update_attrs_wrong_schema_raises(
#     pred: URIRef,
#     value: _ObjectType,
#     attrs: dict[str, Any],
#     schema: Schema | None,
# ) -> None:
#     with pytest.raises(AnnotationError):
#         _update_attrs_from_stmt(pred, value, attrs, schema)


# @pytest.mark.parametrize(
#     "graph, exp_attrs",
#     [
#         (ObamaGraph, [ObamaRawDict]),
#         (PresidentsGraph, [PresidentsRawDict]),
#     ],
# )
# def test_to_builtin_no_schema(graph: Graph, exp_attrs: list[dict[str, Any]]) -> None:
#     python_obj = to_builtin(graph=graph)
#     list_1, list_2 = [
#         sorted(item, key=itemgetter("id")) for item in (python_obj, exp_attrs)
#     ]
#     assert list_1 == list_2


# @pytest.mark.parametrize(
#     "graph, identifier, ref_struct, model_cls, schema",
#     [
#         (ObamaGraph, Obama.ID, Obama, Person, None),
#         (ObamaGraph, Obama.ID, Obama, Person, None),
#         (ObamaGraph + BidenGraph, Obama.ID, Obama, Person, Person.__schema__),
#         (ObamaGraph + BidenGraph, Biden.ID, Biden, Person, Person.__schema__),
#         (
#             ObamaGraph
#             + BidenGraph
#             + PresidentsGraph
#             + VicePresidentsGraph
#             + ClintonGraph
#             + AlGoreGraph,
#             Biden.ID,
#             Biden,
#             Person,
#             None,
#         ),
#         (
#             ObamaGraph
#             + BidenGraph
#             + PresidentsGraph
#             + VicePresidentsGraph
#             + ClintonGraph
#             + AlGoreGraph,
#             Clinton.ID,
#             Clinton,
#             Person,
#             None,
#         ),
#         (
#             ObamaGraph
#             + BidenGraph
#             + PresidentsGraph
#             + VicePresidentsGraph
#             + ClintonGraph
#             + AlGoreGraph,
#             AlGore.ID,
#             AlGore,
#             Person,
#             None,
#         ),
#         (
#             ObamaGraph
#             + BidenGraph
#             + PresidentsGraph
#             + VicePresidentsGraph
#             + ClintonGraph
#             + AlGoreGraph,
#             Obama.ID,
#             Obama,
#             Person,
#             Person.__schema__,
#         ),
#         (
#             ObamaGraph
#             + BidenGraph
#             + PresidentsGraph
#             + VicePresidentsGraph
#             + ClintonGraph
#             + AlGoreGraph,
#             Presidents.ID,
#             Presidents,
#             Group,
#             None,
#         ),
#         (
#             ObamaGraph
#             + BidenGraph
#             + PresidentsGraph
#             + VicePresidentsGraph
#             + ClintonGraph
#             + AlGoreGraph,
#             VicePresidents.ID,
#             VicePresidents,
#             Group,
#             Group.__schema__,
#         ),
#     ],
# )
# def test_to_struct(
#     graph: Graph,
#     identifier: URIRef,
#     ref_struct: LinkedDataClass,
#     model_cls: Type[LinkedDataClass],
#     schema: Schema,
# ) -> None:
#     struct = to_struct(
#         graph=graph,
#         identifier=identifier,
#         model_cls=model_cls,
#         schema=schema,
#     )
#     assert struct.ID == ref_struct.ID
#     for key in struct.__struct_fields__:
#         value = getattr(struct, key)
#         ref_value = getattr(ref_struct, key)
#         if isinstance(value, list):
#             assert set(value) == set(ref_value)
#         else:
#             assert value == ref_value


# @pytest.mark.parametrize(
#     "graph, identifier, model_cls, schema",
#     [
#         (ObamaGraph, Biden.ID, Person, Person.__schema__),
#         (ObamaGraph, Presidents.ID, Person, Person.__schema__),
#     ],
# )
# def test_to_struct_no_id(
#     graph: Graph, identifier: URIRef, model_cls: Type[LinkedDataClass], schema: Schema
# ) -> None:
#     with pytest.raises(ValueError):
#         to_struct(
#             graph=graph, identifier=identifier, model_cls=model_cls, schema=schema
#         )
