from collections.abc import Sequence, Set
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, NotRequired, Required, TypedDict
from typing import (
    Literal as TypingLiteral,
)

from rdflib import BNode, Graph, IdentifiedNode, Literal, URIRef
from rdflib.namespace import RDF

from src.miappe_packaging.exceptions import AnnotationError, SchemaError
from src.miappe_packaging.utils import cached_class_property


class TypeReference(TypedDict):
    value: str | type
    ref: URIRef


class FieldInfo(TypedDict):
    ref: Required[URIRef]
    range: NotRequired[URIRef | TypeReference]
    repeat: NotRequired[bool]
    required: NotRequired[bool]


class Schema(TypedDict):
    __rdf_resource__: URIRef
    attrs: dict[str, FieldInfo]


@dataclass(kw_only=True)
class Base:
    __schema__: ClassVar[Schema]
    store: ClassVar[dict[str, "Base"]] = dict()

    id: str | IdentifiedNode = field(default_factory=BNode)

    def __init_subclass__(cls) -> None:
        # Check fields are provided
        try:
            cls._ensure_matching_field_annotation()
        except AnnotationError as e:
            e.add_note(f"Class: {cls.__name__}")
            raise

        # Register class at registry
        Registry().register(cls)
        return super().__init_subclass__()

    def __post_init__(self) -> None:
        self.store[self.ID] = self

    @classmethod
    def _ensure_matching_field_annotation(cls) -> None:
        """Check that `__schema__` attributes have the same keys as the
        class.

        Raises:
            AnnotationError: if there are keys present in the class but not in
            schema and vice versa
        """
        if not hasattr(cls, "__schema__"):
            raise AnnotationError("__schema__ class attribute must be provided")
        field_keys = set(cls.__annotations__.keys())
        field_keys.discard("id")
        schema_keys = set(cls.__schema__["attrs"].keys())
        schema_keys.discard("id")
        if field_keys != schema_keys:
            raise AnnotationError(
                f"Attributes and schema keys don't match. Symmetric difference: {schema_keys ^ field_keys}"
            )

    @classmethod
    def from_stmts(
        cls, instance_id: IdentifiedNode, stmts: tuple[IdentifiedNode, Any]
    ) -> "Base":
        kwargs = {}
        for ref, value in stmts:
            if ref != RDF.type:
                attr = cls.reverse_schema[ref]
                kwargs[attr] = value
        return cls(id=instance_id, **kwargs)

    @cached_class_property
    def field_schema(cls) -> dict[str, FieldInfo]:
        """Mapping of field name to their semantic info

        Returns:
            dict[str, FieldInfo]: mapping
        """
        return cls.__schema__["attrs"]

    @cached_class_property
    def reverse_schema(cls) -> dict[URIRef, str]:
        """Mapping from URI Reference to class attribute

        Returns:
            dict[URIRef, str]: mapping between semantic reference to field name
        """
        return {info["ref"]: name for name, info in cls.field_schema.items()}

    @cached_class_property
    def rdf_resource(cls) -> URIRef:
        """URI to the instance of rdf:Resource that represents the class.
        Assert the statement (obj, rdf:type, obj.rdf_resource)

        Returns:
            URIRef: URI to the definition of the resource
        """
        return cls.__schema__["__rdf_resource__"]

    @property
    def ID(self) -> IdentifiedNode:
        """ID in rdflib Node format. String values are converted to URIRef using
        `rdflib.URIRef` callable. BNode and URIRef values are not modified.

        Returns:
            IdentifiedNode: id of current object.
        """
        return self.id if isinstance(self.id, IdentifiedNode) else URIRef(self.id)


class Registry:
    _instance = None
    models: dict[URIRef, type[Base]] = dict()
    _graph: Graph = Graph()

    def __new__(self, *args, **kwargs):
        if not self._instance:
            self._instance = super().__new__(self, *args, **kwargs)
        return self._instance

    def _parse(self, path: str | Path) -> None:
        """Parse rdf store from path

        Args:
            path (str | Path): path description
        """
        self._graph.parse(path)

    def serialize(
        self,
        destination: str | Path,
        format: TypingLiteral[
            "json-ld", "turtle", "xml", "pretty-xml", "n3", "nt", "trix"
        ] = "json-ld",
    ) -> None:
        """Write to file for persistency.

        Before the underlying graph is serialised, all semantic objects are first added to the graph

        Args:
            destination (str | Path): file path
            format (TypingLiteral[ &quot;json, optional): supported serialisation formats. Defaults to "json-ld".
        """
        self.add_all()
        self._graph.serialize(destination=destination, format=format)

    def register(self, model: type[Base]) -> None:
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
        self._parse(path)
        for class_ref, class_model in self.models.items():
            class_ids = self._graph.subjects(RDF.type, class_ref, unique=True)
            for class_id in class_ids:
                stmts = self._graph.predicate_objects(class_id, unique=True)
                class_model.from_stmts(class_id, stmts)

    def add(self, instance: Base) -> None:
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
                datatype = datatype if isinstance(datatype, URIRef) else None
                literal_value = Literal(value, datatype=datatype)
                try:
                    self._graph.add((instance.ID, info["ref"], literal_value))
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
