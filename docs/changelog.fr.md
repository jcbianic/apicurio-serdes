# Journal des modifications

Toutes les modifications visibles par les utilisateurs sont documentées ici.

## 0.1.0 (non publié)

### Ajouts

- `ApicurioRegistryClient` — client HTTP pour l'API native v3 d'Apicurio Registry avec mise en cache des schemas et accès thread-safe.
- `AvroSerializer` — sérialise les données Python en octets Avro au cadrage Confluent. Prend en charge les hooks `to_dict` personnalisés, la sélection du wire format `globalId`/`contentId`, et le mode strict.
- `SerializationContext` et `MessageField` — objets de contexte légers compatibles avec l'interface de confluent-kafka.
- `SchemaNotFoundError`, `RegistryConnectionError`, `SerializationError` — hiérarchie d'exceptions typées pour une gestion d'erreurs prévisible.
