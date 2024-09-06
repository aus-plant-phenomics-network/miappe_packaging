# %%
from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Annotated,
    Any,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Optional,
    Sequence,
    Set,
    Type,
    get_args,
    get_origin,
    get_type_hints,
)

from rdflib import IdentifiedNode, URIRef
from rdflib.namespace import FOAF

from src.miappe_packaging.schema import Base, FieldInfo, Registry, Schema

PersonSchema = Schema(
    __rdf_resource__=FOAF.Person,
    attrs={
        "firstName": FieldInfo(ref=FOAF.firstName),
        "lastName": FieldInfo(ref=FOAF.lastName),
        "knows": FieldInfo(
            ref=FOAF.knows,
            repeat=True,
            required=False,
            range={"ref": FOAF.Person, "value": "Person"},
        ),
    },
)


@dataclass
class Person(Base):
    __schema__ = PersonSchema
    firstName: str
    lastName: str
    knows: list[IdentifiedNode] = field(default_factory=list)


Harry = Person(id="http://example.org/Harry", firstName="Harry", lastName="Le")
Sally = Person(firstName="Sally", lastName="Hoang")
John = Person(firstName="John", lastName="Doe")
Jane = Person(firstName="Jane", lastName="Doe")
Harry.knows.append(Sally.ID)
Sally.knows.append(Harry.ID)
John.knows.append(Jane.ID)
Jane.knows.append(John.ID)
registry = Registry()
registry.add(Harry)
registry.add(Sally)
registry.add(John)
registry.add(Jane)
registry.serialize("FOAF.json", format="json-ld")

# %%
