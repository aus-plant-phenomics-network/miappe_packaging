from __future__ import annotations
from typing import (
    ClassVar,
    Any,
    Optional,
    Callable,
    Type,
    cast,
    Generator,
    TypeVar,
    overload,
    Union,
    TYPE_CHECKING,
)
import msgspec
from msgspec import Struct, field
from rdflib import BNode, URIRef, IdentifiedNode, Literal, Graph
from rdflib.store import Store
from rdflib.namespace import NamespaceManager
from rdflib.graph import _TripleType, _ContextIdentifierType
from appnlib.core.exceptions import AnnotationError
from appnlib.core.types import Schema, IDRef
from appnlib.core.utils import make_ref
from appnlib.core.validator import SchemaValidator
from typing import Self

if TYPE_CHECKING:
    from rdflib._type_checking import _NamespaceSetString

__all__ = ("LinkedDataClass",)

_LinkedDataClassT = TypeVar("_LinkedDataClassT", bound="LinkedDataClass")
EncHookT = Optional[Callable[[Any], Any]]
DecHookT = Optional[Callable[[type, Any], Any]]


class LinkedDataClass(Struct, kw_only=True):
    """Base Linked DataClass"""

    id: str | IdentifiedNode = field(default_factory=BNode)
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
            if not SchemaValidator.describe_attrs(
                attrs=cls, schema=cls.__schema__, mode="full"
            ):
                raise AnnotationError("Schema does not fully describe LinkedDataClass")
        # Register
        Registry().register_class(cls)
        return super().__init_subclass__()

    def __post_init__(self) -> None:
        Registry().register_instance(self)


def default_enc_hook(obj: Any) -> Any:
    if isinstance(obj, (Literal, IdentifiedNode)):
        return obj.toPython()
    raise TypeError(f"Invalid encoding type: {type(obj)}")


def default_dec_hook(type: Type, obj: Any) -> Any:
    if type is IdentifiedNode:
        return make_ref(str(obj))


class Codec:
    def __init__(
        self,
        enc_hook: EncHookT = default_enc_hook,
        dec_hook: DecHookT = default_dec_hook,
    ) -> None:
        self.enc_hook = enc_hook
        self.dec_hook = dec_hook

    def encode_to_dict(
        self, dataclass: LinkedDataClass, enc_hook: EncHookT = None
    ) -> dict[str, Any]:
        return msgspec.to_builtins(obj=dataclass, enc_hook=enc_hook)

    def encode_to_triple(
        self, dataclass: LinkedDataClass
    ) -> Generator[_TripleType, None, None]:
        pass

    def decode_from_triple(
        self, triple: Generator[_TripleType, None, None]
    ) -> _LinkedDataClassT:
        pass

    def decode_from_dict(
        self,
        attrs: dict[str, Any],
        model: Type[LinkedDataClass],
        dec_hook: DecHookT = None,
        **kwargs: Any,
    ) -> _LinkedDataClassT:
        dec_hook = dec_hook if dec_hook else self.dec_hook
        return msgspec.from_builtins(attrs, type=model, dec_hook=dec_hook, **kwargs)


DEFAULT_CODEC = Codec()


class RegistryConfig:
    pass


class Session(Graph):
    def _add_dataclass(
        self, dataclass: LinkedDataClass, codec: Codec = DEFAULT_CODEC
    ) -> Self:
        triples = codec.encode_to_triple(dataclass=dataclass)
        self.addN((s, p, o, self) for s, p, o in triples)
        return self

    def add_dataclass(
        self, dataclass: LinkedDataClass, codec: Codec = DEFAULT_CODEC
    ) -> Self:
        self._add_dataclass(dataclass, codec)
        registry = Registry()
        schema = dataclass.schema
        for name, info in schema.attrs.items():
            if isinstance(info.range, IDRef):
                ref_resource = info.range.ref
                range_value = getattr(dataclass, name)
                if not isinstance(range_value, str) and hasattr(range_value, "__len__"):
                    range_value = [range_value]
                for value in range_value:
                    matched_instance = registry.get_instance(
                        resource=ref_resource, identifier=make_ref(value)
                    )
                    self._add_dataclass(matched_instance, codec)
        return self

    def subgraph(
        self, identifier: IdentifiedNode
    ) -> Generator[_TripleType, None, None]:
        return self.triples((identifier, None, None))

    def to_json(
        self,
        destination: str,
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
    ) -> None:
        self.serialize(
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
    _type_dict: ClassVar[dict[URIRef, type[LinkedDataClass]]] = dict()
    _instance_dict: ClassVar[dict[URIRef, dict[IdentifiedNode, LinkedDataClass]]] = (
        dict()
    )
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
        pass

    def _handle_conflict_object(self, obj: Type[LinkedDataClass]) -> None:
        pass

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
        self._session_dict[session.identifier] = session
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
            self._session_dict.pop(key=identifier)

    def register_class(self, cls: Type[LinkedDataClass]) -> None:
        """Add an object to registry, indexed by its rdf_resource

        All LinkedDataClass subclasses are automatically registered
        at object construction

        If a similar object with the same ID has been registered,
        resolution depends on the registry config

        Args:
            cls (Type[LinkedDataClass]): a LinkedDataClass subclass
        """
        if cls.rdf_resource in self._type_dict:
            self._handle_conflict_object(cls)
        else:
            self._type_dict[cls.rdf_resource] = cls
            self._instance_dict[cls.rdf_resource] = dict()

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
            if instance.ID in self._instance_dict[resource]:
                self._handle_conflict_instance(instance)
            else:
                self._instance_dict[resource] = instance
        else:
            self.register_class(instance.__class__)
            self.register_instance(instance)

    def get_instance(
        self, resource: URIRef, identifier: IdentifiedNode
    ) -> LinkedDataClass:
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
