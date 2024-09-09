from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Generic, ParamSpec, TypeVar

from rdflib import BNode, IdentifiedNode, URIRef

from src.miappe_packaging.exceptions import AnnotationError

if TYPE_CHECKING:
    from src.miappe_packaging.base import Base
    from src.miappe_packaging.types import Schema

T = TypeVar("T")
P = ParamSpec("P")


class cached_class_property(Generic[T, P]):
    def __init__(self, func: Callable[P, T]) -> None:
        self.func = func
        self._cached_value: T = None  # type: ignore[assignment]

    def __get__(self, instance: Any, cls: Any, **kwargs: Any) -> T:
        if self._cached_value is None:
            self._cached_value = self.func(cls, **kwargs)
        return self._cached_value


def convert_to_ref(identifier: IdentifiedNode | str | None = None) -> IdentifiedNode:
    if not identifier:
        return BNode()
    return identifier if isinstance(identifier, IdentifiedNode) else URIRef(identifier)


def validate_schema(obj: Any, schema: Schema) -> None:
    """Check that the schema's attribute keys are the same as object's attribute keys

    Args:
        obj (Any): obj for validation
        schema (Schema): object schema. Should have attrs whose keys match the attributes of obj

    Raises:
        AnnotationError: if there are keys in obj and not in schema and vice versa
    """
    obj_fields = set(obj.__annotations__)
    schema_fields = set(schema.attrs.keys())
    obj_fields.discard("id")
    schema_fields.discard("id")
    if obj_fields != schema_fields:
        raise AnnotationError(
            f"Attributes and schema keys don't match. Symmetric difference: {schema_fields ^ obj_fields}"
        )
