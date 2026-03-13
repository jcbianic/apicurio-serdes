"""Error types for apicurio-serdes."""

from __future__ import annotations


class SchemaNotFoundError(Exception):
    """Raised when an artifact or schema ID does not exist in the registry.

    Two construction paths set different attributes:

    Artifact-based lookups (``SchemaNotFoundError(group_id, artifact_id)``):
        group_id: The group that was searched.
        artifact_id: The artifact that was not found.

    ID-based lookups (``SchemaNotFoundError.from_id(id_type, id_value)``):
        id_type: The ID type that was searched ("globalId" or "contentId").
        id_value: The numeric ID that was not found.
    """

    id_type: str
    id_value: int

    def __init__(self, group_id: str, artifact_id: str) -> None:
        self.group_id = group_id
        self.artifact_id = artifact_id
        super().__init__(
            f"Schema not found: artifact '{artifact_id}' in group '{group_id}'"
        )

    @classmethod
    def from_id(cls, id_type: str, id_value: int) -> SchemaNotFoundError:
        """Create a SchemaNotFoundError for an ID-based lookup failure.

        Args:
            id_type: "globalId" or "contentId".
            id_value: The numeric identifier that was not found.

        Returns:
            A SchemaNotFoundError with id_type and id_value attributes set.
        """
        err = cls.__new__(cls)
        err.id_type = id_type
        err.id_value = id_value
        Exception.__init__(err, f"Schema not found: {id_type} {id_value}")
        return err


class DeserializationError(Exception):
    """Raised when deserialization fails (FR-003, FR-004, FR-009, FR-011).

    Covers: invalid magic byte, input too short, Avro decode failure,
    and from_dict hook failure. When wrapping an underlying exception,
    the original is set as __cause__ to preserve the full traceback.

    Attributes:
        cause: The original exception, if any.
    """

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        self.cause = cause
        super().__init__(message)
        if cause is not None:
            self.__cause__ = cause


class SerializationError(Exception):
    """Raised when the ``to_dict`` callable fails during serialization.

    Wraps the original exception as ``__cause__`` so the full traceback is
    preserved. Distinguishes hook failure from Avro schema validation errors.

    Args:
        cause: The original exception raised by the ``to_dict`` callable.

    Attributes:
        cause: The original exception raised by the ``to_dict`` callable.
    """

    def __init__(self, cause: Exception) -> None:
        self.cause = cause
        super().__init__(f"to_dict conversion failed: {cause}")
        self.__cause__ = cause


class AuthenticationError(Exception):
    """Raised when authentication with the token endpoint fails.

    Covers: token endpoint unreachable, non-200 response from token endpoint.

    Args:
        message: Description of the authentication failure.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class RegistryConnectionError(Exception):
    """Raised when the Apicurio Registry is unreachable.

    Wraps the underlying network exception as ``__cause__``. Includes
    the registry URL in the error message so callers can identify which
    endpoint failed.

    Args:
        url: The registry base URL that could not be reached.
        cause: The underlying network exception.

    Attributes:
        url: The registry base URL that could not be reached.
    """

    def __init__(self, url: str, cause: Exception) -> None:
        self.url = url
        super().__init__(f"Unable to connect to registry at {url}: {cause}")
        self.__cause__ = cause
