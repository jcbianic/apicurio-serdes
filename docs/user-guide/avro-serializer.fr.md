# Avro Serializer

`AvroSerializer` sérialise des données Python en octets Avro au format Confluent,
en récupérant le schema depuis Apicurio Registry lors du premier appel.

## Utilisation de base

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)
serializer = AvroSerializer(registry_client=client, artifact_id="UserEvent")

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload = serializer({"userId": "abc-123", "country": "FR"}, ctx)
```

## Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `registry_client` | `ApicurioRegistryClient` | obligatoire | Le client registry utilisé pour récupérer les schemas. |
| `artifact_id` | `str` | `None` | Identifiant d'artifact statique. Mutuellement exclusif avec `artifact_resolver`. |
| `artifact_resolver` | callable | `None` | Callable `(ctx) -> str` qui dérive l'identifiant d'artifact depuis le contexte de sérialisation. Mutuellement exclusif avec `artifact_id`. |
| `schema` | `dict` | `None` | Schema Avro à enregistrer. Obligatoire quand `auto_register=True` ; ignoré sinon. |
| `auto_register` | `bool` | `False` | Enregistre `schema` dans le registry lors de la première sérialisation si l'artifact est introuvable (HTTP 404). |
| `if_exists` | `str` | `"FIND_OR_CREATE_VERSION"` | Comportement si l'artifact existe déjà lors de l'auto-enregistrement. Valeurs : `"FAIL"`, `"FIND_OR_CREATE_VERSION"`, `"CREATE_VERSION"`. |
| `to_dict` | callable | `None` | Convertit une entrée non-dict en dict avant l'encodage. Voir [Sérialisation personnalisée](../how-to/custom-serialization.md). |
| `use_id` | `"globalId"` ou `"contentId"` | `"globalId"` | L'identifiant de schema à intégrer dans l'en-tête du wire format. Voir [Choisir entre globalId et contentId](../how-to/identifier-selection.md). |
| `strict` | `bool` | `False` | Rejette les champs d'entrée absents du schema avec une `ValueError`. |

## Stratégies de résolution d'artifact

Au lieu d'un `artifact_id` statique, vous pouvez passer `artifact_resolver` — un
callable `(SerializationContext) -> str` qui dérive l'identifiant d'artifact au
moment de la sérialisation. Quatre stratégies intégrées sont disponibles.

### `TopicIdStrategy`

Retourne `"{topic}-{field}"` (ex. `"orders-value"`, `"orders-key"`).
Correspond à la `TopicIdStrategy` Java d'Apicurio.

```python
from apicurio_serdes.avro import TopicIdStrategy

serializer = AvroSerializer(registry_client=client, artifact_resolver=TopicIdStrategy())
```

### `SimpleTopicIdStrategy`

Retourne `"{topic}"` (ex. `"orders"`), en ignorant le champ du message.
Correspond à la `SimpleTopicIdStrategy` Java d'Apicurio.

```python
from apicurio_serdes.avro import SimpleTopicIdStrategy

serializer = AvroSerializer(registry_client=client, artifact_resolver=SimpleTopicIdStrategy())
```

### `QualifiedRecordIdStrategy`

Retourne `"{namespace}.{name}"` quand le schema possède un namespace (ex.
`"com.example.Order"`), ou `"{name}"` sinon (ex. `"Order"`). Le topic et le
champ du message sont ignorés — l'identifiant d'artifact est fixé à la
construction depuis le schema. Correspond à la `RecordNameStrategy` de Confluent.

Chaque instance est spécifique à un schema : passez le dict de schema Avro à la
construction.

```python
from apicurio_serdes.avro import QualifiedRecordIdStrategy

