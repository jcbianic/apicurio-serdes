# Wire Format

`apicurio-serdes` produit des octets au **Confluent wire format** — le même cadrage utilisé par les serializers de `confluent-kafka`. Cette page explique la signification de chaque octet et les raisons de ce choix.

## Structure des octets

Chaque message sérialisé comporte trois parties :

```text
┌────────┬──────────────────────────┬────────────────────────┐
│ Byte 0 │       Bytes 1–4          │       Bytes 5+         │
│  0x00  │  Schema ID (big-endian)  │  Avro binary payload   │
│ magic  │     4-byte uint32        │  (schemaless encoding) │
└────────┴──────────────────────────┴────────────────────────┘
```

### Magic Byte (`0x00`)

Le premier octet est toujours `0x00`. Il signale aux consommateurs que ce message utilise le Confluent wire format (par opposition à de l'Avro brut ou à une autre convention de cadrage). Les consommateurs vérifient cet octet avant de tenter de décoder le reste du message.

### Identifiant de schema (octets 1–4)

Un entier non signé de 4 octets en big-endian qui identifie le schema utilisé pour encoder le payload Avro. Les consommateurs utilisent cet identifiant pour récupérer le schema correct depuis le registry avant le décodage.

L'identifiant peut être de deux types, selon la configuration :

| Identifiant | Ce qu'il représente | Quand l'utiliser |
|-------------|---------------------|------------------|
| **globalId** | Un identifiant unique, auto-incrémenté, attribué à chaque version d'artifact lors de sa création. Unique à l'échelle de l'ensemble du registry. | Par défaut. Utilisez-le sauf si vous avez une raison spécifique de ne pas le faire. |
| **contentId** | Un identifiant adressé par contenu, dérivé des octets du schema. Deux schemas identiques partagent toujours le même `contentId`, même s'ils sont enregistrés comme des artifacts différents. | À utiliser lorsque les consommateurs résolvent les schemas par empreinte de contenu plutôt que par historique de version. |

Pour configurer quel identifiant `AvroSerializer` intègre dans l'en-tête, consultez [Choisir entre globalId et contentId](../how-to/identifier-selection.md).

### Payload binaire Avro (octets 5+)

Les octets restants constituent l'encodage binaire Avro des données, écrit en utilisant l'**encodage sans schema** (`schemaless_writer` de fastavro). Le schema n'est pas intégré dans le payload — il est résolu depuis le registry en utilisant l'identifiant de schema des octets 1–4.

## Pourquoi ce format existe

Le Confluent wire format résout un problème fondamental du streaming d'événements : **les producteurs et les consommateurs doivent s'accorder sur le schema, mais on ne veut pas envoyer le schema avec chaque message.**

En intégrant un identifiant de schema compact dans l'en-tête du message, le consommateur peut :

1. Lire l'identifiant de 4 octets dans l'en-tête
2. Récupérer le schema depuis le registry (généralement mis en cache après la première récupération)
3. Décoder le payload Avro en utilisant ce schema

Cela permet de garder les messages compacts tout en préservant une connaissance complète du schema.

## Compatibilité

Les messages produits par `apicurio-serdes` sont compatibles octet par octet avec les messages produits par l'`AvroSerializer` de `confluent-kafka`. Tout consommateur qui comprend le Confluent wire format peut les décoder, à condition de pouvoir résoudre l'identifiant de schema depuis le même registry.

La seule exigence est que producteur et consommateur s'accordent sur le type d'identifiant présent dans l'en-tête (`globalId` vs `contentId`). Si le producteur intègre un `contentId` mais que le consommateur attend un `globalId`, la recherche retournera le mauvais schema ou échouera.
