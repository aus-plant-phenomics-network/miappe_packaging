from typing import Any, Type

from msgspec.json import Encoder
from rdflib import Literal, URIRef


def enc_hook(obj: Any) -> Any:
    if isinstance(obj, Literal):
        return obj.toPython()
    if isinstance(obj, URIRef):
        return obj.toPython()
    raise TypeError(f"Invalid encoding type: {type(obj)}")


def dec_hook(type: Type, obj: Any) -> Any:
    if type is URIRef:
        return URIRef(str(obj))


LinkedEncoder = Encoder(enc_hook=enc_hook)
