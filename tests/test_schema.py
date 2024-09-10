import datetime
from typing import Annotated

from msgspec import field
from rdflib import IdentifiedNode
from rdflib.namespace import FOAF, XSD

from src.miappe_packaging.base import LinkedDataClass, Registry
from src.miappe_packaging.graph import from_struct, to_struct
from src.miappe_packaging.schema import FieldInfo, IDRef, Schema


class Person(LinkedDataClass):
    __rdf_resource__ = FOAF.Person
    __rdf_context__ = FOAF._NS
    firstName: str
    lastName: str
    birthdate: datetime.date
    mbox: str | None = None
    knows: Annotated[
        list[IdentifiedNode],
        FieldInfo(ref=FOAF.knows, range=IDRef(ref=FOAF.Person), repeat=True),
    ] = field(default_factory=list)


def test_to_struct_from_struct() -> None:
    barrack_obama = Person(
        firstName="Barrack", lastName="Obama", birthdate=datetime.date(1961, 8, 4)
    )
    michelle_obama = Person(
        firstName="Michelle", lastName="Obama", birthdate=datetime.date(1964, 1, 17)
    )
    barrack_obama.knows.append(michelle_obama.ID)
    michelle_obama.knows.append(barrack_obama.ID)
    graph = from_struct(struct=barrack_obama)
    recon = to_struct(graph=graph, identifier=barrack_obama.ID, model_cls=Person)
    assert barrack_obama == recon
