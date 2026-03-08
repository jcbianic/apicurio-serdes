"""Error types for apicurio-serdes."""

from __future__ import annotations


class SchemaNotFoundError(Exception):
    """Raised when an artifact does not exist in the registry (HTTP 404).

    Args:
        group_id: The group that was searched.
        artifact_id: The artifact that was not found.

    Attributes:
        group_id: The group that was searched.
        artifact_id: The artifact that was not found.
    """

    def __init__(self, group_id: str, artifact_id: str) -> None:
        self.group_id = group_id
        self.artifact_id = artifact_id
        super().__init__(
            f"Schema not found: artifact '{artifact_id}' in group '{group_id}'"
        )


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
