__all__ = ("AnnotationError",)


class AnnotationError(BaseException): ...


class SchemaError(AnnotationError): ...


class IdError(BaseException): ...