schema = {
    "type": "record",
    "name": "Order",
    "namespace": "com.example",
    "fields": [{"name": "orderId", "type": "string"}],
}
serializer = AvroSerializer(
    registry_client=client,
    artifact_resolver=QualifiedRecordIdStrategy(schema),
    schema=schema,
    auto_register=True,
)
```

Lève une `ValueError` à la construction si le schema ne possède pas de champ
`"name"` ou si le nom est vide.

> **Note** : La `RecordIdStrategy` Java (routage groupId = namespace) n'est **pas**
> implémentée. Utilisez le paramètre `group_id` sur `ApicurioRegistryClient`
> pour ce comportement de routage.

### `TopicRecordIdStrategy`

Retourne `"{topic}-{namespace}.{name}"` quand le schema possède un namespace (ex.
`"orders-com.example.Order"`), ou `"{topic}-{name}"` sinon (ex.
`"orders-Order"`). Correspond à la `TopicRecordNameStrategy` de Confluent.

Chaque instance est spécifique à un schema : passez le dict de schema Avro à la
construction.

```python
from apicurio_serdes.avro import TopicRecordIdStrategy
from apicurio_serdes.serialization import MessageField, SerializationContext

schema = {
    "type": "record",
    "name": "Order",
    "namespace": "com.example",
    "fields": [{"name": "orderId", "type": "string"}],
}
strategy = TopicRecordIdStrategy(schema)
ctx = SerializationContext(topic="orders", field=MessageField.VALUE)
# strategy(ctx) == "orders-com.example.Order"
```

Lève une `ValueError` à la construction si le schema ne possède pas de champ
`"name"` ou si le nom est vide.

> **Note** : La `RecordIdStrategy` Java (routage groupId = namespace) n'est **pas**
> implémentée. Utilisez le paramètre `group_id` sur `ApicurioRegistryClient`
> pour ce comportement de routage.

## Auto-enregistrement

Quand `auto_register=True` et que l'artifact est introuvable dans le registry
(HTTP 404), le sérialiseur appelle `register_schema` pour créer l'artifact avant
la sérialisation :

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    schema={
        "type": "record",
        "name": "UserEvent",
        "namespace": "com.example",
        "fields": [
            {"name": "userId", "type": "string"},
            {"name": "country", "type": "string"},
        ],
    },
    auto_register=True,
)
```

Le paramètre `if_exists` contrôle le comportement si un autre processus a déjà
enregistré l'artifact en parallèle. La valeur par défaut
`"FIND_OR_CREATE_VERSION"` retourne la version existante si le contenu du schema
correspond, ou crée une nouvelle version sinon — ce qui le rend sûr pour les
appels concurrents.

## Exceptions

| Exception | Quand |
|---|---|
| `SchemaNotFoundError` | L'`artifact_id` n'existe pas dans le registry et `auto_register=False`. |
| `SchemaRegistrationError` | `auto_register=True` et le registry a retourné une erreur 4xx ou 5xx, ou le corps de la réponse ne contient pas les identifiants attendus. |
| `RegistryConnectionError` | Le registry est injoignable (erreur réseau). |
| `SerializationError` | Le callable `to_dict` a levé une exception. |
| `ValueError` | Les données ne sont pas conformes au schema Avro, le mode strict a rejeté des champs supplémentaires, ou l'identifiant de schema dépasse la limite 32 bits non signée pour le wire format `CONFLUENT_PAYLOAD` (utilisez `WireFormat.KAFKA_HEADERS` pour le support des identifiants 64 bits). |
| `RuntimeError` | Le client registry sous-jacent a été fermé. |

Consultez [Gestion des erreurs](../how-to/error-handling.md) pour les stratégies
de récupération et des exemples de code.

## Pour aller plus loin

- [Sérialisation personnalisée](../how-to/custom-serialization.md) — dataclasses, modèles Pydantic et objets du domaine
- [Choisir entre globalId et contentId](../how-to/identifier-selection.md) — quand modifier le paramètre `use_id`
- [Mise en cache du schema](../concepts/schema-caching.md) — durée de vie du cache, partage et thread safety
- [Wire Format](../concepts/wire-format.md) — structure des octets de la sortie sérialisée
