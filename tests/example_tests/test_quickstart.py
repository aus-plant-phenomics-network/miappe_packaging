import datetime
from typing import Any

import pytest
from appnlib.core.dataclass import DEFAULT_CODEC, LinkedDataClass, Registry
from appnlib.core.types import FieldInfo, Schema
from msgspec import field
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import FOAF, RDF, XSD

PersonSchema = Schema(
    rdf_resource=FOAF.Person,
    attrs={
        "firstName": FieldInfo(ref=FOAF.firstName),
        "lastName": FieldInfo(ref=FOAF.lastName),
        "birthday": FieldInfo(ref=FOAF.birthday, range=XSD.date),
        "knows": FieldInfo(ref=FOAF.knows, repeat=True, resource_ref=FOAF.Person),
    },
)

GroupSchema = Schema(
    rdf_resource=FOAF.Group,
    attrs={"member": FieldInfo(FOAF.member, repeat=True, resource_ref=FOAF.Person)},
)

registry = Registry()


class Person(LinkedDataClass):
    __schema__ = PersonSchema

    firstName: str
    lastName: str
    birthday: datetime.date
    knows: list[str] = field(default_factory=list)


class Group(LinkedDataClass):
    __schema__ = GroupSchema
    member: list[str]


ID_POOL = {
    "BarrackObama": "http://example.org/BarrackObama",
    "JoeBiden": "http://example.org/JoeBiden",
    "BillClinton": "http://example.org/BillClinton",
    "AlGore": "http://example.org/AlGore",
}

Obama = Person(
    id=ID_POOL["BarrackObama"],
    firstName="Barrack",
    lastName="Obama",
    birthday=datetime.date(1961, 8, 4),
    knows=[ID_POOL["JoeBiden"], ID_POOL["BillClinton"]],
)

Biden = Person(
    id=ID_POOL["JoeBiden"],
    firstName="Joe",
    lastName="Biden",
    birthday=datetime.date(1942, 11, 20),
    knows=[ID_POOL["BarrackObama"]],
)

Clinton = Person(
    id=ID_POOL["BillClinton"],
    firstName="Bill",
    lastName="Clinton",
    birthday=datetime.date(1946, 8, 19),
    knows=[ID_POOL["AlGore"], ID_POOL["BarrackObama"]],
)

AlGore = Person(
    id=ID_POOL["AlGore"],
    firstName="Al",
    lastName="Gore",
    birthday=datetime.date(1948, 3, 31),
    knows=[ID_POOL["BillClinton"]],
)

Presidents = Group(
    id="http://example.org/USPresidents",
    member=[ID_POOL["BarrackObama"], ID_POOL["BillClinton"], ID_POOL["JoeBiden"]],
)
VicePresidents = Group(
    id="http://example.org/USVicePresidents",
    member=[ID_POOL["AlGore"], ID_POOL["JoeBiden"]],
)


def create_dict(person: LinkedDataClass) -> dict[str, Any]:
    result = {}
    for sfield in person.__struct_fields__:
        result[sfield] = getattr(person, sfield)
    return result


def create_person_graph(person: Person) -> Graph:
    graph = Graph()
    graph.add((person.ID, RDF.type, FOAF.Person))
    graph.add((person.ID, FOAF.firstName, Literal(person.firstName)))
    graph.add((person.ID, FOAF.lastName, Literal(person.lastName)))
    graph.add((person.ID, FOAF.birthday, Literal(person.birthday)))
    for pid in person.knows:
        graph.add((person.ID, FOAF.knows, URIRef(pid)))
    return graph


def create_group_graph(group: Group) -> Graph:
    graph = Graph()
    graph.add((group.ID, RDF.type, FOAF.Group))
    for pid in group.member:
        graph.add((group.ID, FOAF.member, URIRef(pid)))
    return graph


ObamaDict = create_dict(Obama)
BidenDict = create_dict(Biden)
AlGoreDict = create_dict(AlGore)
ClintonDict = create_dict(Clinton)
PresidentsDict = create_dict(Presidents)
VicePresidentsDict = create_dict(VicePresidents)

ObamaGraph = create_person_graph(Obama)
BidenGraph = create_person_graph(Biden)
ClintonGraph = create_person_graph(Clinton)
AlGoreGraph = create_person_graph(AlGore)
PresidentsGraph = create_group_graph(Presidents)
VicePresidentsGraph = create_group_graph(VicePresidents)


@pytest.mark.parametrize(
    "struct_obj, dict_obj",
    [
        (Obama, ObamaDict),
        (Biden, BidenDict),
        (Clinton, ClintonDict),
        (AlGore, AlGoreDict),
        (Presidents, PresidentsDict),
        (VicePresidents, VicePresidentsDict),
    ],
)
def test_codec_struct_to_dict(struct_obj: LinkedDataClass, dict_obj: dict) -> None:
    parsed = DEFAULT_CODEC.encode_to_dict(struct_obj)
    assert parsed == dict_obj


@pytest.mark.parametrize(
    "struct_obj, dict_obj, model",
    [
        (Obama, ObamaDict, Person),
        (Biden, BidenDict, Person),
        (Clinton, ClintonDict, Person),
        (AlGore, AlGoreDict, Person),
        (Presidents, PresidentsDict, Group),
        (VicePresidents, VicePresidentsDict, Group),
    ],
)
def test_codec_dict_to_struct(struct_obj: LinkedDataClass, dict_obj: dict, model: type[LinkedDataClass]) -> None:
    parsed = DEFAULT_CODEC.decode_from_dict(dict_obj, model)
    assert parsed == struct_obj


@pytest.mark.parametrize(
    "struct_obj, graph_obj",
    [
        (Obama, ObamaGraph),
        (Biden, BidenGraph),
        (AlGore, AlGoreGraph),
        (Clinton, ClintonGraph),
        (Presidents, PresidentsGraph),
        (VicePresidents, VicePresidentsGraph),
    ],
)
def test_codec_struct_to_graph(struct_obj: LinkedDataClass, graph_obj: Graph) -> None:
    parsed = DEFAULT_CODEC.encode_to_triple(struct_obj)
    for stmt in parsed:
        assert stmt in graph_obj
