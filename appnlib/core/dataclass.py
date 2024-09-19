from __future__ import annotations

from collections.abc import Callable, Generator
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Self,
    cast,
)
from typing import Literal as PyLiteral

from appnlib.core.exceptions import AnnotationError, IntegrityError
from appnlib.core.types import Schema
from appnlib.core.utils import make_ref
from appnlib.core.validator import SchemaValidator
from pydantic import BaseModel, ConfigDict, Field
from rdflib import BNode, Graph, IdentifiedNode, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD, NamespaceManager

if TYPE_CHECKING:
    from appnlib.core.types import Schema
    from rdflib._type_checking import _NamespaceSetString
    from rdflib.graph import _ContextIdentifierType, _TripleType
    from rdflib.store import Store

__all__ = ("LinkedDataClass",)

EncHookT = Callable[[Any], Any] | None
DecHookT = Callable[[type, Any], Any] | None


class LinkedDataClass(BaseModel):
    """Base Linked DataClass"""

    id: str | IdentifiedNode = Field(default_factory=BNode)
    """Instance ID. If not provided, will be assigned a blank node ID"""
    __schema__: ClassVar[Schema]
    """Schema object. Class attribute"""
    model_config = ConfigDict(
        json_encoders={
            URIRef: lambda v: v.toPython(),
            BNode: lambda v: v.toPython(),
            Literal: lambda v: v.toPython(),
            "LinkedDataClass": lambda v: v.ID,
        },
    )

    @property
    def ID(self) -> IdentifiedNode:  # noqa: N802
        """Return id as either URIRef or BNode"""
        return make_ref(self.id)

    @property
    def schema(self) -> Schema:
        """Get associated schema"""
        return self.__schema__

    @property
    def rdf_resource(self) -> URIRef:
        """Get associated rdf resource"""
        return self.schema.rdf_resource

    def __init_subclass__(cls) -> None:
        # Validate schema
        if hasattr(cls, "__schema__") and not SchemaValidator.describe_attrs(attrs=cls, schema=cls.__schema__, mode="full"):
            raise AnnotationError("Schema does not fully describe LinkedDataClass")
        # Register
        # Registry().register_schema(cls.__schema__)
        return super().__init_subclass__()

    def __post_init__(self) -> None:
        # Registry().register_instance(self)
        pass

    def to_triple(self) -> list[_TripleType]:
        result: list[_TripleType] = []
        schema = self.schema
        for sfield in self.model_fields:
            if sfield == "id":
                continue
            value = getattr(self, sfield)
            info = schema.attrs[sfield]
            if not isinstance(value, str) and hasattr(value, "__len__"):
                if not info.repeat:
                    raise AnnotationError(f"field {sfield} is not annotated as repeat but is of container type: {type(value)}")
            else:
                value = [value]
            for _value in value:
                _value = make_ref(_value) if info.range == XSD.IDREF else Literal(_value, datatype=info.range)
                result.append((self.ID, info.ref, _value))

        if hasattr(self, "__dict__"):
            for sfield, value in self.__dict__.items():
                if not hasattr(value, "__len__") or isinstance(value, str):
                    value = [value]
                for _value in value:
                    result.append((self.ID, Literal(sfield), Literal(_value)))

        result.append((self.ID, RDF.type, self.rdf_resource))
        return result


class RegistryConfig(BaseModel):
    on_conflict_schema: PyLiteral[
        "raise",
        "overwrite",
        "subclass",
        "ignore",
    ] = "raise"
    """Describes how conflicting schema should be handled by the registry. Conflicting schema arises when
    two dataclasses have schemas that describe the same resource but have different values.
    The two accepted config values are:

    - raises: will raise an error immediately when conflicting schemas are detected
    - overwrite: if two schemas describe the same resource are detected, the later-defined schema will overwrite the earlier-defined.
    - subclass: given two schemas that are in conflict, use the schema that is the subclass of the other.
    If neither schema is a subclass of the other, will raise an error.

    The default value is raise.
    """
    on_confict_identifier: PyLiteral["raise", "overwrite", "ignore"] = "overwrite"
    """Describe how conflicting identifier should be handled by the registry"""


