"""apicurio-serdes: Python serialization library for Apicurio Registry."""

from importlib.metadata import version

from apicurio_serdes._async_client import AsyncApicurioRegistryClient
from apicurio_serdes._client import ApicurioRegistryClient
from apicurio_serdes._errors import (
    DeserializationError,
    RegistryConnectionError,
    ResolverError,
    SchemaNotFoundError,
    SchemaRegistrationError,
    SerializationError,
)
from apicurio_serdes.serialization import WireFormat

__version__ = version("apicurio-serdes")

__all__ = [
    "ApicurioRegistryClient",
    "AsyncApicurioRegistryClient",
    "DeserializationError",
    "RegistryConnectionError",
    "ResolverError",
    "SchemaNotFoundError",
    "SchemaRegistrationError",
    "SerializationError",
    "WireFormat",
    "__version__",
]
