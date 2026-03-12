# Avro Serializer

`AvroSerializer` sérialise des données Python en octets Avro au format Confluent, en récupérant le schema depuis Apicurio Registry lors du premier appel.

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
| `artifact_id` | `str` | obligatoire | L'identifiant de l'artifact de schema dans le registry. |
| `to_dict` | callable | `None` | Convertit une entrée non-dict en dict avant l'encodage. Voir [Sérialisation personnalisée](../how-to/custom-serialization.md). |
| `use_id` | `"globalId"` ou `"contentId"` | `"globalId"` | L'identifiant de schema à intégrer dans l'en-tête du wire format. Voir [Choisir entre globalId et contentId](../how-to/identifier-selection.md). |
| `strict` | `bool` | `False` | Rejette les champs d'entrée absents du schema avec une `ValueError`. |

## Exceptions

| Exception | Quand |
|---|---|
| `SchemaNotFoundError` | L'`artifact_id` n'existe pas dans le registry (HTTP 404). |
| `RegistryConnectionError` | Le registry est injoignable (erreur réseau). |
| `SerializationError` | Le callable `to_dict` a levé une exception. |
| `ValueError` | Les données ne sont pas conformes au schema Avro, le mode strict a rejeté des champs supplémentaires, ou l'identifiant de schema dépasse la limite 32 bits non signée pour le wire format `CONFLUENT_PAYLOAD` (utilisez `WireFormat.KAFKA_HEADERS` pour le support des identifiants 64 bits). |
| `RuntimeError` | Le client registry sous-jacent a été fermé. |

Consultez [Gestion des erreurs](../how-to/error-handling.md) pour les stratégies de récupération et des exemples de code.

## Pour aller plus loin

- [Sérialisation personnalisée](../how-to/custom-serialization.md) — sérialiser des dataclasses, modèles Pydantic et objets du domaine
- [Choisir entre globalId et contentId](../how-to/identifier-selection.md) — quand modifier le paramètre `use_id`
- [Mise en cache du schema](../concepts/schema-caching.md) — durée de vie du cache, partage et thread safety
- [Wire Format](../concepts/wire-format.md) — structure des octets de la sortie sérialisée
