from msgspec import Struct
from rdflib import URIRef


class IDRef(Struct):
    ref: URIRef


class FieldInfo(Struct):
    ref: URIRef
    range: URIRef | IDRef | None = None


class Schema(Struct):
    rdf_resource: URIRef
    attrs: dict[str, FieldInfo]

    @property
    def name_mapping(self) -> dict[str, FieldInfo]:
        """Mapping from name to field information

        Returns:
            dict[str, FieldInfo]: returned object
        """
        return self.attrs

    @property
    def ref_mapping(self) -> dict[URIRef, str]:
        """Mapping from field reference to field name

        Returns:
            dict[URIRef, str]: returned object
        """
        return {item.ref: name for name, item in self.attrs.items()}
