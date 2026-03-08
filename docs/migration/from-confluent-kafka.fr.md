# Migration depuis confluent-kafka

Ce guide recense toutes les différences entre les serializers du schema registry de `confluent-kafka` et ceux d'`apicurio-serdes`, afin de vous permettre de mettre à jour votre code producteur en toute confiance.

## Comparaison des API

### Noms de classes

| confluent-kafka | apicurio-serdes | Notes |
|-----------------|-----------------|-------|
| `SchemaRegistryClient` | `ApicurioRegistryClient` | Paramètres de construction différents |
| `AvroSerializer` | `AvroSerializer` | Même nom, même convention d'appel |
| `SerializationContext` | `SerializationContext` | Même interface |
| `MessageField` | `MessageField` | Mêmes valeurs d'enum (`KEY`, `VALUE`) |

### Paramètres du constructeur

=== "confluent-kafka"

    ```python
    from confluent_kafka.schema_registry import SchemaRegistryClient
    from confluent_kafka.schema_registry.avro import AvroSerializer

    registry = SchemaRegistryClient({
        "url": "http://registry:8080/apis/ccompat/v7",
    })
    serializer = AvroSerializer(
        schema_registry_client=registry,
        schema_str='{"type":"record","name":"UserEvent",...}',
        to_dict=my_to_dict,
    )
    ```

=== "apicurio-serdes"

    ```python
    from apicurio_serdes import ApicurioRegistryClient
    from apicurio_serdes.avro import AvroSerializer

    client = ApicurioRegistryClient(
        url="http://registry:8080/apis/registry/v3",
        group_id="com.example.schemas",
    )
    serializer = AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
        to_dict=my_to_dict,
    )
    ```

Différences clés :

| Paramètre | confluent-kafka | apicurio-serdes |
|-----------|-----------------|-----------------|
| URL du registry | Endpoint ccompat (`/apis/ccompat/v7`) | Endpoint natif v3 (`/apis/registry/v3`) |
| Source du schema | `schema_str` (JSON Avro en ligne) | `artifact_id` (récupéré depuis le registry) |
| Groupe | Non applicable | `group_id` (**obligatoire** sur le client) |
| ID wire format | Non configurable (utilise l'ID de schema) | `use_id` — `"globalId"` (par défaut) ou `"contentId"` |
| Mode strict | Non disponible | `strict=True` rejette les champs supplémentaires |

### Schémas d'appel

L'appel de sérialisation en lui-même est identique :

```python
# Both libraries use the same calling convention
ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload: bytes = serializer({"userId": "abc", "country": "FR"}, ctx)
```

### Types d'exceptions

| confluent-kafka | apicurio-serdes | Quand |
|-----------------|-----------------|-------|
| `SchemaRegistryError` | `SchemaNotFoundError` | L'artifact n'existe pas (404) |
| `KafkaException` (réseau) | `RegistryConnectionError` | Le registry est injoignable |
| N/A | `SerializationError` | Le hook `to_dict` a levé une exception |
| `SerializerError` | `ValueError` | Les données ne correspondent pas au schema |

## Comprendre `group_id`

C'est la différence la plus importante. Dans Apicurio Registry, les schemas sont organisés selon une hiérarchie :

```text
Registry
 └── Group (e.g., "com.example.schemas")
      └── Artifact (e.g., "UserEvent")
           └── Version (e.g., "1", "2", "latest")
```

`group_id` identifie le groupe qui contient vos schemas. Il est **obligatoire** car l'API v3 d'Apicurio inclut le groupe dans chaque URL d'artifact.

### Pourquoi Confluent n'en a pas besoin

Confluent Schema Registry utilise un espace de nommage plat — les schemas sont identifiés uniquement par un nom de « subject » (généralement `<topic>-key` ou `<topic>-value`). Il n'y a pas de notion de groupe.

### Correspondance entre vos subjects Confluent et Apicurio

Si vous migrez de Confluent Schema Registry vers Apicurio Registry :

| Subject Confluent | Correspondance Apicurio |
|-------------------|-------------------------|
| `user-events-value` | Groupe : `com.example.schemas`, Artifact : `UserEvent` |
| `order-events-key` | Groupe : `com.example.schemas`, Artifact : `OrderKey` |

Le groupe est une frontière logique que vous choisissez lors de l'enregistrement des schemas dans Apicurio. Un usage courant consiste à utiliser le nom de domaine inversé de votre organisation (par ex., `com.example.schemas`).

## Différences de comportement

| Comportement | confluent-kafka | apicurio-serdes |
|--------------|-----------------|-----------------|
| Source du schema | Chaîne JSON en ligne ou auto-enregistrée | Toujours récupéré depuis le registry par `artifact_id` |
| Auto-enregistrement | Pris en charge (`auto.register.schemas=True`) | Non pris en charge — les schemas doivent exister dans le registry |
| Cache de schema | Par instance de `SchemaRegistryClient` | Par instance d'`ApicurioRegistryClient` |
| Thread safety | Thread-safe | Thread-safe |
| Wire format | Cadrage Confluent (`0x00` + ID sur 4 octets) | Même cadrage Confluent (compatible) |
| Évolution de schema | Gérée par les règles de compatibilité du registry | Identique — Apicurio applique les règles de compatibilité |

## Exemple de migration minimal

### Avant (confluent-kafka)

```python
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import (
    SerializationContext,
    MessageField,
)

schema_str = '{"type":"record","name":"UserEvent","fields":[{"name":"userId","type":"string"},{"name":"country","type":"string"}]}'

registry = SchemaRegistryClient({"url": "http://registry:8080/apis/ccompat/v7"})
serializer = AvroSerializer(registry, schema_str)

producer = Producer({"bootstrap.servers": "kafka:9092"})
ctx = SerializationContext("user-events", MessageField.VALUE)

producer.produce("user-events", value=serializer({"userId": "abc", "country": "FR"}, ctx))
producer.flush()
```

### Après (apicurio-serdes)

```python
from confluent_kafka import Producer
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)
serializer = AvroSerializer(registry_client=client, artifact_id="UserEvent")

producer = Producer({"bootstrap.servers": "kafka:9092"})
ctx = SerializationContext("user-events", MessageField.VALUE)

producer.produce("user-events", value=serializer({"userId": "abc", "country": "FR"}, ctx))
producer.flush()
```

**Ce qui a changé** : les lignes d'import et la configuration du client. L'appel `producer.produce()` est identique — les octets produits utilisent le même wire format Confluent.

## Étapes suivantes

- [Modèle d'adressage](../concepts/addressing-model.md) — comprendre la hiérarchie groupe/artifact/version
- [Démarrage rapide](../getting-started/quickstart.md) — exemple complet fonctionnel partant de zéro
- [Référence API](../api-reference/index.md) — documentation complète des paramètres
