import datetime
from dataclasses import dataclass
from typing import Any, Optional, Type, Union

import pytest
from rdflib import BNode, IdentifiedNode, URIRef, Namespace
from rdflib.namespace import FOAF, XSD

from appnlib.core.exceptions import AnnotationError
from appnlib.core.schema import FieldInfo, IDRef, Schema
from appnlib.core.utils import (
    field_info_from_annotations,
    get_key_or_attribute,
    make_ref,
    validate_schema,
)
from tests.fixture import (
    Group,
    Obama,
    ObamaDataClass,
    ObamaDict,
    ObamaNamedTuple,
    ObamaTypedDict,
    Presidents,
    VicePresidents,
)


class ThirdPartyType:
    pass


@pytest.mark.parametrize(
    "annotation, info",
    [
        (int, FieldInfo(ref=URIRef("./name"), range=XSD.integer, required=True)),
        (float, FieldInfo(ref=URIRef("./name"), range=XSD.float, required=True)),
        (str, FieldInfo(ref=URIRef("./name"), range=XSD.string, required=True)),
        (Any, FieldInfo(ref=URIRef("./name"), range=XSD.string, required=True)),
        (
            datetime.date,
            FieldInfo(ref=URIRef("./name"), range=XSD.date, required=True),
        ),
        (
            datetime.datetime,
            FieldInfo(ref=URIRef("./name"), range=XSD.dateTime, required=True),
        ),
        (
            datetime.time,
            FieldInfo(ref=URIRef("./name"), range=XSD.time, required=True),
        ),
        (
            bool,
            FieldInfo(ref=URIRef("./name"), range=XSD.boolean, required=True),
        ),
        (None, FieldInfo(ref=URIRef("./name"), required=False)),
    ],
)
def test_get_field_info_basic_type(annotation: Type, info: FieldInfo) -> None:
    parsed_info = field_info_from_annotations(
        field_name="name",
        class_name="Test",
        annotation=annotation,
        context=Namespace("./"),
    )
    assert parsed_info == info


@pytest.mark.parametrize(
    "annotation, info",
    [
        (
            int | None,
            FieldInfo(ref=URIRef("./name"), range=XSD.integer, required=False),
        ),
        (
            Optional[float],
            FieldInfo(ref=URIRef("./name"), range=XSD.float, required=False),
        ),
        (None | str, FieldInfo(ref=URIRef("./name"), range=XSD.string, required=False)),
        (None, FieldInfo(ref=URIRef("./name"), required=False)),
        (
            datetime.date | None,
            FieldInfo(ref=URIRef("./name"), range=XSD.date, required=False),
        ),
        (
            Union[datetime.datetime, None],
            FieldInfo(ref=URIRef("./name"), range=XSD.dateTime, required=False),
        ),
        (
            Optional[datetime.time],
            FieldInfo(ref=URIRef("./name"), range=XSD.time, required=False),
        ),
        (
            bool | None,
            FieldInfo(ref=URIRef("./name"), range=XSD.boolean, required=False),
        ),
    ],
)
def test_get_field_info_optional(annotation: Type, info: FieldInfo) -> None:
    parsed_info = field_info_from_annotations(
        field_name="name",
        class_name="Test",
        annotation=annotation,
        context=Namespace("./"),
    )
    assert parsed_info == info


@pytest.mark.parametrize(
    "annotation, info",
    [
        (
            list[int],
            FieldInfo(
                ref=URIRef("./name"), range=XSD.integer, required=True, repeat=True
            ),
        ),
        (
            Optional[float] | list[float],
            FieldInfo(
                ref=URIRef("./name"), range=XSD.float, required=False, repeat=True
            ),
        ),
        (
            None | list[datetime.datetime],
            FieldInfo(
                ref=URIRef("./name"), range=XSD.dateTime, required=False, repeat=True
            ),
        ),
        (
            set[bool] | bool,
            FieldInfo(
                ref=URIRef("./name"), range=XSD.boolean, required=True, repeat=True
            ),
        ),
        (
            set[datetime.time | None],
            FieldInfo(
                ref=URIRef("./name"), range=XSD.time, required=False, repeat=True
            ),
        ),
        (
            str | list[str] | None,
            FieldInfo(
                ref=URIRef("./name"), range=XSD.string, required=False, repeat=True
            ),
        ),
    ],
)
def test_get_field_info_sequence(annotation: Type, info: FieldInfo) -> None:
    parsed_info = field_info_from_annotations(
        field_name="name",
        class_name="Test",
        annotation=annotation,
        context=Namespace("./"),
    )
    assert parsed_info == info


@pytest.mark.parametrize(
    "annotation",
    [
        (int | str),
        (tuple[int, str]),
        (list[int] | float),
        (datetime.date | datetime.datetime | datetime.time),
        (int | str | float | None),
    ],
)
def test_get_field_info_composite_type_raises(annotation: Type) -> None:
    with pytest.raises(TypeError):
        field_info_from_annotations(
            field_name="name",
            class_name="Class",
            annotation=annotation,
            context=Namespace("./"),
        )


