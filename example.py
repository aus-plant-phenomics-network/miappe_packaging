# %%
import datetime
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Annotated, NamedTuple, TypedDict

from msgspec import field
from rdflib.namespace import FOAF

from src.miappe_packaging.schema import FieldInfo, IDRef, Schema
from src.miappe_packaging.struct import LinkedDataClass, Registry


class Person(LinkedDataClass):
    __rdf_resource__ = FOAF.Person
    __rdf_context__ = FOAF._NS
    firstName: str
    lastName: str
    birthdate: datetime.date
    mbox: str | None = None
    knows: Annotated[
        list[str],
        FieldInfo(ref=FOAF.knows, range=IDRef(ref=FOAF.Person), repeat=True),
    ] = field(default_factory=list)


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
    birthdate=datetime.datetime(1961, 8, 4),
    knows=[ID_POOL["JoeBiden"], ID_POOL["BillClinton"]],
)

Biden = Person(
    id=ID_POOL["JoeBiden"],
    firstName="Joe",
    lastName="Biden",
    birthdate=datetime.date(1942, 11, 20),
    knows=[ID_POOL["BarrackObama"]],
)

Clinton = Person(
    id=ID_POOL["BillClinton"],
    firstName="Bill",
    lastName="Clinton",
    birthdate=datetime.datetime(1946, 8, 19),
    knows=[ID_POOL["AlGore"], ID_POOL["BarrackObama"]],
)

AlGore = Person(
    id=ID_POOL["AlGore"],
    firstName="Al",
    lastName="Gore",
    birthdate=datetime.datetime(1948, 3, 31),
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

registry = Registry()

registry.serialize(destination="WhiteHouse.json", context={"foaf": FOAF._NS})
