# Choisir entre `globalId` et `contentId`

`AvroSerializer` intègre un identifiant de schema sur 4 octets dans chaque message sérialisé. Vous pouvez choisir quel identifiant utiliser grâce au paramètre `use_id`. Ce guide explique les compromis.

## Les deux identifiants

Chaque version de schema dans Apicurio Registry possède deux identifiants :

| Identifiant | Ce que c'est | Comment il est attribué |
|-------------|-------------|------------------------|
| **globalId** | Un entier unique, auto-incrémenté, attribué lors de la création d'une version d'artefact. | Séquentiel — `1`, `2`, `3`, ... à travers l'ensemble du registry. |
| **contentId** | Un entier dérivé du contenu, calculé à partir des octets du schema. | Déterministe — deux schemas identiques partagent toujours le même `contentId`. |

Les deux sont renvoyés par le registry dans les en-têtes de réponse HTTP (`X-Registry-GlobalId` et `X-Registry-ContentId`) et mis en cache par `ApicurioRegistryClient`.

## Comment choisir

```python
# Default: use globalId
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    use_id="globalId",
)

# Alternative: use contentId
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    use_id="contentId",
)
```

## Quand utiliser `globalId` (par défaut)

Utilisez `globalId` lorsque :

- Vous souhaitez le **comportement par défaut** — il correspond à la convention wire format Confluent la plus courante
- Vos consommateurs résolvent les schemas par historique de version (la plupart des configurations Apicurio et Confluent)
- Chaque version de schema doit avoir un identifiant **distinct**, même si le contenu du schema est identique à une version précédente

`globalId` est le choix par défaut recommandé. Choisissez-le sauf si vous avez une raison spécifique d'utiliser `contentId`.

## Quand utiliser `contentId`

Utilisez `contentId` lorsque :

- Vos consommateurs sont configurés pour résoudre les schemas par **hash de contenu** plutôt que par identifiant de version
- Vous voulez que des **schemas identiques** enregistrés dans des groupes différents ou en tant qu'artefacts différents partagent le même identifiant dans le wire format
- Vous utilisez les fonctionnalités de déduplication par contenu d'Apicurio

## Producteur et consommateur doivent s'accorder

Le type d'identifiant **n'est pas encodé dans le wire format**. `globalId` et `contentId` occupent tous deux les mêmes 4 octets dans l'en-tête du message. Le consommateur doit savoir quel type attendre.

Si le producteur intègre un `contentId` mais que le consommateur l'interprète comme un `globalId` (ou inversement), le consommateur récupérera le mauvais schema ou ne parviendra pas à en trouver un.

Assurez-vous que les configurations de votre producteur et de votre consommateur s'accordent sur le type d'identifiant utilisé.

## Comportement du registry

Lorsque `ApicurioRegistryClient` récupère un schema, le registry renvoie **les deux** identifiants dans les en-têtes de réponse. Le client met les deux en cache. Le paramètre `use_id` contrôle uniquement lequel est écrit dans l'en-tête du wire format par le serializer — il n'affecte ni ce que le registry renvoie, ni le fonctionnement de la mise en cache.
