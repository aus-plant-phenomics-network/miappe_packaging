from __future__ import annotations

import datetime
from collections.abc import Mapping, Sequence, Set
from types import NoneType
from typing import Any, Type, get_args, get_origin

from msgspec import Meta
from rdflib import BNode, IdentifiedNode, URIRef
from rdflib.namespace import XSD

from src.miappe_packaging.exceptions import AnnotationError
from src.miappe_packaging.schema import FieldInfo, Schema

__all__ = (
    "bnode_factory",
    "field_info_from_annotations",
    "get_key_or_attribute",
    "make_ref",
    "validate_schema",
)


XSD_TO_PYTHON: dict[
    URIRef,
    tuple[
        Type,
        Meta | None,
    ],
] = {
    XSD.base64Binary: (bytes, None),
    XSD.boolean: (bool, None),
    XSD.byte: (bytes, None),
    XSD.date: (datetime.date, None),
    XSD.dateTime: (datetime.datetime, None),
    XSD.dateTimeStamp: (datetime.datetime, Meta(tz=True)),
    XSD.decimal: (float, None),
    XSD.double: (float, None),
    XSD.duration: (datetime.timedelta, None),
    XSD.float: (float, None),
    XSD.int: (int, None),
    XSD.integer: (int, None),
    XSD.long: (int, None),
    XSD.short: (int, None),
    XSD.negativeInteger: (int, Meta(lt=0)),
    XSD.nonNegativeInteger: (int, Meta(ge=0)),
    XSD.nonPositiveInteger: (int, Meta(le=0)),
    XSD.positiveInteger: (int, Meta(gt=0)),
    XSD.time: (datetime.time, None),
    XSD.string: (str, None),
}

PYTHON_TO_XSD: dict[Type | Any, URIRef] = {
    datetime.date: XSD.date,
    datetime.time: XSD.time,
    datetime.datetime: XSD.dateTime,
    str: XSD.string,
    int: XSD.integer,
    float: XSD.float,
    bytes: XSD.byte,
    bool: XSD.boolean,
    Any: XSD.string,
    None: None,  # type: ignore [dict-item, index]
}


def bnode_factory() -> URIRef:
    return URIRef("./localID/" + str(BNode()))


def make_ref(identifier: IdentifiedNode | str | None = None) -> IdentifiedNode:
    if not identifier:
        return bnode_factory()
    if isinstance(identifier, BNode):
        if not identifier.startswith("./localID"):
            return URIRef("./localID/" + identifier)
        return URIRef(identifier)
    if isinstance(identifier, URIRef):
        return identifier
    if isinstance(identifier, str):
        return URIRef(identifier)
    raise TypeError(f"Invalid type: {type(identifier)}")


def get_key_or_attribute(
    field: str, obj: Any, raise_error_if_missing: bool = False
) -> Any:
    if hasattr(obj, field):
        return getattr(obj, field)
    if isinstance(obj, dict) and field in obj:
        return obj.get(field)
    if raise_error_if_missing:
        raise KeyError(f"Object has no key: {field}")
    return None


def validate_schema(obj: Any, schema: Schema) -> None:
    """Check that the schema's attribute keys are the same as object's attribute keys

    Args:
        obj (Any): obj for validation
        schema (Schema): object schema. Should have attrs whose keys match the attributes of obj

    Raises:
        AnnotationError: if there are keys in obj and not in schema and vice versa
    """
    if schema is None:
        raise ValueError("Schema must be provided")
    if isinstance(obj, dict):
        obj_fields = set(obj.keys())
    elif hasattr(obj, "__annotations__"):
        obj_fields = set(obj.__annotations__)
    else:
        raise TypeError(
            "object must either be a dictionary or a class with type annotation"
        )
    schema_fields = set(schema.attrs.keys())
    obj_fields.discard("id")
    schema_fields.discard("id")
    if obj_fields != schema_fields:
        raise AnnotationError(
            f"Attributes and schema keys don't match. Symmetric difference: {schema_fields ^ obj_fields}"
        )


def field_info_from_annotations(
    field_name: str,
    class_name: str,
    annotation: Any,
    context: URIRef,
) -> FieldInfo:
    kwargs = {
        "ref": URIRef(context + field_name),  # Set to field name
        "range": None,  # Obtained from PYTHON_TO_XSD dict
        "required": True,  # Set to False if type is Optional
        "repeat": False,  # Set to True if origin is list or tuple
    }
    if hasattr(annotation, "__args__"):
        base_type: set[Type] = set()
        origins: set[Type] = set()
        if hasattr(annotation, "__origin__") and isinstance(
            get_origin(annotation), type
        ):
            origins.add(get_origin(annotation))
        for tp in get_args(annotation):
            if hasattr(tp, "__args__"):
                base_type.update(get_args(tp))
            else:
                base_type.add(tp)

            if hasattr(tp, "__origin__") and isinstance(get_origin(tp), type):
                origins.add(get_origin(tp))

        for origin in origins:
            if issubclass(origin, Sequence) or issubclass(origin, Set):
                kwargs["repeat"] = True
                break
            if issubclass(origin, Mapping):
                raise TypeError(
                    f"Auto-annotated does not support mapping type. Type: {origin} is not supported. Class: {class_name}, field: {field_name}"
                )
        if len(base_type) == 2 and NoneType not in base_type or len(base_type) > 2:
            raise TypeError(
                f"Composite type accepts a base type and a NoneType only. Class: {class_name}, field: {field_name}"
            )
        for tp in base_type:
            if tp is NoneType:
                kwargs["required"] = False
                continue
            if tp not in PYTHON_TO_XSD:
                raise TypeError(
                    f"Auto-annotation supports only common base type. Type: {tp} is not supported. Class: {class_name}, field: {field_name}"
                )
            kwargs["range"] = PYTHON_TO_XSD[tp]
    else:  # Not a parameterized type
        if annotation not in PYTHON_TO_XSD:
            raise TypeError(
                f"Auto-annotation supports only common base type. Type: {annotation} is not supported. Class: {class_name}, field: {field_name}"
            )
        if annotation is None:
            kwargs["required"] = False
        kwargs["range"] = PYTHON_TO_XSD[annotation]
    return FieldInfo(**kwargs)  # type: ignore[arg-type]
