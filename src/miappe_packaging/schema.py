from __future__ import annotations

from collections.abc import Sequence, Set
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, NotRequired, Required, TypedDict, overload
from typing import (
    Literal as TypingLiteral,
)

from rdflib import BNode, Graph, IdentifiedNode, Literal, URIRef
from rdflib.namespace import RDF

from src.miappe_packaging.exceptions import AnnotationError, IdError, SchemaError
from src.miappe_packaging.utils import cached_class_property


class Registry:
    _instance = None
    models: dict[URIRef, type["Base"]] = dict()
    _graph: Graph = Graph()
    ID_Pool: set[IdentifiedNode] = set()

    @property
    def graph(self) -> Graph:
        return self._graph

    def __new__(self, *args, **kwargs):
        if not self._instance:
            self._instance = super().__new__(self, *args, **kwargs)
        return self._instance

    def validate_id_unique(self, id: IdentifiedNode) -> bool:
        if id in self.ID_Pool:
            return False
        self.ID_Pool.add(id)
        return True

    @overload
    def serialize(
        self,
        destination: str | Path,
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
        format: TypingLiteral[
            "json-ld", "turtle", "xml", "pretty-xml", "n3", "nt", "trix"
        ] = "json-ld",
        base: str | None = None,
        encoding: str | None = None,
        **args: Any,
    ) -> None: ...
    def serialize(
        self,
        destination: str | Path,
        format: TypingLiteral[
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

    def register(self, model: type["Base"]) -> None:
        """Register model class with registry. Model classes are searchable with registry
        by their rdfs:Resource reference

        Args:
            model (type[Base]): model class
        """
        self.models[model.rdf_resource] = model

    def load(self, path: str | Path) -> None:
        """Open file from path and create semantic class objects based on linked data.

        Args:
            path (str | Path): path to linked data file
        """
        self.graph.parse(path)
        for class_ref, class_model in self.models.items():
            class_ids = self._graph.subjects(RDF.type, class_ref, unique=True)
            for class_id in class_ids:
                stmts = self._graph.predicate_objects(class_id, unique=True)
                class_model.from_stmts(class_id, stmts)

    def add(self, instance: "Base") -> None:
        """Add an instance of a semantic class to current graph

        Args:
            instance (Base): semantic class instance
        """

        def atomic_add(name: str, info: FieldInfo, value: Any) -> None:
            if issubclass(type(value), (Sequence, Set)) and not isinstance(value, str):
                for item in value:
                    atomic_add(name, info, item)
            else:
                datatype = info.get("range", None)
                if not datatype or isinstance(datatype, URIRef):
                    add_value = Literal(value, datatype=datatype)
                else:
                    if not isinstance(value, URIRef):
                        raise IdError(
                            f"IDRef range type object must be a URIRef. Class: {instance.__class__.__name__}, field: {name}"
                        )
                    add_value = value
                try:
                    self._graph.add((instance.ID, info["ref"], add_value))
                except KeyError:
                    raise SchemaError(
                        f"Missing required ref for schema field {name} of of class: {instance.__class__.__name__}"
                    )

        self._graph.add((instance.ID, RDF.type, instance.rdf_resource))
        for name, info in instance.field_schema.items():
            value = getattr(instance, name)
            if value is not None:
                atomic_add(name, info, value)

    def add_all(self) -> None:
        """Automatically add all semantic object instance to
        graph to prepare to write to disk
        """
        for _, class_model in self.models.items():
            for _, model_instance in class_model.store.items():
                self.add(model_instance)
