from typing import Protocol, Any, Literal, Callable
from rdflib import BNode, URIRef, Namespace
from appnlib.core.schema import Schema, FieldInfo






    @staticmethod
    def has_matching_required(src: Schema | FieldSet, dst: Schema) -> None:
        req_dst = SchemaValidator.get_req_fields(dst)
        if isinstance(src, FieldSet):
            src_fields = SchemaValidator._to_set(src)
            if not req_dst.issubset(src):
                raise Validation
        req_src = SchemaValidator.get_req_fields(src)
        return req_dst == req_src

    def is_valid_subset(src: Schema | FieldSet, dst: Schema) -> bool:
        """Check whether src is a valid subset of dst.

        Src is a valid subset of dst iff
        - If src is a set, it is a subset of dst's attrs fields, and all required fields of dst's attrs
        are in src.
        - If src is a Schema, its attrs' field set is a subset of dst's attrs' field set, all required fields of dst's attrs are in src and also required

        Args:
            src (Schema | FieldSet): source schema
            dst (Schema): dst schema

        Returns:
            bool: whether src is a valid subset of dst
        """
        is_subset = SchemaValidator._to_set(src).issubset(SchemaValidator._to_set(dst))
        has_matching_req = SchemaValidator.has_matching_required(src, dst)
        return has_matching_req and is_subset
