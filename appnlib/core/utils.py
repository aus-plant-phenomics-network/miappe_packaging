from __future__ import annotations

import datetime
from collections.abc import Mapping, Sequence, Set
from types import NoneType
from typing import Any, Type, get_args, get_origin

from msgspec import Meta
from rdflib import BNode, IdentifiedNode, URIRef, Namespace
from rdflib.namespace import XSD

from appnlib.core.exceptions import AnnotationError
from appnlib.core.schema import FieldInfo, Schema


__all__ = (
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


def make_ref(identifier: IdentifiedNode | str | None = None) -> IdentifiedNode:
    """Create a Node reference

    If identifier is a `URIRef` or `BNode`, the function will return identifier as is. If the identifier is a string,
    depending on whether it starts with `_:`, the function will return a `BNode` or `URIRef` with the identifier
    value. If not provided, the function will generate and return a BNode

    Args:
        identifier (IdentifiedNode | str | None, optional): identifier value. Defaults to None.

    Raises:
        TypeError: if identifier is not a string or not IdentifiedNode or BNode type.

    Returns:
        IdentifiedNode: identifier as `IdentifiedNode` type
    """
    if identifier is None:
        return BNode()
    if isinstance(identifier, IdentifiedNode):
        return identifier
    if isinstance(identifier, str):
        if identifier.startswith("_:"):
            return BNode(identifier[2:])
        return URIRef(identifier)
    raise TypeError(f"Invalid type: {type(identifier)}")


def get_key_or_attribute(
    field: str, obj: Any, raise_error_if_missing: bool = False
) -> Any:
    """From an object, attempt to get key if object is dict like otherwise get attribute.

    Read obj.get(field) then try getattr(obj, field)

    Args:
        field (str): key/attribute name
        obj (Any): object to extract key/attribute from
        raise_error_if_missing (bool, optional): whether to raise if the field is missing. Defaults to False.

    Raises:
        KeyError: If the object has no key or attribute with the name field

    Returns:
        Any: the key/attribute value if they exist, or None if they don't and `raise_error_if_missing` is False
    """
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
    context: Namespace,
) -> FieldInfo:
    """Gather `FieldInfo` from provided annotation.

    - `ref`: derived from context and field_name. For instance, if context if FOAF, field_name is firstName, ref will be
    `FOAF.firstName`
    - `range`: derived from annotation type. Range will be mapped between an acceptable python type and and XSD URIRef
    - `required`: derived from annotation type. Whether the annotation is a Union with None
    - `repeat`: derived from annotation type. Whether the annotation origin is a `Sequence` or `Set`

    Annotation must be a native python type, a Sequence (`list`/`tuple`) or a Set (`set`)
    of native python types. Native python types are `datetime.date`, `datetime.time`, `datetime.datetime`,
    `str`, `int`, `float`, `bytes`, `bool`, `Any`, `None`

    Args:
        field_name (str): name of the field - for error reporting purposes and for deriving ref
        class_name (str): name of the class - for error reporting purposes
        annotation (Any): field annotation
        context (Namespace): a namespace that has field_name as a member

    Raises:
        TypeError: if the annotated type is not a python native type.
        TypeError: if annotation origin (for Generics) are not Sequence or Set
        TypeError: if union type is not between a native/native/list/set and a None. Union with more than 2 types are not accepted


    Returns:
        FieldInfo: parsed field info
    """
    kwargs = {
        "ref": context[field_name],  # Set to field name
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
                f"Union type accepts a base type and a NoneType only. Class: {class_name}, field: {field_name}"
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
