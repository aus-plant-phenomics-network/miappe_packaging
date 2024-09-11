import datetime
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Annotated, NamedTuple, TypedDict

from msgspec import field
from rdflib.namespace import FOAF

from appnlib.core.schema import FieldInfo, IDRef, Schema
from appnlib.core.struct import LinkedDataClass


class Person(LinkedDataClass):
    __rdf_resource__ = FOAF.Person
    __rdf_context__ = FOAF._NS
    firstName: str
    lastName: str
    birthday: datetime.date
    mbox: str | None = None
    knows: Annotated[
        list[str],
        FieldInfo(ref=FOAF.knows, range=IDRef(ref=FOAF.Person), repeat=True),
    ] = field(default_factory=list)


@dataclass
class PersonDataClass:
    id: str
    firstName: str
    lastName: str
    birthday: datetime.date
    mbox: str | None = None
    knows: list[str] = dc_field(default_factory=list)


class PersonNamedTuple(NamedTuple):
    id: str
    firstName: str
    lastName: str
    birthday: datetime.date
    mbox: str | None = None
    knows: list[str] = list()


class PersonTypedDict(TypedDict):
    id: str
    firstName: str
    lastName: str
    birthday: datetime.date
    mbox: str
    knows: list[str]


class Group(LinkedDataClass):
    __schema__ = Schema(
        __rdf_resource__=FOAF.Group,
        attrs={
            "member": FieldInfo(FOAF.member, range=IDRef(ref=FOAF.Person), repeat=True)
        },
    )
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

person_name_map = Person.__schema__.name_mapping
group_name_map = Group.__schema__.name_mapping


def to_raw_dict(dict_item: dict, name_map: dict[str, FieldInfo]) -> dict:
    result = {"id": dict_item["id"]}
    for name, info in name_map.items():
        value = dict_item[name]
        if value is not None:
            result[str(info.ref)] = value
    return result


ObamaDict = {k: getattr(Obama, k) for k in Obama.__struct_fields__}
BidenDict = {k: getattr(Biden, k) for k in Biden.__struct_fields__}
ClintonDict = {k: getattr(Clinton, k) for k in Clinton.__struct_fields__}
AlGoreDict = {k: getattr(AlGore, k) for k in AlGore.__struct_fields__}
PresidentsDict = {k: getattr(Presidents, k) for k in Presidents.__struct_fields__}
VicePresidentsDict = {
    k: getattr(VicePresidents, k) for k in VicePresidents.__struct_fields__
}
ObamaRawDict = to_raw_dict(ObamaDict, person_name_map)
BidenRawDict = to_raw_dict(BidenDict, person_name_map)
ClintonRawDict = to_raw_dict(ClintonDict, person_name_map)
AlGoreRawDict = to_raw_dict(AlGoreDict, person_name_map)
PresidentsRawDict = to_raw_dict(PresidentsDict, group_name_map)
VicePresidentsRawDict = to_raw_dict(VicePresidentsDict, group_name_map)

ObamaDataClass = PersonDataClass(**ObamaDict)
ObamaNamedTuple = PersonNamedTuple(**ObamaDict)
ObamaTypedDict = PersonTypedDict(**ObamaDict)  # type:ignore[typeddict-item]
