__all__ = ("AnnotationError",)


class AnnotationError(BaseException): ...


class ValidationError(BaseException): ...


class MissingSchema(AnnotationError): ...
