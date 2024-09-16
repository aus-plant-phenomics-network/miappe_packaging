from dataclasses import dataclass
from typing import Any, NamedTuple, TypedDict

import pytest
from msgspec import Struct
from rdflib import BNode, IdentifiedNode, URIRef

from appnlib.core.utils import (
    get_key_or_attribute,
    make_ref,
)


class PersonStruct(Struct):
    name: str
    age: int


@dataclass
class PersonDataClass:
    name: str
    age: int


class PersonTuple(NamedTuple):
    name: str
    age: int


class PersonTypedDict(TypedDict):
    name: str
    age: int


class PersonClass:
    def __init__(self, age: int, name: str) -> None:
        self.age = age
        self.name = name


MeStruct = PersonStruct(name="me", age=10)
MeDC = PersonDataClass(name="me", age=10)
MeDict = {"name": "me", "age": 10}
MeTuple = PersonTuple(name="me", age=10)
MeTypedDict = PersonTypedDict(name="me", age=10)
MeClass = PersonClass(name="me", age=10)


@pytest.mark.parametrize(
    "ref, exp",
    [
        # String converted to URIRef
        (
            "http://example.org/dog",
            URIRef("http://example.org/dog"),
        ),
        # String converted to BNode
        ("_:http://example.org/dog", BNode("http://example.org/dog")),
        # URIRef kept as is
        (
            URIRef("http://example.org/dog"),
            URIRef("http://example.org/dog"),
        ),
        # BNode kept as is
        (BNode("1001"), BNode("1001")),
    ],
)
def test_make_ref(ref: str | IdentifiedNode, exp: URIRef) -> None:
    parsed_ref = make_ref(ref)
    assert parsed_ref == exp


def test_make_ref_factory() -> None:
    # Creates BNode
    ref = make_ref()
    assert isinstance(ref, BNode)


@pytest.mark.parametrize("ref", [(1.0), ([1, 2, 3])])
def test_invalid_make_ref_raises(ref: Any) -> None:
    # Invalid type raises
    with pytest.raises(TypeError):
        make_ref(ref)


@pytest.mark.parametrize(
    "instance, name",
    [
        (MeDC, "name"),
        (MeStruct, "name"),
        (MeTuple, "name"),
        (MeDict, "name"),
        (MeTypedDict, "name"),
        (MeClass, "name"),
    ],
)
def test_get_key_or_attribute(instance: Any, name: str) -> None:
    value = get_key_or_attribute(name, instance)
    assert value == "me"


@pytest.mark.parametrize(
    "instance, name",
    [
        (MeDC, "name_x"),
        (MeStruct, "name_x"),
        (MeTuple, "name_x"),
        (MeDict, "name_x"),
        (MeTypedDict, "name_x"),
        (MeClass, "name_x"),
    ],
)
def test_get_key_or_attribute_invalid_raises(instance: Any, name: str) -> None:
    with pytest.raises(KeyError):
        get_key_or_attribute(name, instance, raise_error_if_missing=True)


@pytest.mark.parametrize(
    "instance, name",
    [
        (MeDC, "name_x"),
        (MeStruct, "name_x"),
        (MeTuple, "name_x"),
        (MeDict, "name_x"),
        (MeTypedDict, "name_x"),
        (MeClass, "name_x"),
    ],
)
def test_get_key_or_attribute_no_raise(instance: Any, name: str) -> None:
    value = get_key_or_attribute(name, instance)
    assert value is None
