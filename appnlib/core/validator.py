from __future__ import annotations
from typing import Literal
from enum import StrEnum
from appnlib.core.types import (
    Schema,
    StructP,
    DataClassT,
    DataClassP,
    AnnotatedP,
)


class DescribeMode(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    REQUIRED = "required"


class SchemaValidator:
    @staticmethod
    def is_sub_schema(src: Schema, dst: Schema) -> bool:
        """Check whether src schema is a sub-schema of dst schema

        src is a sub-schema of dst iff
        - src and dst describe the same resource
        - fields of src are a subset of fields of dst
        - required fields of src are a subset of required fields of dst

        Args:
            src (Schema): source schema
            dst (Schema): dest schema

        Returns:
            bool: _description_
        """
        if not isinstance(src, Schema):
            raise TypeError(f"src must be of Schema type: {type(src)}")
        if not isinstance(dst, Schema):
            raise TypeError(f"dst must be of Schema type: {type(dst)}")
        return (
            src.rdf_resource == dst.rdf_resource
            and src.fields.issubset(dst.fields)
            and src.required.issubset(dst.required)
        )

    @staticmethod
    def describe_attrs(
        attrs: DataClassT,
        schema: Schema,
        mode: DescribeMode | Literal["full", "partial", "required"] = DescribeMode.FULL,
    ) -> bool:
        """Check whether schema describes attrs

        If mode is required:
            - Check whether attrs has all required fields of schema
        If mode is partial
            - Check whether schema fields are a subset of attrs' fields
        If mode is full
            - Check whether schema fields and attrs fields are exactly the same
        Args:
            attrs (DataClassT): _description_
            schema (Schema): _description_
            mode (DescribeMode | Literal["full", "partial", "required"], optional): _description_. Defaults to DescribeMode.FULL.

        Raises:
            TypeError: if schema is not of Schema type
            TypeError: if attrs is not a dict/dataclass/struct or has __annotated__ fields
            ValueError: if mode value is not a DescribeMode enum or a str of full/partial/required

        Returns:
            bool: validation check
        """
        mode = mode.value if isinstance(mode, DescribeMode) else mode
        if not isinstance(schema, Schema):
            raise TypeError(f"Expects a Schema. Given type: {type(schema)}")
        field_set: set[str]
        if isinstance(attrs, dict):
            field_set = set(attrs.keys())
        elif isinstance(attrs, StructP):
            field_set = set(attrs.__struct_fields__)
        elif isinstance(attrs, DataClassP):
            field_set = set(attrs.__dataclass_fields__.keys())
        elif isinstance(attrs, AnnotatedP):
            field_set = set(attrs.__annotations__.keys())
        else:
            raise TypeError(
                f"Invalid type. Expects dict, struct, dataclass or annotated. Given: {type(attrs)}"
            )

        if mode == "required":
            return schema.required.issubset(field_set)
        if mode == "partial":
            return schema.fields.issubset(field_set)
        if mode == "full":
            return schema.fields == field_set
        raise ValueError(f"Invalid mode: expects required/partial/full. Given: {mode}")
