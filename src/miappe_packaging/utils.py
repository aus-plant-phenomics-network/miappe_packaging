from typing import (
    Any,
    Callable,
    Generic,
    ParamSpec,
    TypeVar,
)

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
