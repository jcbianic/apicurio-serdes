# Installation

## Requirements

- Python 3.10 or newer
- Apicurio Registry 3.x

## Install

If your project uses [uv](https://docs.astral.sh/uv/):

```bash
uv add apicurio-serdes
```

Or with pip:

```bash
pip install apicurio-serdes
```

## Verify

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer

print("apicurio-serdes is ready.")
```

Next: follow the [Quickstart](quickstart.md) to serialize your first message.
