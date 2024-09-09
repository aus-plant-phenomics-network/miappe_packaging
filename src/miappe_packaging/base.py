from __future__ import annotations

from typing import ClassVar, Final

from msgspec import Struct, field
from rdflib import BNode, IdentifiedNode

from src.miappe_packaging.exceptions import AnnotationError, MissingSchema
from src.miappe_packaging.registry import Registry
from src.miappe_packaging.types import Schema
from src.miappe_packaging.utils import convert_to_ref, validate_schema


class Base(Struct, kw_only=True):
    """Base Semantic Class

    Can be treated as a simple Python dataclass object.
    """

    id: str = field(default_factory=BNode)
    """Instance ID. If not provided, will be assigned a blank node ID"""
    __schema__: ClassVar[Schema]
    """Schema object. Class attribute"""

    def __post_init__(self) -> None:
        Registry().register(self)

    @property
    def ID(self) -> IdentifiedNode:
        """ID in rdflib Node format. String values are converted to URIRef using
        `rdflib.URIRef` callable. BNode and URIRef values are not modified.

        Returns:
            IdentifiedNode: id of current object.
        """
        return convert_to_ref(self.id)

    def __init_subclass__(cls) -> None:
        # Check fields are provided
        if hasattr(cls, "__schema__"):
            try:
                validate_schema(cls, cls.__schema__)
            except AnnotationError as e:
                e.add_note(f"Class: {cls.__name__}")
                raise
        else:
            raise MissingSchema("Schema object must be provided")

        return super().__init_subclass__()