DEFAULT_REGISTRY_CONFIG = RegistryConfig()


class Session:
    def __init__(
        self,
        store: Store | str = "default",
        identifier: _ContextIdentifierType | str | None = None,
        namespace_manager: NamespaceManager | None = None,
        base: str | None = None,
        bind_namespaces: _NamespaceSetString = "rdflib",
        **kwargs: Any,
    ) -> None:
        self._graph = Graph(
            store=store,
            identifier=identifier,
            namespace_manager=namespace_manager,
            base=base,
            bind_namespaces=bind_namespaces,
            **kwargs,
        )
        self._instances: set[IdentifiedNode] = set()

    @property
    def graph(self) -> Graph:
        return self._graph

    def _add_dataclass(self, dataclass: LinkedDataClass, codec: Codec = DEFAULT_CODEC) -> Self:
        triples = codec.encode_to_triple(dataclass=dataclass)
        self._graph.addN((s, p, o, self._graph) for s, p, o in triples)
        return self

    def add(self, dataclass: LinkedDataClass, codec: Codec = DEFAULT_CODEC) -> Self:
        self._add_dataclass(dataclass, codec)
        registry = Registry()
        schema = dataclass.schema
        for name, info in schema.attrs.items():
            if info.resource_ref:
                ref_resource = info.resource_ref
                range_value = getattr(dataclass, name)
                if isinstance(range_value, str) or not hasattr(range_value, "__len__"):
                    range_value = [range_value]
                for value in range_value:
                    value_id = make_ref(value)
                    if value_id not in self._instances:
                        matched_instance = registry.get_instance(resource=ref_resource, identifier=make_ref(value))
                        self._add_dataclass(matched_instance, codec)
                        self._instances.add(value_id)
        return self

    def subgraph(self, identifier: IdentifiedNode) -> Generator[_TripleType, None, None]:
        return self._graph.triples((identifier, None, None))

    def to_json(
        self,
        destination: str | None = None,
        base: str | None = None,
        encoding: str | None = None,
        context: dict[str, URIRef | Namespace] | None = None,
        use_native_types: bool = False,
        use_rdf_type: bool = False,
        auto_compact: bool = False,
        indent: int = 2,
        separators: tuple[str, str] = (",", ":"),
        sort_keys: bool = True,
        ensure_ascii: bool = False,
    ) -> Any:
        return self._graph.serialize(
            destination=destination,
            format="json-ld",
            base=base,
            encoding=encoding,
            context=context,
            use_native_types=use_native_types,
            use_rdf_type=use_rdf_type,
            auto_compact=auto_compact,
            indent=indent,
            separators=separators,
            sort_keys=sort_keys,
            ensure_ascii=ensure_ascii,
        )


