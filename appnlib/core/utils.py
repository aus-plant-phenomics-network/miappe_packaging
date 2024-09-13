from __future__ import annotations

from typing import Any

from rdflib import BNode, IdentifiedNode, URIRef

__all__ = (
    "get_key_or_attribute",
    "make_ref",
)


def make_ref(identifier: IdentifiedNode | str | None = None) -> IdentifiedNode:
    """Create a Node reference

    If identifier is a `URIRef` or `BNode`, the function will return identifier as is. If the identifier is a string,
    depending on whether it starts with `_:`, the function will return a `BNode` or `URIRef` with the identifier
    value. If not provided, the function will generate and return a BNode

    Args:
        identifier (IdentifiedNode | str | None, optional): identifier value. Defaults to None.

    Raises:
        TypeError: if identifier is not a string or not IdentifiedNode or BNode type.

    Returns:
        IdentifiedNode: identifier as `IdentifiedNode` type
    """
    if identifier is None:
        return BNode()
    if isinstance(identifier, IdentifiedNode):
        return identifier
    if isinstance(identifier, str):
        if identifier.startswith("_:"):
            return BNode(identifier[2:])
        return URIRef(identifier)
    raise TypeError(f"Invalid type: {type(identifier)}")


def get_key_or_attribute(
    field: str, obj: Any, raise_error_if_missing: bool = False
) -> Any:
    """From an object, attempt to get key if object is dict like otherwise get attribute.

    Read obj.get(field) then try getattr(obj, field)

    Args:
        field (str): key/attribute name
        obj (Any): object to extract key/attribute from
        raise_error_if_missing (bool, optional): whether to raise if the field is missing. Defaults to False.

    Raises:
        KeyError: If the object has no key or attribute with the name field

    Returns:
        Any: the key/attribute value if they exist, or None if they don't and `raise_error_if_missing` is False
    """
    if hasattr(obj, field):
        return getattr(obj, field)
    if isinstance(obj, dict) and field in obj:
        return obj.get(field)
    if raise_error_if_missing:
        raise KeyError(f"Object has no key: {field}")
    return None
