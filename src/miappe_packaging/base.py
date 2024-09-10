from __future__ import annotations

from typing import ClassVar, Type, Any, get_args, get_origin
from collections.abc import Sequence, Set, Mapping
from msgspec import Struct, Meta, field, UnsetType, UNSET
from rdflib import BNode, IdentifiedNode, URIRef
from rdflib.namespace import XSD
import datetime
from types import NoneType
from src.miappe_packaging.exceptions import AnnotationError
from src.miappe_packaging.utils import convert_to_ref, validate_schema


XSD_TO_PYTHON: dict[URIRef | Type, tuple[Type, Meta | None]] = {
    XSD.base64Binary: (bytes, None),
    XSD.boolean: (bool, None),
    XSD.byte: (bytes, None),
    XSD.date: (datetime.date, None),
    XSD.dateTime: (datetime.datetime, None),
    XSD.dateTimeStamp: (datetime.datetime, Meta(tz=True)),
    XSD.decimal: (float,),
    XSD.double: (float,),
    XSD.duration: (datetime.timedelta),
    XSD.float: (float,),
    XSD.int: (int,),
    XSD.integer: (int,),
    XSD.long: (int,),
    XSD.short: (int,),
    XSD.negativeInteger: (int, Meta(lt=0)),
    XSD.nonNegativeInteger: (int, Meta(ge=0)),
    XSD.nonPositiveInteger: (int, Meta(le=0)),
    XSD.positiveInteger: (int, Meta(gt=0)),
    XSD.time: (datetime.time,),
    XSD.string: (str,),
}

PYTHON_TO_XSD: dict[Type, URIRef] = {
    datetime.date: XSD.date,
    datetime.time: XSD.time,
    datetime.datetime: XSD.dateTime,
    str: XSD.string,
    int: XSD.integer,
    float: XSD.float,
    bytes: XSD.byte,
    bool: XSD.boolean,
    Any: XSD.string,
    None: None,
}


class IDRef(Struct):
    ref: URIRef


class FieldInfo(Struct):
    ref: URIRef
    range: URIRef | IDRef | None = None
    repeat: bool = False
    required: bool = True
    meta: Meta | None = None


class Schema(Struct):
    __rdf_resource__: URIRef
    attrs: dict[str, FieldInfo]

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


class LinkedDataClass(Struct, kw_only=True):
    """Base Linked DataClass

    Can be treated as a simple Python dataclass object.
    """

    id: str = field(default_factory=BNode)
    """Instance ID. If not provided, will be assigned a blank node ID"""
    __schema__: ClassVar[Schema]
    """Schema object. Class attribute"""
    __rdf_resource__: ClassVar[URIRef]
    __rdf_context__: ClassVar[URIRef] = URIRef("./")

    @property
    def ID(self) -> IdentifiedNode:
        """ID in rdflib Node format. String values are converted to URIRef using
        `rdflib.URIRef` callable. BNode and URIRef values are not modified.

        Returns:
            IdentifiedNode: id of current object.
        """
        return convert_to_ref(self.id)

    def __init_subclass__(cls) -> None:
        # Validate schema if schema is not provided
        if hasattr(cls, "__schema__"):
            try:
                validate_schema(cls, cls.__schema__)
            except AnnotationError as e:
                e.add_note(f"Class: {cls.__name__}")
                raise
        # Alternatively gather schema information from field annotation
        else:
            if not hasattr(cls, "__rdf_resource__"):
                raise AnnotationError(
                    f"either __rdf_resource__ or __schema__ must be provided. Class: {cls.__name__}"
                )
            annotations = cls.__annotations__
            attrs = {}
            for k, v in annotations.items():
                if k == "__rdf_resource__":
                    continue
                if not hasattr(v, "__metadata__"):
                    attrs[k] = field_info_from_annotations(
                        k,
                        cls.__name__,
                        v,
                        getattr(cls, "__rdf_context__", URIRef("./")),
                    )
                else:
                    metadata = getattr(v, "__metadata__")
                    for tp in metadata:
                        if isinstance(tp, FieldInfo):
                            attrs[k] = tp

            schema = Schema(
                __rdf_resource__=getattr(cls, "__rdf_resource__"), attrs=attrs
            )
            setattr(cls, "__schema__", schema)

        return super().__init_subclass__()


def field_info_from_annotations(
    field_name: str,
    class_name: str,
    annotation: Any,
    context: URIRef,
) -> FieldInfo:
    kwargs = {
        "ref": context + field_name,  # Set to field name
        "range": None,  # Obtained from PYTHON_TO_XSD dict
        "required": True,  # Set to False if type is Optional
        "repeat": False,  # Set to True if origin is list or tuple
    }
    if hasattr(annotation, "__args__"):
        base_type = set()
        for tp in get_args(annotation):
            if hasattr(tp, "__args__"):
                base_type.update(get_args(tp))
            else:
                base_type.add(tp)
        origins = {
            get_origin(tp) for tp in get_args(annotation) if hasattr(tp, "__origin__")
        }
        for origin in origins:
            if issubclass(origin, Sequence) or issubclass(origin, Set):
                kwargs["repeat"] = True
                continue
            if issubclass(origin, Mapping):
                raise TypeError(
                    f"Auto-annotated does not support mapping type. Type: {origin} is not supported. Class: {class_name}, field: {field_name}"
                )
        if len(base_type) >= 2 and NoneType not in base_type:
            raise AnnotationError(
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
        kwargs["range"] = PYTHON_TO_XSD[annotation]
    return FieldInfo(**kwargs)
