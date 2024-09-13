# from __future__ import annotations

# from collections.abc import Sequence
# from pathlib import Path
# from typing import Any, ClassVar, Literal, Self, cast, overload

# import msgspec
# from msgspec import Struct, field
# from rdflib import BNode, Graph, Namespace, URIRef

# from appnlib.core.exceptions import ValidationError
# from appnlib.core.graph import from_struct
# from appnlib.core.json import LinkedEncoder, enc_hook
# from appnlib.core.schema import FieldInfo, Schema, SchemaValidator
# from appnlib.core.utils import (
#     make_ref,
# )

# __all__ = (
#     "LinkedDataClass",
#     "Registry",
#     "encode_struct",
# )


# class LinkedDataClass(Struct, kw_only=True):
#     """Base Linked DataClass

#     Can be treated as a simple Python dataclass object.
#     """

#     id: str = field(default_factory=BNode)
#     """Instance ID. If not provided, will be assigned a blank node ID"""
#     __schema__: ClassVar[Schema]
#     """Schema object. Class attribute"""
#     __rdf_resource__: ClassVar[URIRef]
#     __rdf_context__: ClassVar[URIRef | Namespace] = URIRef("./")

#     def encode(self, format: Literal["json", "builtin"] = "json") -> dict | bytes:
#         return encode_struct(self, format=format)

#     @property
#     def ID(self) -> URIRef:
#         """ID in rdflib Node format. String values are converted to URIRef using
#         `rdflib.URIRef` callable. BNode and URIRef values are not modified.

#         Returns:
#             URIRef: id of current object.
#         """
#         return cast(URIRef, make_ref(self.id))

#     def __post_init__(self) -> None:
#         Registry().register(self)

#     @property
#     def schema(self) -> Schema:
#         return self.__schema__

#     def __init_subclass__(cls) -> None:
#         # Validate schema if schema is not provided
#         if hasattr(cls, "__schema__"):
#             try:
#                 SchemaValidator.is_valid_dataclass(cls, cls.__schema__)
#             except ValidationError as e:
#                 e.add_note(f"Class: {cls.__name__}")
#                 raise
#         # Alternatively gather schema information from field annotation
#         else:
#             if not hasattr(cls, "__rdf_resource__"):
#                 raise ValidationError(
#                     f"either __rdf_resource__ or __schema__ must be provided. Class: {cls.__name__}"
#                 )
#             annotations = cls.__annotations__
#             attrs = {}
#             for k, v in annotations.items():
#                 if k == "__rdf_resource__":
#                     continue
#                 if not hasattr(v, "__metadata__"):
#                     attrs[k] = FieldInfo.from_annotations(
#                         k,
#                         cls.__name__,
#                         v,
#                         getattr(cls, "__rdf_context__", URIRef("./")),
#                     )
#                 else:
#                     metadata = getattr(v, "__metadata__")
#                     for tp in metadata:
#                         if isinstance(tp, FieldInfo):
#                             attrs[k] = tp

#             schema = Schema(
#                 __rdf_resource__=getattr(cls, "__rdf_resource__"), attrs=attrs
#             )
#             setattr(cls, "__schema__", schema)

#         return super().__init_subclass__()


# class Registry:
#     _instance: Self | None = None
#     type_dict: dict[URIRef, type[LinkedDataClass]] = dict()
#     instance_dict: dict[URIRef, dict[URIRef, LinkedDataClass]] = dict()
#     _graph = Graph()

#     @property
#     def graph(self) -> Graph:
#         return self._graph

#     def __new__(self, *args: Any, **kwargs: Any) -> Self:
#         if not self._instance:
#             self._instance = super().__new__(self, *args, **kwargs)
#         return cast(Self, self._instance)

#     def register(self, instance: LinkedDataClass) -> None:
#         rdf_resource = instance.__schema__.rdf_resource
#         # add to type dict
#         if type(instance) not in self.type_dict:
#             self.type_dict[rdf_resource] = instance.__class__
#         if rdf_resource not in self.instance_dict:
#             self.instance_dict[rdf_resource] = dict()
#         # add to instance dict
#         self.instance_dict[rdf_resource][instance.ID] = instance

#     def add_all(self) -> None:
#         for _, id_map in self.instance_dict.items():
#             for _, struct in id_map.items():
#                 from_struct(struct=struct, graph=self._graph)

#     def add(self, graph: Graph | Sequence[Graph]) -> None:
#         if isinstance(graph, Graph):
#             self._graph = self.graph + graph
#         else:
#             for g in graph:
#                 self._graph = self.graph + g

#     @overload
#     def serialize(
#         self,
#         destination: str | Path,
#         *,
#         base: str | None = None,
#         encoding: str | None = None,
#         context: dict[str, URIRef] | None = None,
#         use_native_types: bool = False,
#         use_rdf_type: bool = False,
#         auto_compact: bool = False,
#         indent: int = 2,
#         separators: tuple[str, str] = (",", ":"),
#         sort_keys: bool = True,
#         ensure_ascii: bool = False,
#     ) -> None: ...
#     @overload
#     def serialize(
#         self,
#         destination: str | Path,
#         *,
#         format: Literal[
#             "json-ld", "turtle", "xml", "pretty-xml", "n3", "nt", "trix"
#         ] = "json-ld",
#         base: str | None = None,
#         encoding: str | None = None,
#         **args: Any,
#     ) -> None: ...
#     def serialize(
#         self,
#         destination: str | Path,
#         *,
#         format: Literal[
#             "json-ld", "turtle", "xml", "pretty-xml", "n3", "nt", "trix"
#         ] = "json-ld",
#         base: str | None = None,
#         encoding: str | None = None,
#         **args: Any,
#     ) -> None:
#         """Write to file for persistency.

#         Before the underlying graph is serialised, all LinkedDataClasss are first added to the graph

#         Args:
#             destination (str | Path): file path
#             format (Literal["json-ld", "turtle", "xml", "pretty-xml", "n3", "nt", "trix"], optional): supported serialisation formats. Defaults to "json-ld".
#         """
#         self.add_all()
#         self._graph.serialize(
#             destination=destination, format=format, base=base, encoding=encoding, **args
#         )


# def encode_struct(
#     struct: object, format: Literal["json", "builtin"] = "json"
# ) -> dict | bytes:
#     match format:
#         case "json":
#             return LinkedEncoder.encode(struct)
#         case "builtin":
#             return cast(dict, msgspec.to_builtins(struct, enc_hook=enc_hook))
#         case _:
#             raise TypeError(f"Invalid format: {format}")
