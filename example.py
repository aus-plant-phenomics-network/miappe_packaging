# %%
from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    ClassVar,
)

from appnlib.core.exceptions import AnnotationError
from appnlib.core.types import BNode, IdentifiedNode, Schema, URIRef
from appnlib.core.utils import make_ref
from appnlib.core.validator import SchemaValidator
from pydantic import BaseModel, ConfigDict, Field
from rdflib import Literal
from rdflib.namespace import RDF, XSD

if TYPE_CHECKING:
    from appnlib.core.types import Schema
    from rdflib.graph import _TripleType

__all__ = ("LinkedDataClass",)


class LinkedDataClass(BaseModel):
    """Base Linked DataClass"""

    id: str | IdentifiedNode = Field(default_factory=BNode)
    """Instance ID. If not provided, will be assigned a blank node ID"""
    __schema__: ClassVar[Schema]
    """Schema object. Class attribute"""
    model_config = ConfigDict(
        json_encoders={
            URIRef: lambda v: v.toPython(),
            BNode: lambda v: v.toPython(),
            Literal: lambda v: v.toPython(),
            "LinkedDataClass": lambda v: v.ID,
        },
    )

    @property
    def ID(self) -> IdentifiedNode:  # noqa: N802
        """Return id as either URIRef or BNode"""
        return make_ref(self.id)

    @property
    def schema(self) -> Schema:
        """Get associated schema"""
        return self.__schema__

    @property
    def rdf_resource(self) -> URIRef:
        """Get associated rdf resource"""
        return self.schema.rdf_resource

    def __init_subclass__(cls) -> None:
        # Validate schema
        if hasattr(cls, "__schema__") and not SchemaValidator.describe_attrs(attrs=cls, schema=cls.__schema__, mode="full"):
            raise AnnotationError("Schema does not fully describe LinkedDataClass")
        # Register
        # Registry().register_schema(cls.__schema__)
        return super().__init_subclass__()

    def __post_init__(self) -> None:
        # Registry().register_instance(self)
        pass

    def to_triple(self) -> list[_TripleType]:
        result: list[_TripleType] = []
        schema = self.schema
        for sfield in self.model_fields:
            if sfield == "id":
                continue
            value = getattr(self, sfield)
            info = schema.attrs[sfield]
            if not isinstance(value, str) and hasattr(value, "__len__"):
                if not info.repeat:
                    raise AnnotationError(f"field {sfield} is not annotated as repeat but is of container type: {type(value)}")
            else:
                value = [value]
            for _value in value:
                _value = make_ref(_value) if info.range == XSD.IDREF else Literal(_value, datatype=info.range)
                result.append((self.ID, info.ref, _value))

        if hasattr(self, "__dict__"):
            for sfield, value in self.__dict__.items():
                if not hasattr(value, "__len__") or isinstance(value, str):
                    value = [value]
                for _value in value:
                    result.append((self.ID, Literal(sfield), Literal(_value)))

        result.append((self.ID, RDF.type, self.rdf_resource))
        return result