def test_get_field_info_dict_type_raises() -> None:
    with pytest.raises(TypeError):
        field_info_from_annotations(
            field_name="name",
            class_name="Class",
            annotation=dict[str, Any],
            context=Namespace("./"),
        )


@pytest.mark.parametrize(
    "annotation",
    [
        (ThirdPartyType),
        (ThirdPartyType | None),
        (Optional[ThirdPartyType]),
        (list[ThirdPartyType]),
        (set[ThirdPartyType]),
    ],
)
def test_get_field_info_non_base_type_raises(annotation: Type) -> None:
    with pytest.raises(TypeError):
        field_info_from_annotations(
            field_name="name",
            class_name="Class",
            annotation=annotation,
            context=Namespace("./"),
        )


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
    ref = make_ref()
    assert isinstance(ref, BNode)


@pytest.mark.parametrize("ref", [(1.0), ([1, 2, 3])])
def test_invalid_make_ref_raises(ref: Any) -> None:
    with pytest.raises(TypeError):
        make_ref(ref)


def test_validate_schema_valid() -> None:
    @dataclass
    class Person:
        first_name: str
        last_name: str
        knows: list[str]

    schema = Schema(
        __rdf_resource__=FOAF.Person,
        attrs={
            "first_name": FieldInfo(FOAF.firstName),
            "last_name": FieldInfo(FOAF.lastName),
            "knows": FieldInfo(FOAF.knows, range=IDRef(FOAF.Person), repeat=True),
        },
    )
    try:
        validate_schema(Person, schema)
    except Exception:
        raise


def test_validate_schema_invalid_missing_fields_raises() -> None:
    @dataclass
    class Person:
        first_name: str
        last_name: str
        knows: list[str]

    schema = Schema(
        __rdf_resource__=FOAF.Person,
        attrs={
            "first_name": FieldInfo(FOAF.firstName),
            "last_name": FieldInfo(FOAF.lastName),
            "age": FieldInfo(FOAF.age, range=XSD.positiveInteger),
            "knows": FieldInfo(FOAF.knows, range=IDRef(FOAF.Person), repeat=True),
        },
    )
    with pytest.raises(AnnotationError):
        validate_schema(Person, schema)


@pytest.mark.parametrize(
    "instance, name",
    [
        (Obama, "ID"),
        (ObamaDict, "id"),
        (ObamaTypedDict, "birthday"),
        (ObamaDataClass, "firstName"),
        (ObamaNamedTuple, "knows"),
    ],
)
def test_get_key_or_attribute(instance: Any, name: str) -> None:
    value = get_key_or_attribute(name, instance)
    assert value == getattr(Obama, name)


@pytest.mark.parametrize(
    "instance, name",
    [
        (Obama, "IDx"),
        (ObamaDict, "idx"),
        (ObamaTypedDict, "birthdayx"),
        (ObamaDataClass, "firstNamex"),
        (ObamaNamedTuple, "knowsx"),
    ],
)
def test_get_key_or_attribute_no_raise(instance: Any, name: str) -> None:
    value = get_key_or_attribute(name, instance, raise_error_if_missing=False)
    assert value is None


@pytest.mark.parametrize(
    "instance, name",
    [
        (Obama, "IDx"),
        (ObamaDict, "idx"),
        (ObamaTypedDict, "birthdayx"),
        (ObamaDataClass, "firstNamex"),
        (ObamaNamedTuple, "knowsx"),
    ],
)
def test_get_key_or_attribute_raises(instance: Any, name: str) -> None:
    with pytest.raises(KeyError):
        get_key_or_attribute(name, instance, raise_error_if_missing=True)


@pytest.mark.parametrize(
    "instance, schema",
    [
        (ObamaDataClass, Obama.__schema__),
        (ObamaDict, Obama.__schema__),
        (ObamaNamedTuple, Obama.__schema__),
        (ObamaTypedDict, Obama.__schema__),
    ],
)
def test_validate_schema_non_linked_dataclass(instance: Any, schema: Schema) -> None:
    try:
        validate_schema(instance, schema)
    except Exception:
        raise


@pytest.mark.parametrize(
    "instance, schema",
    [
        (ObamaDataClass, Group.__schema__),
        (ObamaDict, Presidents.__schema__),
        (ObamaNamedTuple, VicePresidents.__schema__),
        (ObamaTypedDict, Group.__schema__),
    ],
)
def test_validate_schema_non_linked_dataclass_wrong_schema_raises(
    instance: Any, schema: Schema
) -> None:
    with pytest.raises(AnnotationError):
        validate_schema(instance, schema)


@pytest.mark.parametrize(
    "instance",
    [
        (ObamaDataClass),
        (ObamaDict),
        (ObamaNamedTuple),
        (ObamaTypedDict),
    ],
)
def test_validate_schema_non_linked_dataclass_no_schema_raises(instance: Any) -> None:
    with pytest.raises(ValueError):
        validate_schema(instance, None)  # type: ignore[arg-type]


def test_validate_schema_invalid_object_raises() -> None:
    obama_tuple = ((k, v) for k, v in ObamaDict.items())
    with pytest.raises(TypeError):
        validate_schema(obama_tuple, Obama.__schema__)
