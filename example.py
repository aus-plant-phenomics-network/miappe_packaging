# %%
from miappe_packaging.struct import LinkedDataClass
from rdflib.namespace import XSD, FOAF
from msgspec import field
import datetime


class Person(LinkedDataClass):
    __rdf_resource__ = FOAF.Person

    first_name: str
    last_name: str
    address: str | None = None
    birthday: datetime.datetime | None = None
    knows: list[str] | str = field(default_factory=list)


me = Person(first_name="Son", last_name="Le", address="lehoangsonsg@gmail.com")

# %%
