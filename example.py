# %%
import datetime

from msgspec import field
from rdflib.namespace import FOAF, XSD

from appnlib.core.dataclass import LinkedDataClass, Registry
from appnlib.core.types import FieldInfo, Schema

PersonSchema = Schema(
    rdf_resource=FOAF.Person,
    attrs={
        "firstName": FieldInfo(ref=FOAF.firstName),
        "lastName": FieldInfo(ref=FOAF.lastName),
        "birthdate": FieldInfo(ref=FOAF.birthday, range=XSD.date),
        "knows": FieldInfo(ref=FOAF.knows, repeat=True, resource_ref=FOAF.Person),
    },
)

GroupSchema = Schema(
    rdf_resource=FOAF.Group,
    attrs={"member": FieldInfo(FOAF.member, repeat=True, resource_ref=FOAF.Person)},
)


class Person(LinkedDataClass):
    __schema__ = PersonSchema

    firstName: str
    lastName: str
    birthdate: datetime.date
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
    birthdate=datetime.date(1961, 8, 4),
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
    birthdate=datetime.date(1946, 8, 19),
    knows=[ID_POOL["AlGore"], ID_POOL["BarrackObama"]],
)

AlGore = Person(
    id=ID_POOL["AlGore"],
    firstName="Al",
    lastName="Gore",
    birthdate=datetime.date(1948, 3, 31),
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
session = registry.create_session()
session.add(VicePresidents)
session.add(Presidents)
session.to_json(destination="WhiteHouse.json", context={"foaf": FOAF._NS})

# %%
