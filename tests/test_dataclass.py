import datetime
from typing import Generator

import pytest
from appnlib.core.dataclass import DEFAULT_CODEC, LinkedDataClass, Registry, RegistryConfig
from appnlib.core.exceptions import AnnotationError
from appnlib.core.types import FieldInfo, Schema
from rdflib import Literal, URIRef
from rdflib.namespace import FOAF, RDF, XSD


def test_attrs_more_fields_than_schema_raises() -> None:
    with pytest.raises(AnnotationError):

        class Person(LinkedDataClass):
            __schema__ = Schema(rdf_resource=FOAF.Person, attrs={"firstName": FieldInfo(ref=FOAF.firstName)})
            firstName: str
            lastName: str


def test_schema_more_fields_than_attrs_raises() -> None:
    with pytest.raises(AnnotationError):

        class Person(LinkedDataClass):
            __schema__ = Schema(
                rdf_resource=FOAF.Person,
                attrs={
                    "firstName": FieldInfo(ref=FOAF.firstName),
                    "lastName": FieldInfo(ref=FOAF.lastName),
                },
            )
            firstName: str


@pytest.fixture(scope="function")
def registry() -> Generator[Registry, None, None]:
    Registry.reset()  # Very patchy fix
    yield Registry()
    Registry.reset()


def test_encode_to_triple_basic_string(registry: Registry) -> None:
    class Person(LinkedDataClass):
        __schema__ = Schema(rdf_resource=FOAF.Person, attrs={"firstName": FieldInfo(ref=FOAF.firstName)})
        firstName: str

    me_id = URIRef("http://example.org/me")
    me = Person(id=me_id, firstName="Me")
    triples = DEFAULT_CODEC.encode_to_triple(me)
    first = (me_id, FOAF.firstName, Literal("Me"))
    second = (me_id, RDF.type, FOAF.Person)
    assert {first, second} == set(triples)


def test_encode_to_triple_date(registry: Registry) -> None:
    class Person(LinkedDataClass):
        __schema__ = Schema(
            rdf_resource=FOAF.Person,
            attrs={
                "firstName": FieldInfo(ref=FOAF.firstName),
                "birthday": FieldInfo(ref=FOAF.birthday, range=XSD.date),
            },
        )
        firstName: str
        birthday: datetime.date

    me_id = URIRef("http://example.org/me")
    me = Person(id=me_id, firstName="Me", birthday=datetime.date(2015, 10, 10))
    triples = DEFAULT_CODEC.encode_to_triple(me)
    first = (me_id, FOAF.firstName, Literal("Me"))
    third = (me_id, FOAF.birthday, Literal(me.birthday))
    second = (me_id, RDF.type, FOAF.Person)
    assert {first, second, third} == set(triples)


def test_encode_to_triple_link_one_item(registry: Registry) -> None:
    class Person(LinkedDataClass):
        __schema__ = Schema(
            rdf_resource=FOAF.Person,
            attrs={
                "firstName": FieldInfo(ref=FOAF.firstName),
                "birthday": FieldInfo(ref=FOAF.birthday, range=XSD.date),
                "knows": FieldInfo(ref=FOAF.knows, resource_ref=FOAF.Person, repeat=True),
            },
        )
        firstName: str
        birthday: datetime.date
        knows: list[str]

    me_id = URIRef("http://example.org/me")
    him_id = URIRef("http://example.org/him")
    me = Person(id=me_id, firstName="Me", birthday=datetime.date(2015, 10, 10), knows=[him_id])
    triples = DEFAULT_CODEC.encode_to_triple(me)
    first = (me_id, FOAF.firstName, Literal("Me"))
    second = (me_id, RDF.type, FOAF.Person)
    third = (me_id, FOAF.birthday, Literal(me.birthday))
    fourth = (me_id, FOAF.knows, him_id)
    assert {first, second, third, fourth} == set(triples)


def test_encode_to_triple_link_multiple_items(registry: Registry) -> None:
    class Person(LinkedDataClass):
        __schema__ = Schema(
            rdf_resource=FOAF.Person,
            attrs={
                "firstName": FieldInfo(ref=FOAF.firstName),
                "birthday": FieldInfo(ref=FOAF.birthday, range=XSD.date),
                "knows": FieldInfo(ref=FOAF.knows, resource_ref=FOAF.Person, repeat=True),
            },
        )
        firstName: str
        birthday: datetime.date
        knows: list[str]

    me_id = URIRef("http://example.org/me")
    him_id = URIRef("http://example.org/him")
    her_id = URIRef("http://example.org/her")
    me = Person(id=me_id, firstName="Me", birthday=datetime.date(2015, 10, 10), knows=[him_id, her_id])
    triples = DEFAULT_CODEC.encode_to_triple(me)
    first = (me_id, FOAF.firstName, Literal("Me"))
    second = (me_id, RDF.type, FOAF.Person)
    third = (me_id, FOAF.birthday, Literal(me.birthday))
    fourth = (me_id, FOAF.knows, him_id)
    fifth = (me_id, FOAF.knows, her_id)
    assert {first, second, third, fourth, fifth} == set(triples)


def test_encode_to_triple_invalid_repeat_annotation_raises(registry: Registry) -> None:
    class Person(LinkedDataClass):
        __schema__ = Schema(
            rdf_resource=FOAF.Person,
            attrs={
                "firstName": FieldInfo(ref=FOAF.firstName),
                "birthday": FieldInfo(ref=FOAF.birthday, range=XSD.date),
                "knows": FieldInfo(ref=FOAF.knows, resource_ref=FOAF.Person),
            },
        )
        firstName: str
        birthday: datetime.date
        knows: list[str]

    me_id = URIRef("http://example.org/me")
    him_id = URIRef("http://example.org/him")
    her_id = URIRef("http://example.org/her")
    me = Person(id=me_id, firstName="Me", birthday=datetime.date(2015, 10, 10), knows=[him_id, her_id])
    with pytest.raises(AnnotationError):
        triples = DEFAULT_CODEC.encode_to_triple(me)


def test_encode_to_triple_extra_fields(registry: Registry) -> None:
    registry.config = RegistryConfig(on_conflict_schema="overwrite")

    class Person(LinkedDataClass):
        __schema__ = Schema(rdf_resource=FOAF.Person, attrs={"firstName": FieldInfo(ref=FOAF.firstName)})
        firstName: str

    me_id = URIRef("http://example.org/me")
    data = {
        "id": me_id,
        "firstName": "Me",
        "birthday": datetime.date(1993, 1, 1),
    }

    me = DEFAULT_CODEC.decode_from_dict(
        data,
        Person,
    )

    class ExtPerson(LinkedDataClass):
        __schema__ = Schema(
            rdf_resource=FOAF.Person, attrs={"firstName": FieldInfo(ref=FOAF.firstName), "birthday": FieldInfo(ref=FOAF.birthday, range=XSD.date)}
        )
        firstName: str
        birthday: datetime.date

    triples = DEFAULT_CODEC.encode_to_triple(me)
    first = (me_id, FOAF.firstName, Literal("Me"))
    second = (me_id, RDF.type, FOAF.Person)
    third = (me_id, Literal("birthday"), Literal(datetime.date(1993, 1, 1)))
    assert {first, second, third} == set(triples)
