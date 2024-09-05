# %%
from __future__ import annotations

import datetime
from dataclasses import dataclass

from rdflib.namespace import FOAF, XSD

from src.miappe_packaging.base import Base, Registry
from src.miappe_packaging.utils import field


@dataclass()
class Person(Base):
    __meta_class__ = FOAF.Person

    first_name: str = field(ref=FOAF.firstName)

    last_name: str = field(ref=FOAF.lastName)

    birth_day: datetime.date | None = field(
        ref=FOAF.birthday, type_ref=XSD.date, default=None
    )

    email: str | None = field(ref=FOAF.mbox, default=None)

    knows: list[Person] = field(ref=FOAF.knows, default_factory=list)


# HELPERS
Harry = Person(
    id="http://example.org/Harry",
    first_name="Harry",
    last_name="Le",
    birth_day=datetime.date(1995, 10, 29),
    email="lehoangsonsg@gmail.com",
)
Sally = Person(
    id="http://example.org/Sally",
    first_name="Sally",
    last_name="Hoang",
    birth_day=datetime.date(1993, 1, 2),
    email="httra12@gmail.com",
)
Harry.knows.append(Sally)
registry = Registry()
registry.add(Harry)
registry.add(Sally)
registry.serialize("FOAF.json")
# %%
