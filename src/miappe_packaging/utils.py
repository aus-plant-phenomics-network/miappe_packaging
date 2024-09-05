from collections.abc import Mapping
from dataclasses import _MISSING_TYPE, MISSING
from dataclasses import field as dc_field
from typing import Any, Callable, TypedDict, overload

from rdflib import URIRef

from src.miappe_packaging.exceptions import AnnotationError


class cached_class_property:
    def __init__(self, func: Any) -> None:
        self.func = func
        self._cached_value = None

    def __get__(self, instance: Any, cls: Any, **kwargs: Any) -> Any:
        if self._cached_value is None:
            self._cached_value = self.func(cls, **kwargs)
        return self._cached_value


class Metadata(TypedDict):
    ref: URIRef
    type_ref: URIRef | None


@overload
def field(
    *,
    ref: URIRef | str | None = None,
    type_ref: URIRef | str | None = None,
    metadata: Mapping[Any, Any] | None = None,
    default: Any = MISSING,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    kw_only: bool | _MISSING_TYPE = MISSING,
    exclude: bool = False,
) -> Any: ...
@overload
def field(
    *,
    ref: URIRef | str | None = None,
    type_ref: URIRef | str | None = None,
    metadata: Mapping[Any, Any] | None = None,
    default_factory: Callable[[Any], Any] | _MISSING_TYPE = MISSING,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    kw_only: bool | _MISSING_TYPE = MISSING,
    exclude: bool = False,
) -> Any: ...
@overload
def field(
    *,
    ref: URIRef | str | None = None,
    type_ref: URIRef | str | None = None,
    metadata: Mapping[Any, Any] | None = None,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    kw_only: bool | _MISSING_TYPE = MISSING,
    exclude: bool = False,
) -> Any: ...
def field(
    *,
    ref: URIRef | str | None = None,
    type_ref: URIRef | str | None = None,
    metadata: dict[Any, Any] | None = None,
    default: Any = MISSING,
    default_factory: Callable[[Any], Any] | _MISSING_TYPE = MISSING,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    kw_only: bool | _MISSING_TYPE = MISSING,
    exclude: bool = False,
) -> Any:
    if type_ref and isinstance(type_ref, str):
        type_ref = URIRef(type_ref)
    ref_metadata = Metadata(ref=ref, type_ref=type_ref)
    if metadata:
        metadata["reference"] = ref_metadata
    else:
        metadata = {"reference": ref_metadata}
    metadata["exclude"] = exclude
    if default != MISSING and default_factory != MISSING:
        raise AnnotationError("Cannot have both default and default_factory provided.")
    if default != MISSING:
        return dc_field(
            default=default,
            init=init,
            repr=repr,
            hash=hash,
            compare=compare,
            metadata=metadata,
            kw_only=kw_only,
        )
    if default_factory != MISSING:
        return dc_field(
            default_factory=default_factory,
            init=init,
            repr=repr,
            hash=hash,
            compare=compare,
            metadata=metadata,
            kw_only=kw_only,
        )
    return dc_field(
        init=init,
        repr=repr,
        hash=hash,
        compare=compare,
        metadata=metadata,
        kw_only=kw_only,
    )
