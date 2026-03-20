# apicurio-serdes

[![CI](https://github.com/jcbianic/apicurio-serdes/actions/workflows/ci.yml/badge.svg)](https://github.com/jcbianic/apicurio-serdes/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jcbianic/apicurio-serdes/graph/badge.svg?token=YF678N9T0K)](https://codecov.io/gh/jcbianic/apicurio-serdes)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=jcbianic_apicurio-serdes&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=jcbianic_apicurio-serdes)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/jcbianic/apicurio-serdes/badge)](https://securityscorecards.dev/viewer/?uri=github.com/jcbianic/apicurio-serdes)
[![Docs](https://readthedocs.org/projects/apicurio-serdes/badge/)](https://apicurio-serdes.readthedocs.io)
[![PyPI version](https://img.shields.io/pypi/v/apicurio-serdes)](https://pypi.org/project/apicurio-serdes/)
[![Python versions](https://img.shields.io/pypi/pyversions/apicurio-serdes)](https://pypi.org/project/apicurio-serdes/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/apicurio-serdes)](https://pypi.org/project/apicurio-serdes/)
[![License](https://img.shields.io/pypi/l/apicurio-serdes)](https://pypi.org/project/apicurio-serdes/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)

Python serialization library for [Apicurio Registry](https://www.apicur.io/registry/).

Provides Avro serializers that fetch and cache schemas from an Apicurio Registry v3 instance, with support for both sync and async usage. Two wire formats are supported: the Confluent-compatible payload framing and Apicurio's Kafka-headers mode.

## Feature status

| Feature | Status |
|---|---|
| Sync registry client (`ApicurioRegistryClient`) | Shipped |
| Async registry client (`AsyncApicurioRegistryClient`) | Shipped |
| Avro serializer (`AvroSerializer`) | Shipped |
| Avro deserializer (`AvroDeserializer`) | Shipped |
| Confluent wire format (magic byte + globalId) | Shipped |
| Kafka-headers wire format | Shipped |

## Installation

```bash
pip install apicurio-serdes
```

## Quick start

### Sync client

```python
from apicurio_serdes import ApicurioRegistryClient

client = ApicurioRegistryClient(
    url="http://localhost:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

cached = client.get_schema("UserEvent")
# cached.schema     — parsed Avro schema dict (fastavro-ready)
# cached.global_id  — Apicurio globalId
# cached.content_id — Apicurio contentId
```

### Async client

```python
from apicurio_serdes import AsyncApicurioRegistryClient

client = AsyncApicurioRegistryClient(
    url="http://localhost:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

cached = await client.get_schema("UserEvent")
```

### Wire formats

```python
from apicurio_serdes import WireFormat

# Magic byte (0x00) + 4-byte globalId prefix — Confluent-compatible
WireFormat.CONFLUENT_PAYLOAD

# Raw Avro bytes; schema ID carried in a Kafka message header
WireFormat.KAFKA_HEADERS
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, coding standards, and how to submit a pull request.

## License

[MIT](LICENSE)
