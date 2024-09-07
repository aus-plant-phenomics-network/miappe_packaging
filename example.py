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
from rdflib.namespace import FOAF, XSD

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
            range={"ref": FOAF.Person},
        ),
    },
)


@dataclass
class Person(Base):
    __schema__ = PersonSchema
    firstName: str
    lastName: str
    knows: list[IdentifiedNode] = field(default_factory=list)


registry = Registry()
registry.graph.bind("foaf", FOAF)
Harry = Person(id="http://schema.org/Harry", firstName="Harry", lastName="Le")
Sally = Person(id="http://schema.org/Sally", firstName="Sally", lastName="Hoang")
John = Person(id="http://schema.org/John", firstName="John", lastName="Doe")
Jane = Person(id="http://schema.org/Jane", firstName="Jane", lastName="Doe")
Harry.knows.append(Sally.ID)
Harry.knows.append(Jane.ID)
Sally.knows.append(Harry.ID)
John.knows.append(Jane.ID)
Jane.knows.append(John.ID)
Jane.knows.append(Harry.ID)
registry.serialize("FOAF.json", format="json-ld")

# %%
registry = Registry()
registry.load("FOAF.json")


# %%
