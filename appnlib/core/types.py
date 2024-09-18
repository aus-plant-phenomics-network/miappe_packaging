from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, runtime_checkable

from msgspec import Meta, Struct
from rdflib import IdentifiedNode, URIRef
from rdflib.namespace import XSD

if TYPE_CHECKING:
    from dataclasses import Field

__all__ = (
    "AnnotatedP",
    "DataClassP",
    "FieldInfo",
    "LinkedDataClassP",
    "Schema",
    "StructP",
)


XSD_TO_PYTHON: dict[
    URIRef,
    tuple[type, Meta | None],
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

PYTHON_TO_XSD: dict[type | Any, URIRef] = {
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


@runtime_checkable
class AnnotatedP(Protocol):
    """Protocol that has __annotations__ field"""

    __annotations__: dict[str, type]


@runtime_checkable
class DataClassP(AnnotatedP, Protocol):
    """Native python dataclass protocol. Must have __dataclass_fields__ field"""

    __dataclass_fields__: ClassVar[dict[str, Field]]


@runtime_checkable
class StructP(AnnotatedP, Protocol):
    """msgspec.Struct protocol. Must have __struct_fields__ field"""

    __struct_fields__: ClassVar[tuple[str, ...]]


DataClassT = dict[str, Any] | AnnotatedP | DataClassP | StructP
"""Schema-less dataclass/struct/dict"""


@runtime_checkable
class LinkedDataClassP(StructP, Protocol):
    """Struct dataclass with accompanied schema information"""

    @property
    def schema(self) -> Schema: ...

    @property
    def rdf_resource(self) -> URIRef: ...


NodeT = IdentifiedNode | str
FieldSetT = set[str]


class FieldInfo(Struct):
    """Field property information"""

    ref: URIRef
    """Predicate reference. Used for serialising to rdf triples"""
    range: URIRef | None = None
    """Range reference - will be used to serialise object literal."""
    resource_ref: URIRef | None = None
    """When the range is XSD.IDRef type, the field describe the resource being referenced"""
    repeat: bool = False
    """Whether the attribute takes on multiple values. Used for validation"""
    required: bool = True
    """Whether the attribute is required. Used for validation """
    meta: Meta | None = None
    """Additional validation information as `msgspec.Meta` object"""

    def __post_init__(self) -> None:
        if isinstance(self.resource_ref, URIRef):
            if not self.range or self.range == XSD.IDREF:
                self.range = XSD.IDREF
            else:
                raise ValueError("If a resource reference is provided, range must be a None or XSD.IDREF")


class Schema(Struct):
    """Schema object that provides properties information for
    attributes of a `LinkedDataClass`.
    """

    rdf_resource: URIRef
    """Reference to rdf resource of the LinkedDataClass"""
    attrs: dict[str, FieldInfo]
    """Mapping between field name and field info"""

    @property
    def name_mapping(self) -> dict[str, FieldInfo]:
        """Mapping from name to field information

        Returns:
            dict[str, FieldInfo]: returned object
        """
        return self.attrs

    @property
    def ref_mapping(self) -> dict[URIRef, str]:
        """Mapping from field reference to field name

        Returns:
            dict[URIRef, str]: returned object
        """
        return {item.ref: name for name, item in self.attrs.items()}

    @property
    def fields(self) -> FieldSetT:
        """Get all attributes defined in the schema

        Returns:
            FieldSet: set of attributes defined in schema
        """
        return set(self.attrs.keys())

    @property
    def required(self) -> FieldSetT:
        """Get required fields from schema

        Returns:
            FieldSet: set of required fields in schema
        """
        return {k for k, v in self.attrs.items() if v.required}
