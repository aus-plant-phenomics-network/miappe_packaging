from __future__ import annotations

import typing
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, ClassVar, cast

from rdflib import BNode, Graph, IdentifiedNode, Literal, URIRef
from rdflib.namespace import RDF

from src.miappe_packaging.utils import Metadata, cached_class_property, field


class Registry:
    _instance = None
    models: dict[URIRef, type[Base]] = dict()
    model_instances: dict[type[Base], dict[URIRef, Base]] = dict()
    graph: Graph = Graph()

    def __new__(self, *args, **kwargs):
        if not self._instance:
            self._instance = super().__new__(self, *args, **kwargs)
        return self._instance

    def parse(self, path: str | Path) -> None:
        self.graph.parse(path)

    def register(self, model: Base) -> None:
        metaclass = model.metaclass
        modelclass = model.__class__
        if metaclass not in self.models:
            self.models[metaclass] = model.__class__
        if modelclass not in self.model_instances:
            self.model_instances[modelclass] = {model.id: model}
        else:
            self.model_instances[modelclass][model.id] = model

    def add_literal(
        self,
        id: IdentifiedNode,
        value_url: URIRef,
        type_url: URIRef | None,
        value: Any,
    ) -> None:
        if hasattr(value, "__len__") and not isinstance(value, str):
            for v in value:
                self.add_literal(id, value_url, type_url, v)
        else:
            if isinstance(value, Base):
                v = value.id
            else:
                if type_url:
                    v = Literal(value, datatype=type_url)
                else:
                    v = Literal(value)
            self.graph.add((id, value_url, v))

    def add(self, data: Base) -> None:
        id_node = cast(IdentifiedNode, data.id)
        self.graph.add((id_node, RDF.type, data.metaclass))
        for name, metadata in data.reference.items():
            metadata: Metadata
            if (value := getattr(data, name)) is not None:
                self.add_literal(id_node, metadata["ref"], metadata["type_ref"], value)

    def serialize(
        self,
        destination: str | Path,
        format: typing.Literal["json-ld", "turtle"] = "json-ld",
    ) -> None:
        self.graph.serialize(destination=destination, format=format)


@dataclass(kw_only=True)
class Base:
    __meta_class__: ClassVar[str | URIRef]

    id: IdentifiedNode | str = field(default_factory=BNode, exclude=True)

    def __post_init__(self) -> None:
        if not isinstance(self.id, IdentifiedNode):
            self.id = URIRef(self.id)
        Registry().register(self)

    @cached_class_property
    def metaclass(cls) -> URIRef:
        if isinstance(cls.__meta_class__, str):
            return URIRef(cls.__meta_class__)
        return cls.__meta_class__

    @cached_class_property
    def reference(cls) -> dict[str, Metadata]:
        annotations: dict[str, Metadata] = {}
        for info in fields(cls):
            if info.metadata["exclude"]:
                continue
            reference: Metadata = info.metadata["reference"]
            annotations[info.name] = reference
        return annotations