class Registry:
    _instance: Self | None = None
    _schema_dict: ClassVar[dict[URIRef, Schema]]
    _instance_dict: ClassVar[dict[URIRef, dict[IdentifiedNode, LinkedDataClass]]]
    _session_dict: ClassVar[dict[IdentifiedNode, Session]]

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._schema_dict = {}
            cls._instance_dict = {}
            cls._session_dict = {}
        return cast(Self, cls._instance)

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def __init__(self, config: RegistryConfig = DEFAULT_REGISTRY_CONFIG) -> None:
        if not hasattr(self, "_config"):
            self._config = config

    @property
    def config(self) -> RegistryConfig:
        return self._config

    @config.setter
    def config(self, value: RegistryConfig) -> None:
        self._config = value

    def _handle_conflict_instance(
        self,
        instance: LinkedDataClass,
    ) -> None:
        match self.config.on_confict_identifier:
            case "raise":
                raise IntegrityError(f"A previous instance with the same ID have been registered: {instance.ID}")
            case "overwrite":
                self._instance_dict[instance.rdf_resource][instance.ID] = instance
                return

    def _handle_conflict_schema(self, obj: Schema) -> None:
        match self.config.on_conflict_schema:
            case "raise":
                raise IntegrityError(f"A schema describing the same resource has been registered: {obj.rdf_resource}")
            case "overwrite":
                self._schema_dict[obj.rdf_resource] = obj
                return
            case "subclass":
                prev_obj = self._schema_dict[obj.rdf_resource]
                if SchemaValidator.is_sub_schema(obj, prev_obj):
                    self._schema_dict[obj.rdf_resource] = prev_obj
                    return
                if SchemaValidator.is_sub_schema(prev_obj, obj):
                    self._schema_dict[obj.rdf_resource] = obj
                    return
                raise IntegrityError(f"Conflicting schemas that are not sub schema of one another: {obj.rdf_resource}")

    def create_session(
        self,
        store: Store | str = "default",
        identifier: _ContextIdentifierType | str | None = None,
        namespace_manager: NamespaceManager | None = None,
        base: str | None = None,
        bind_namespaces: _NamespaceSetString = "rdflib",
        **kwargs: Any,
    ) -> Session:
        """Create a session using rdflib.Graph constructor params"""
        session = Session(
            store=store,
            identifier=identifier,
            namespace_manager=namespace_manager,
            base=base,
            bind_namespaces=bind_namespaces,
            **kwargs,
        )
        self._session_dict[session.graph.identifier] = session
        return session

    def get_session(self, identifier: IdentifiedNode, **kwargs: Any) -> Session:
        """Get a session based on its identifier. If the session does not exist,
        create a new one and return.

        Args:
            identifier (IdentifiedNode): ID of the session graph
            kwargs (Any): other kwargs for create_session
        """
        if identifier in self._session_dict:
            return self._session_dict[identifier]
        return self.create_session(identifier=identifier, **kwargs)

    def remove_session(self, identifier: IdentifiedNode) -> None:
        """Remove a session from the registry based on its identifier.

        Args:
            identifier (IdentifiedNode): ID of the session graph
        """
        if identifier in self._session_dict:
            self._session_dict.pop(identifier)

    def register_schema(self, schema: Schema) -> None:
        """Add an object to registry, indexed by its rdf_resource

        All LinkedDataClass subclasses are automatically registered
        at object construction

        If a similar object with the same ID has been registered,
        resolution depends on the registry config

        Args:
            schema (Type[LinkedDataClass]): a LinkedDataClass subclass
        """
        if schema.rdf_resource in self._schema_dict:
            self._handle_conflict_schema(schema)
        else:
            self._schema_dict[schema.rdf_resource] = schema
            self._instance_dict[schema.rdf_resource] = {}

    def register_instance(self, instance: LinkedDataClass) -> None:
        """Add an instance to registry.

        Can be used to explicitly add an instance, but most of the
        time called at instance construction (post init)

        If a similar instance with the same ID has already been registered,
        resolution depends on registry config

        Args:
            instance (LinkedDataClass): instance to add to registry
        """
        resource = instance.rdf_resource
        if resource in self._instance_dict:
            # Another instance with the same ID and resource already registered
            if instance.ID in self._instance_dict[resource]:
                self._handle_conflict_instance(instance)
            else:
                # Schema conflict should ready be resolved at this point
                self._instance_dict[resource][instance.ID] = instance
        # Unlikely but could happen - i.e. user overwriting the _instance_dict.
        else:
            self.register_schema(instance.schema)
            self.register_instance(instance)

    def get_instance(self, resource: URIRef, identifier: IdentifiedNode) -> LinkedDataClass:
        """Get a registered instance from resource and identifier

        Will raise a KeyError if either resource or identifier is not
        registered with the Registry

        Args:
            resource (URIRef): rdf resource of the instance
            identifier (IdentifiedNode): ID of the instance

        Returns:
            LinkedDataClass: instance if found
        """
        return self._instance_dict[resource][identifier]
