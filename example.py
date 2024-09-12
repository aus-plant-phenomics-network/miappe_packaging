# %%
from dataclasses import dataclass
from typing import NamedTuple, dataclass_transform, get_type_hints
from msgspec import Struct

@dataclass_transform()
class BaseModel: ...


@dataclass
class MyModel:
    name: str
    age: int


class AnotherModel:
    name: str
    age: int


MyClass = type("MyClass", (), {"__annotations__": {"age": int, "name": str}})


# %%
