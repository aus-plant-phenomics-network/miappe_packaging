from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Protocol, Self, _SpecialForm, runtime_checkable

from pydantic import (
    BaseModel,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    ValidationError,
    model_validator,
)
from pydantic import (
    Field as PydanticField,
)
from pydantic_core import core_schema
from rdflib import BNode as _BNode
from rdflib import URIRef as _URIRef
from rdflib.namespace import XSD

if TYPE_CHECKING:
    from dataclasses import Field as DataclassField

    from pydantic.fields import FieldInfo as PydanticFieldInfo
    from pydantic.json_schema import JsonSchemaValue

__all__ = (
    "AnnotatedP",
    "BNodePydanticWrapper",
    "DataClassP",
    "FieldInfo",
    "LinkedDataClassP",
    "PydanticModel",
    "Schema",
    "URIRefPydanticWrapper",
)


class URIRefPydanticWrapper:
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        def validate_from_str(value: str) -> _URIRef:
            if value.startswith("_:"):
                raise ValueError(f"BNode value provided: {value}")
            return _URIRef(value)

        from_str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(validate_from_str),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=core_schema.union_schema(
                [
                    # check if it's an instance first before doing any further work
                    core_schema.is_instance_schema(_URIRef),
                    from_str_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda instance: instance.toPython()),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        # Use the same schema that would be used for `str`
        return handler(core_schema.str_schema())


class BNodePydanticWrapper:
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        def validate_from_str(value: str) -> _BNode:
            if not value.startswith("_:"):
                raise ValidationError(f"BNode value must start with ':_', provided: {value}")
            return _BNode(value)

        from_str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(validate_from_str),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=core_schema.union_schema(
                [
                    # check if it's an instance first before doing any further work
                    core_schema.is_instance_schema(_BNode),
                    from_str_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda instance: instance.toPython()),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        # Use the same schema that would be used for `str`
        return handler(core_schema.str_schema())


URIRef = Annotated[_URIRef, URIRefPydanticWrapper]
BNode = Annotated[_BNode, BNodePydanticWrapper]
IdentifiedNode = URIRef | BNode

XSD_TO_PYTHON: dict[URIRef, type | _SpecialForm] = {
    XSD.base64Binary: bytes,
    XSD.boolean: bool,
    XSD.byte: bytes,
    XSD.date: datetime.date,
    XSD.dateTime: datetime.datetime,
    XSD.dateTimeStamp: datetime.datetime,
    XSD.decimal: float,
    XSD.double: float,
    XSD.duration: datetime.timedelta,
    XSD.float: float,
    XSD.int: int,
    XSD.integer: int,
    XSD.long: int,
    XSD.short: int,
    XSD.negativeInteger: Annotated[int, PydanticField(lt=0)],
    XSD.nonNegativeInteger: Annotated[int, PydanticField(ge=0)],
    XSD.nonPositiveInteger: Annotated[int, PydanticField(le=0)],
    XSD.positiveInteger: Annotated[int, PydanticField(gt=0)],
    XSD.time: datetime.time,
    XSD.string: str,
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

    __dataclass_fields__: ClassVar[dict[str, DataclassField]]


@runtime_checkable
class PydanticModel(AnnotatedP, Protocol):
    """PydanticModel protocol. Must have fields"""

    model_fields: dict[str, PydanticFieldInfo]


DataClassT = dict[str, Any] | AnnotatedP | DataClassP | PydanticModel
"""Schema-less dataclass/struct/dict"""


@runtime_checkable
class LinkedDataClassP(PydanticModel, Protocol):
    """Struct dataclass with accompanied schema information"""

    @property
    def schema(self) -> Schema: ...

    @property
    def rdf_resource(self) -> URIRef: ...


NodeT = IdentifiedNode | str
FieldSetT = set[str]


class FieldInfo(BaseModel):
    """Field property information"""

    ref: URIRef
    """Predicate reference. Used for serializing to rdf triples"""
    range: URIRef | None = None
    """Range reference - will be used to serialise object literal."""
    resource_ref: URIRef | None = None
    """When the range is XSD.IDRef type, the field describe the resource being referenced"""
    repeat: bool = False
    """Whether the attribute takes on multiple values. Used for validation"""
    required: bool = True
    """Whether the attribute is required. Used for validation """

    @model_validator(mode="after")
    def check_range_and_resource_ref(self) -> Self:
        """Validate range and resource_ref fields in FieldInfo

        If `resource_ref` is not None, range must be either XSD.IDREF or None

        Raises:
            ValueError: if `resource_ref` is provided and `range` is not XSD.IDREF

        Returns:
            Self: instance
        """
        if isinstance(self.resource_ref, _URIRef):
            if not self.range or self.range == XSD.IDREF:
                self.range = XSD.IDREF
            else:
                raise ValueError("If a resource reference is provided, range must be a None or XSD.IDREF")
        return self


class Schema(BaseModel):
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
