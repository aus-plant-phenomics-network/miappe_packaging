from __future__ import annotations
from rdflib import URIRef, IdentifiedNode, Namespace
from types import NoneType
from msgspec import Struct, Meta
from typing import Type, Any, Protocol, ClassVar, Optional, get_args, get_origin
from collections.abc import Mapping, Sequence, Set
from dataclasses import Field
from rdflib.namespace import XSD
import datetime

XSD_TO_PYTHON: dict[
    URIRef,
    tuple[Type, Optional[Meta]],
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


class AnnotatedP(Protocol):
    """Protocol that has __annotations__ field"""

    __annotations__: ClassVar[dict[str, Type]]


class DataClassP(AnnotatedP, Protocol):
    """Native python dataclass protocol. Must have __dataclass_fields__ field"""

    __dataclass_fields__: ClassVar[dict[str, Field]]


class StructP(AnnotatedP, Protocol):
    """msgspec.Struct protocol. Must have __struct_fields__ field"""

    __struct_fields__: ClassVar[tuple[str, ...]]


DataClassT = dict[str, Any] | AnnotatedP | DataClassP | StructP
"""Schema-less dataclass/struct/dict"""


class LinkedDataClassP(StructP, Protocol):
    """Struct dataclass with accompanied schema information"""

    @property
    def schema(self) -> Schema: ...

    @property
    def rdf_resource(self) -> URIRef: ...


NodeT = IdentifiedNode | str
FieldSetT = set[str]


class IDRef(Struct):
    """Add metadata to the range attribute of FieldInfo.

    FieldInfo with IDRef attribute means that the field references
    an object of type ref.
    """

    ref: URIRef
    """Type of referenced object in rdf.property term"""


class FieldInfo(Struct):
    """Field property information"""

    ref: URIRef
    """Predicate reference. Used for serialising to rdf triples"""
    range: URIRef | IDRef | None = None
    """Range reference - will be used to serialise object literal."""
    repeat: bool = False
    """Whether the attribute takes on multiple values. Used for validation"""
    required: bool = True
    """Whether the attribute is required. Used for validation """
    meta: Meta | None = None
    """Additional validation information as `msgspec.Meta` object"""

    @classmethod
    def from_annotations(
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


class Schema(Struct):
    """
    Schema object that provides properties information for
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
        return set([k for k, v in self.attrs.items() if v.required])
