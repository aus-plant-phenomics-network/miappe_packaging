# %%
from __future__ import annotations

import datetime

from msgspec import field
from rdflib import IdentifiedNode
from rdflib.namespace import FOAF, XSD

import src.miappe_packaging.converter as Converter
from src.miappe_packaging.base import Base
from src.miappe_packaging.registry import Registry
from src.miappe_packaging.types import FieldInfo, IDRef, Schema

PersonSchema = Schema(
    rdf_resource=FOAF.Person,
    attrs={
        "firstName": FieldInfo(ref=FOAF.firstName),
        "lastName": FieldInfo(ref=FOAF.lastName),
        "knows": FieldInfo(ref=FOAF.knows, range=IDRef(ref=FOAF.Person)),
        "age": FieldInfo(ref=FOAF.age),
        "birthday": FieldInfo(ref=FOAF.birthday),
        "email": FieldInfo(ref=FOAF.mbox),
    },
)


class Person(Base):
    __schema__ = PersonSchema

    firstName: str
    lastName: str
    age: int
    birthday: datetime.date
    email: str
    knows: list[str | IdentifiedNode] = field(default_factory=list)


Harry = Person(
    id="http://example.org/Harry",
    firstName="Harry",
    lastName="Le",
    birthday=datetime.date(1995, 10, 29),
    email="lehoangsonsg@gmail.com",
    age=29,
    knows=["http://example.org/Sally"],
)

Sally = Person(
    id="http://example.org/Sally",
    firstName="Sally",
    lastName="Hoang",
    birthday=datetime.date(1993, 1, 2),
    email="lehoangsonsg@gmail.com",
    age=31,
    knows=["http://example.org/Harry"],
)

registry = Registry()
registry.serialize(destination="FOAF.json", context={"foaf": FOAF._NS})
# %%
