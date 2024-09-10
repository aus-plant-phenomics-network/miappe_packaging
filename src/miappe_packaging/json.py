from typing import Any, Type

from rdflib import IdentifiedNode, Literal, URIRef


def enc_hook(obj: Any) -> Any:
    if isinstance(obj, Literal):
        return obj.toPython()
    if isinstance(obj, IdentifiedNode):
        return obj.toPython()
    raise TypeError(f"Invalid encoding type: {type(obj)}")


def dec_hook(type: Type, obj: Any) -> Any:
    if type is IdentifiedNode:
        return URIRef(obj)
