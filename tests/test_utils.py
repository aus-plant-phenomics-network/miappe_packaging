import datetime
from typing import Any, Optional, Type, Union

import pytest
from rdflib import URIRef
from rdflib.namespace import XSD

from src.miappe_packaging.schema import FieldInfo
from src.miappe_packaging.utils import field_info_from_annotations


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
        context=URIRef("./"),
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
        context=URIRef("./"),
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
        context=URIRef("./"),
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
def test_get_field_info_expects_error_composite_type(annotation: Type) -> None:
    with pytest.raises(TypeError):
        field_info_from_annotations(
            field_name="name",
            class_name="Class",
            annotation=annotation,
            context=URIRef("./"),
        )


def test_get_field_info_expects_error_dict_type() -> None:
    with pytest.raises(TypeError):
        field_info_from_annotations(
            field_name="name",
            class_name="Class",
            annotation=dict[str, Any],
            context=URIRef("./"),
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
def test_get_field_info_expects_error_non_base_type(annotation: Type) -> None:
    with pytest.raises(TypeError):
        field_info_from_annotations(
            field_name="name",
            class_name="Class",
            annotation=annotation,
            context=URIRef("./"),
        )
