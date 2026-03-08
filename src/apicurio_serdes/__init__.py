"""apicurio-serdes: Python serialization library for Apicurio Registry."""

from apicurio_serdes._client import ApicurioRegistryClient
from apicurio_serdes.serialization import WireFormat

__all__ = ["ApicurioRegistryClient", "WireFormat"]
