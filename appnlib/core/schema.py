from __future__ import annotations
from msgspec import Meta, Struct
from rdflib import URIRef, BNode, Namespace
from typing import Protocol, Literal, Callable, Any

from appnlib.core.exceptions import ValidationError

__all__ = (
    "FieldInfo",
    "IDRef",
    "Schema",
)


class HasSchema(Protocol):
    @property
    def schema(self) -> Schema: ...


NodeT = BNode | URIRef | str
AttrsT = dict[str, Any] | HasSchema
FieldSet = set[str]
UnannotatedStrategyT = Literal["ignore", "raise", "coerce"]
CoerceMethodT = Namespace | Callable[[str], URIRef]


class IDRef(Struct):
    ref: URIRef


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
    def fields(self) -> FieldSet:
        """Get all attributes defined in the schema

        Returns:
            FieldSet: set of attributes defined in schema
        """
        return set(self.attrs.keys())

    @property
    def required(self) -> FieldSet:
        """Get required fields from schema

        Returns:
            FieldSet: set of required fields in schema
        """
        return set([k for k, v in self.attrs.items() if v.required])


class SchemaValidator:
    @staticmethod
    def compatible(src: Schema, dst: Schema) -> None:
        """Assert that two schemas are compatible.

        Two schemas are compatible if they describe the same resource - i.e. having the
        same `rdf_resource`

        Args:
            src (Schema): src schema
            dst (Schema): dst schema

        Raises:
            ValidationError: if src and dst have different resources
        """
        if src.rdf_resource != dst.rdf_resource:
            raise ValidationError(
                f"Schemas describing different resources: {src.rdf_resource} != {dst.rdf_resource}"
            )

    @staticmethod
    def equal(src_fields: FieldSet, dst_fields: FieldSet) -> None:
        """Validate that two field sets are equal

        Args:
            src_fields (FieldSet): src fields
            dst_fields (FieldSet): dst fields

        Raises:
            ValidationError: if there is a field in src but not in dst and vice versa
        """
        if src_fields != dst_fields:
            raise ValidationError(
                f"Different required fields. In src: {src_fields - dst_fields}. In dst: {dst_fields - src_fields}"
            )

    @staticmethod
    def subset(src_fields: FieldSet, dst_fields: FieldSet) -> None:
        """Check if src fields is a subset of dst fields

        Args:
            src_fields (FieldSet): set of src fields
            dst_fields (FieldSet): set of dst fields

        Raises:
            ValidationError: if there are fields in src_fields but not in dst_fields
        """
        if not src_fields.issubset(dst_fields):
            raise ValidationError(f"Not a subset. In src: {src_fields - dst_fields}")

    @staticmethod
    def is_valid_extension(src: Schema, dst: Schema) -> None:
        """Validate that dst schema is a valid extension of src schema.

        dst is a valid extension of src iff
        - They describe the same resource - i.e. matching `rdf_resource`
        - All fields present in src are present in dst
        - All required fields in src must also be required in dst

        Args:
            src (Schema): base schema
            dst (Schema): extended schema
        """
        SchemaValidator.compatible(src, dst)
        SchemaValidator.subset(src.fields, dst.fields)
        SchemaValidator.subset(src.required, dst.required)
