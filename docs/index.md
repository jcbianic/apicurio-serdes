# apicurio-serdes

Python serialization library for Apicurio Registry.

## Overview

`apicurio-serdes` provides `AvroSerializer` and `AvroDeserializer` backed by
the native Apicurio Registry v3 API, with an interface intentionally compatible
with `confluent-kafka`'s schema registry API.

## Installation

```bash
pip install apicurio-serdes
```

## Quick Start

```python
from apicurio_serdes import (
    ApicurioRegistryClient,
    AvroDeserializer,
    AvroSerializer,
    SerializationContext,
)
```

See the [User Guide](user-guide/deserialization.md) for detailed usage.
