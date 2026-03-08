# Modèle d'adressage

Apicurio Registry organise les schemas selon une hiérarchie à trois niveaux : **group**, **artifact** et **version**. Cette page explique la signification de chaque niveau, pourquoi `group_id` est requis dans `apicurio-serdes`, et comment cela se transpose par rapport à l'espace de noms plat de Confluent Schema Registry.

## La hiérarchie

```text
Registry
 └── Group (e.g., "com.example.schemas")
      ├── Artifact: "UserEvent"
      │    ├── Version 1  (schema v1)
      │    └── Version 2  (schema v2, latest)
      └── Artifact: "OrderEvent"
           └── Version 1  (schema v1, latest)
```

### Group

Un espace de noms logique pour un ensemble de schemas apparentés. Les groups sont similaires aux packages en Java ou aux modules en Python — ils évitent les collisions de noms et fournissent une structure organisationnelle.

Exemples :

- `com.example.schemas` — tous les schemas d'une équipe ou d'un domaine
- `payments` — schemas liés au service de paiements
- `default` — le groupe par défaut lorsqu'aucun n'est spécifié

### Artifact

Un schema nommé au sein d'un groupe. Chaque artifact possède un `artifact_id` unique au sein de son groupe. Un artifact peut avoir plusieurs versions à mesure que le schema évolue.

### Version

Une révision spécifique d'un artifact. Les versions sont numérotées séquentiellement (`1`, `2`, `3`, ...). L'alias `latest` pointe toujours vers la version la plus récente.

## Pourquoi `group_id` est requis

Dans `apicurio-serdes`, le `group_id` est un **paramètre obligatoire** de l'`ApicurioRegistryClient` :

```python
client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",  # Required
)
```

Cela s'explique par le fait que l'API REST v3 d'Apicurio inclut le groupe dans chaque URL d'artifact :

```text
GET /groups/{groupId}/artifacts/{artifactId}/versions/latest/content
```

Sans groupe, l'appel API ne peut pas être construit. Chaque recherche de schema doit savoir dans quel groupe chercher.

## Comparaison avec Confluent Schema Registry

Confluent Schema Registry utilise un espace de noms plat sans notion de groupe :

| Concept | Confluent Schema Registry | Apicurio Registry |
|---------|--------------------------|-------------------|
| Espace de noms | Aucun (plat) | Group |
| Identifiant de schema | Subject (par ex., `user-events-value`) | Group + Artifact (par ex., `com.example.schemas` / `UserEvent`) |
| Convention de nommage | `<topic>-<key\|value>` | Libre au sein d'un groupe |
| Multi-tenancy | Registries séparés | Groups au sein d'un seul registry |

### Migration des subjects Confluent vers Apicurio

Lors d'une migration de Confluent Schema Registry vers Apicurio, vous devez décider :

1. **Dans quel groupe** placer vos schemas (par ex., `com.example.schemas`)
2. **Quel artifact ID** utiliser pour chaque schema

Exemples courants de correspondance :

| Subject Confluent | Group Apicurio | Artifact Apicurio |
|-------------------|---------------|-------------------|
| `user-events-value` | `com.example.schemas` | `UserEvent` |
| `order-events-value` | `com.example.schemas` | `OrderEvent` |
| `user-events-key` | `com.example.schemas` | `UserEventKey` |

Le point essentiel : **le nom du subject Confluent encode à la fois l'identité du schema et le lien avec le topic dans une seule chaîne.** Dans Apicurio, ce sont des concepts séparés — l'artifact ID est l'identité du schema, et le lien avec le topic se fait au niveau applicatif.

## Comment `apicurio-serdes` utilise la hiérarchie

Lorsque vous créez un serializer :

```python
serializer = AvroSerializer(
    registry_client=client,       # client knows group_id
    artifact_id="UserEvent",      # artifact within that group
)
```

Le serializer résout le schema en appelant :

```text
GET /groups/com.example.schemas/artifacts/UserEvent/versions/latest/content
```

La réponse inclut à la fois un `globalId` et un `contentId` dans les en-têtes HTTP. Le serializer utilise l'un de ces identifiants (configurable via `use_id`) dans l'en-tête du [wire format](wire-format.md).
