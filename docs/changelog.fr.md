# Journal des modifications

Toutes les modifications visibles par les utilisateurs sont documentées ici.

## Non publié

### Ajouts

- `AvroDeserializer` et `AsyncAvroDeserializer` acceptent un paramètre optionnel
  `reader_schema` (dict de schema Avro, défaut `None`). Quand il est fourni,
  fastavro effectue une résolution de schema Avro entre le schema d'écriture
  (embarqué dans le message) et le schema lecteur fourni, permettant les
  patrons d'évolution de schema : les valeurs par défaut remplissent les
  nouveaux champs ajoutés, les promotions de type sont supportées, ainsi que
  les renommages de champs via alias. Parsé une seule fois à la construction.
- Méthode `register_schema(artifact_id, schema, if_exists)` sur `ApicurioRegistryClient`
  et `AsyncApicurioRegistryClient`. Enregistre un artifact de schema via l'endpoint
  Apicurio Registry v3 `POST /groups/{groupId}/artifacts` et peuple le cache
  interne en cas de succès.
- `AvroSerializer` accepte trois nouveaux paramètres optionnels : `schema` (dict
  de schema Avro), `auto_register` (bool, défaut `False`) et `if_exists` (politique
  `ifExists` v3). Quand `auto_register=True`, le premier appel à serialize enregistre
  le schema automatiquement si l'artifact est introuvable (HTTP 404).
- `SchemaRegistrationError` — nouvelle exception typée levée quand le registry
  rejette une demande d'enregistrement de schema (réponse 4xx/5xx ou champs JSON
  manquants dans le corps de la réponse). Exportée depuis la racine du paquet.
- Les valeurs de `if_exists` suivent l'API Apicurio Registry v3 : `"FAIL"`,
  `"FIND_OR_CREATE_VERSION"` (défaut), `"CREATE_VERSION"`.
- `QualifiedRecordIdStrategy` — nouvelle stratégie de résolution d'artifact. Dérive
  l'identifiant d'artifact depuis le nom et le namespace du record Avro :
  `"{namespace}.{name}"` quand le namespace est présent, `"{name}"` sinon.
  Correspond à la `RecordNameStrategy` de Confluent. Lève une `ValueError` à la
  construction si le schema ne possède pas de champ `"name"`.
- `TopicRecordIdStrategy` — nouvelle stratégie de résolution d'artifact. Dérive
  l'identifiant d'artifact depuis le topic et le nom du record Avro :
  `"{topic}-{namespace}.{name}"` quand le namespace est présent,
  `"{topic}-{name}"` sinon. Correspond à la `TopicRecordNameStrategy` de Confluent.
  Lève une `ValueError` à la construction si le schema ne possède pas de champ
  `"name"`.

## 0.2.0 (2026-03-11)

### Durcissement des clients et déduplication

Cette version se concentre sur l'amélioration de la robustesse et de la maintenabilité par le durcissement complet des clients et la déduplication du code.

### Ajouts

- `ApicurioRegistryClient` — client HTTP pour l'API native v3 d'Apicurio Registry avec mise en cache des schemas et accès thread-safe.
- `AsyncApicurioRegistryClient` — équivalent asynchrone utilisant `httpx.AsyncClient`, adapté à l'utilisation concurrente de coroutines.
- `AvroSerializer` — sérialise les données Python en octets Avro au cadrage Confluent. Prend en charge les hooks `to_dict` personnalisés, la sélection du wire format `globalId`/`contentId`, le mode strict, et le wire format `KAFKA_HEADERS`.
- `AvroDeserializer` — désérialise les octets Avro au cadrage Confluent en dicts Python avec hook `from_dict` optionnel.
- `AsyncAvroDeserializer` — équivalent asynchrone d'`AvroDeserializer`.
- `SerializationContext` et `MessageField` — objets de contexte légers compatibles avec l'interface de confluent-kafka.
- Enum `WireFormat` — modes de cadrage `CONFLUENT_PAYLOAD` et `KAFKA_HEADERS`.
- `SchemaNotFoundError`, `RegistryConnectionError`, `SerializationError`, `DeserializationError` — hiérarchie d'exceptions typées pour une gestion d'erreurs prévisible.
- `CachedSchema` — dataclass gelée (immutable) contenant les données de schema résolues et les métadonnées du registry.
- Protection contre l'utilisation d'un client fermé (`RuntimeError`) sur les clients sync et async.
- Validation de l'identifiant de schema 32 bits pour le wire format `CONFLUENT_PAYLOAD` avec message d'erreur suggérant `KAFKA_HEADERS`.
- Validation de la plage int64 signé sur les `globalId`/`contentId` des en-têtes de réponse du registry.
- 19 Architecture Decision Records dans `docs/decisions/`.

### Modifié

- **Rupture** : le défaut de `use_id` d'`AvroDeserializer` et `AsyncAvroDeserializer` est passé de `"contentId"` à `"globalId"` pour correspondre au défaut d'`AvroSerializer` (voir ADR-006).

### Interne

- Extraction de la classe de base partagée `_RegistryClientBase` pour dédupliquer la logique des clients sync/async (ADR-001).
- Pattern de verrouillage à double vérification pour le remplissage du cache thread-safe (ADR-004).
- Suppression du fichier obsolète `TECHNICAL_DEBT.md`.
