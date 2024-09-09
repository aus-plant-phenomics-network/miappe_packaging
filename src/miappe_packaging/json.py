from typing import Any

from rdflib import IdentifiedNode, Literal

from src.miappe_packaging.types import Schema


def enc_hook(obj: Any) -> Any:
    if isinstance(obj, Literal):
        return obj.toPython()
    if isinstance(obj, IdentifiedNode):
        return obj.toPython()
    raise TypeError(f"Invalid encoding type: {type(obj)}")
