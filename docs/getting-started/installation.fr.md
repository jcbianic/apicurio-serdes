# Installation

## Prérequis

- Python 3.10 ou version ultérieure
- Apicurio Registry 3.x

## Installer

Si votre projet utilise [uv](https://docs.astral.sh/uv/) :

```bash
uv add apicurio-serdes
```

Ou avec pip :

```bash
pip install apicurio-serdes
```

## Vérifier

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer

print("apicurio-serdes is ready.")
```

Ensuite : suivez le [Démarrage rapide](quickstart.md) pour sérialiser votre premier message.
