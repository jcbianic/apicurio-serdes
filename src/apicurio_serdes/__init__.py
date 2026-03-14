"""apicurio-serdes: Python serialization library for Apicurio Registry."""

from importlib.metadata import version

from apicurio_serdes._async_client import AsyncApicurioRegistryClient
from apicurio_serdes._auth import BearerAuth, KeycloakAuth
from apicurio_serdes._client import ApicurioRegistryClient
from apicurio_serdes._errors import (
    AuthenticationError,
    DeserializationError,
    RegistryConnectionError,
    SchemaNotFoundError,
    SerializationError,
)
from apicurio_serdes.serialization import WireFormat

__version__ = version("apicurio-serdes")

__all__ = [
    "ApicurioRegistryClient",
    "AsyncApicurioRegistryClient",
    "AuthenticationError",
    "BearerAuth",
    "DeserializationError",
    "KeycloakAuth",
    "RegistryConnectionError",
    "SchemaNotFoundError",
    "SerializationError",
    "WireFormat",
    "__version__",
]
