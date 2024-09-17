from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Generator,
    Optional,
    Self,
    Type,
    Union,
    cast,
)
from typing import Literal as PyLiteral

import msgspec
from msgspec import Struct, field
from rdflib import BNode, Graph, IdentifiedNode, Literal, Namespace, URIRef
from rdflib.graph import _ContextIdentifierType, _TripleType
from rdflib.namespace import XSD, NamespaceManager
from rdflib.store import Store

from appnlib.core.exceptions import AnnotationError, IntegrityError
from appnlib.core.types import Schema
from appnlib.core.utils import make_ref
from appnlib.core.validator import SchemaValidator

if TYPE_CHECKING:
    from rdflib._type_checking import _NamespaceSetString

__all__ = ("LinkedDataClass",)

EncHookT = Optional[Callable[[Any], Any]]
DecHookT = Optional[Callable[[type, Any], Any]]


class LinkedDataClass(Struct, kw_only=True):
    """Base Linked DataClass"""

    id: str = field(default_factory=BNode)
    """Instance ID. If not provided, will be assigned a blank node ID"""
    __schema__: ClassVar[Schema]
    """Schema object. Class attribute"""

    @property
    def ID(self) -> IdentifiedNode:
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
        if hasattr(cls, "__schema__"):
            if not SchemaValidator.describe_attrs(attrs=cls, schema=cls.__schema__, mode="full"):
                raise AnnotationError("Schema does not fully describe LinkedDataClass")
        # Register
        Registry().register_schema(getattr(cls, "__schema__"))
        return super().__init_subclass__()

    def __post_init__(self) -> None:
        Registry().register_instance(self)


def default_enc_hook(obj: Any) -> Any:
    if isinstance(obj, (Literal, IdentifiedNode)):
        return obj.toPython()
    raise TypeError(f"Invalid encoding type: {type(obj)}")


def default_dec_hook(type: Type, obj: Any) -> Any:
    if issubclass(type, IdentifiedNode):
        return make_ref(str(obj))


class Codec:
    def __init__(
        self,
        enc_hook: EncHookT = default_enc_hook,
        dec_hook: DecHookT = default_dec_hook,
    ) -> None:
        self.enc_hook = enc_hook
        self.dec_hook = dec_hook

    def encode_to_dict(self, dataclass: LinkedDataClass, enc_hook: EncHookT = None) -> dict[str, Any]:
        return cast(dict[str, Any], msgspec.to_builtins(obj=dataclass, enc_hook=enc_hook))

    def encode_to_triple(self, dataclass: LinkedDataClass) -> list[_TripleType]:
        result: list[_TripleType] = []
        schema = dataclass.schema
        for sfield in dataclass.__struct_fields__:
            if sfield == "id":
                continue
            value = getattr(dataclass, sfield)
            info = schema.attrs[sfield]
            if not isinstance(value, str) and hasattr(value, "__len__"):
                if not info.repeat:
                    raise AnnotationError(f"field {sfield} is not annotated as repeat but is of container type: {type(value)}")
            else:
                value = [value]
            for _value in value:
                _value = make_ref(_value) if info.range == XSD.IDREF else Literal(_value, datatype=info.range)
                result.append((dataclass.ID, info.ref, _value))

        if hasattr(dataclass, "__dict__"):
            for sfield, value in dataclass.__dict__.items():
                if not hasattr(value, "__len__") or isinstance(value, str):
                    value = [value]
                for _value in value:
                    result.append((dataclass.ID, Literal(info.ref), Literal(_value)))
        return result

    def decode_triple_to_dict(
        self,
        triple: Generator[_TripleType, None, None] | list[_TripleType],
        schema: Schema,
    ) -> LinkedDataClass:
        pass

    def decode_from_dict(
        self,
        attrs: dict[str, Any],
        model: Type[LinkedDataClass],
        dec_hook: DecHookT = None,
        **kwargs: Any,
    ) -> LinkedDataClass:
        dec_hook = dec_hook if dec_hook else self.dec_hook
        return cast(
            LinkedDataClass,
            msgspec.convert(attrs, type=model, dec_hook=dec_hook, **kwargs),
        )


DEFAULT_CODEC = Codec()


class RegistryConfig(Struct):
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


class Session:
    def __init__(
        self,
        store: Union[Store, str] = "default",
        identifier: Optional[Union[_ContextIdentifierType, str]] = None,
        namespace_manager: Optional[NamespaceManager] = None,
        base: Optional[str] = None,
        bind_namespaces: "_NamespaceSetString" = "rdflib",
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
        destination: str,
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
    ) -> None:
        self._graph.serialize(
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
    _schema_dict: ClassVar[dict[URIRef, Schema]] = dict()
    _instance_dict: ClassVar[dict[URIRef, dict[IdentifiedNode, LinkedDataClass]]] = dict()
    _session_dict: ClassVar[dict[IdentifiedNode, Session]] = dict()
    __config__: ClassVar[RegistryConfig] = RegistryConfig()

    def __new__(self, *args: Any, **kwargs: Any) -> Self:
        if not self._instance:
            self._instance = super().__new__(self, *args, **kwargs)
        return cast(Self, self._instance)

    def _handle_conflict_instance(
        self,
        instance: LinkedDataClass,
    ) -> None:
        match self.__config__.on_confict_identifier:
            case "raise":
                raise IntegrityError(f"A previous instance with the same ID have been registered: {instance.ID}")
            case "overwrite":
                self._instance_dict[instance.rdf_resource][instance.ID] = instance
                return

    def _handle_conflict_schema(self, obj: Schema) -> None:
        match self.__config__.on_conflict_schema:
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
                elif SchemaValidator.is_sub_schema(prev_obj, obj):
                    self._schema_dict[obj.rdf_resource] = obj
                    return
                else:
                    raise IntegrityError(f"Conflicting schemas that are not sub schema of one another: {obj.rdf_resource}")

    def create_session(
        self,
        store: Union[Store, str] = "default",
        identifier: Optional[Union[_ContextIdentifierType, str]] = None,
        namespace_manager: Optional[NamespaceManager] = None,
        base: Optional[str] = None,
        bind_namespaces: "_NamespaceSetString" = "rdflib",
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
            self._instance_dict[schema.rdf_resource] = dict()

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
