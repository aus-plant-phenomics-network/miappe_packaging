from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, overload

from rdflib import Graph, IdentifiedNode, URIRef
from rdflib.namespace import NamespaceManager
from rdflib.store import Store

from src.miappe_packaging.converter import struct_to_graph
from src.miappe_packaging.exceptions import IdError

if TYPE_CHECKING:
    from src.miappe_packaging.base import Base


class Registry:
    _instance = None

    @property
    def graph(self) -> Graph:
        return self._graph

    def __new__(self, *args, **kwargs):
        if not self._instance:
            self._graph = Graph()
            self.type_dict: dict[URIRef, type[Base]] = dict()
            self.instance_dict: dict[URIRef, dict[IdentifiedNode, Base]] = dict()
            self._instance = super().__new__(self, *args, **kwargs)
        return self._instance

    def register(self, instance: "Base") -> None:
        rdf_resource = instance.__schema__.rdf_resource
        # add to type dict
        if type(instance) not in self.type_dict:
            self.type_dict[rdf_resource] = instance.__class__
        if rdf_resource not in self.instance_dict:
            self.instance_dict[rdf_resource] = dict()
        # add to instance dict
        if instance.ID in self.instance_dict[rdf_resource]:
            raise IdError("ID already exists in registry")
        self.instance_dict[rdf_resource][instance.ID] = instance

    def add_all(self) -> None:
        for _, id_map in self.instance_dict.items():
            for _, struct in id_map.items():
                struct_to_graph(struct=struct, graph=self._graph)

    @overload
    def serialize(
        self,
        destination: str | Path,
        *,
        base: str | None = None,
        encoding: str | None = None,
        context: dict[str, URIRef] | None = None,
        use_native_types: bool = False,
        use_rdf_type: bool = False,
        auto_compact: bool = False,
        indent: int = 2,
        separators: tuple[str, str] = (",", ":"),
        sort_keys: bool = True,
        ensure_ascii: bool = False,
    ) -> None: ...
    @overload
    def serialize(
        self,
        destination: str | Path,
        *,
        format: Literal[
            "json-ld", "turtle", "xml", "pretty-xml", "n3", "nt", "trix"
        ] = "json-ld",
        base: str | None = None,
        encoding: str | None = None,
        **args: Any,
    ) -> None: ...
    def serialize(
        self,
        destination: str | Path,
        *,
        format: Literal[
            "json-ld", "turtle", "xml", "pretty-xml", "n3", "nt", "trix"
        ] = "json-ld",
        base: str | None = None,
        encoding: str | None = None,
        **args: Any,
    ) -> None:
        """Write to file for persistency.

        Before the underlying graph is serialised, all semantic objects are first added to the graph

        Args:
            destination (str | Path): file path
            format (TypingLiteral[ &quot;json, optional): supported serialisation formats. Defaults to "json-ld".
        """
        self.add_all()
        self._graph.serialize(
            destination=destination, format=format, base=base, encoding=encoding, **args
        )
