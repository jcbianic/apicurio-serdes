# Gestion des erreurs

`apicurio-serdes` lève des types d'exceptions spécifiques pour chaque mode de défaillance,
ainsi que des exceptions Python standard pour les erreurs de validation.

## Vue d'ensemble des exceptions

| Exception | Quand elle est levée | Attributs clés |
|-----------|---------------------|----------------|
| `SchemaNotFoundError` | L'artefact ou l'identifiant de schema n'existe pas dans le registry (HTTP 404) | `group_id`, `artifact_id` ou `id_type`, `id_value` |
| `RegistryConnectionError` | Le registry est injoignable (erreur réseau) | `url` |
| `SerializationError` | Le callable `to_dict` a levé une exception | `cause` |
| `DeserializationError` | Wire format invalide, échec de décodage Avro, ou échec du hook `from_dict` | `cause` |
| `RuntimeError` | Le client registry a été fermé | — |
| `ValueError` | L'identifiant de schema dépasse la limite 32 bits (CONFLUENT_PAYLOAD), ou les identifiants de la réponse registry sont hors de la plage int64 | — |

Toutes les exceptions personnalisées sont importables depuis `apicurio_serdes._errors`.

## Gérer `SchemaNotFoundError`

Levée lorsque l'`artifact_id` n'existe pas dans le groupe spécifié.

```python
from apicurio_serdes._errors import SchemaNotFoundError

try:
    payload = serializer(data, ctx)
except SchemaNotFoundError as e:
    print(f"Schema not found: group={e.group_id}, artifact={e.artifact_id}")
```

**Causes fréquentes :**

- L'identifiant de l'artefact est mal orthographié ou a une casse incorrecte (`UserEvent` vs `userevent`)
- Le schema se trouve dans un groupe différent de celui configuré sur le client
- Le schema n'a pas encore été enregistré

**Récupération :** Vérifiez que l'artefact existe dans le registry :

```bash
curl "http://localhost:8080/apis/registry/v3/groups/com.example.schemas/artifacts"
```

## Gérer `RegistryConnectionError`

Levée lorsque le registry est injoignable — la requête HTTP a échoué avant d'obtenir une réponse.

```python
from apicurio_serdes._errors import RegistryConnectionError

try:
    payload = serializer(data, ctx)
except RegistryConnectionError as e:
    print(f"Registry unreachable at {e.url}")
    # e.__cause__ is the underlying httpx.ConnectError
```

**Causes fréquentes :**

- Le registry est arrêté ou pas encore démarré
- L'URL est incorrecte (chemin `/apis/registry/v3` manquant)
- Un pare-feu ou un problème réseau bloque la connexion

**Nouvelle tentative intégrée :** Les deux clients effectuent automatiquement des
nouvelles tentatives sur les défaillances transitoires — aucune boucle de nouvelle
tentative manuelle n'est nécessaire. Configurez ce comportement à la construction :

```python
from apicurio_serdes import ApicurioRegistryClient

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
    max_retries=3,               # défaut — mettre à 0 pour désactiver
    retry_backoff_ms=1000,       # délai de base pour la première tentative (ms)
    retry_max_backoff_ms=20000,  # délai maximum (ms)
)
```

Les nouvelles tentatives couvrent les `httpx.TransportError` (échec au niveau réseau)
et les réponses HTTP avec les codes 429, 502, 503 et 504 (erreurs serveur transitoires).
Une fois toutes les tentatives épuisées, `RegistryConnectionError` est levée.

**N'encapsulez pas** les appels dans une boucle de nouvelle tentative supplémentaire —
cela multiplierait le nombre effectif de tentatives et interférerait avec le délai
exponentiel intégré.

Remarque : cette exception n'est levée que lors du **premier** appel de sérialisation
(lorsque le schema est récupéré). Une fois le schema mis en cache, aucune requête HTTP
supplémentaire n'est effectuée, les erreurs réseau ne peuvent donc pas survenir pendant
la sérialisation.

## Gérer `SerializationError`

Levée lorsque le callable `to_dict` lève une exception pendant la conversion.

```python
from apicurio_serdes._errors import SerializationError

try:
    payload = serializer(data, ctx)
except SerializationError as e:
    print(f"to_dict conversion failed: {e.cause}")
    # e.cause is the original exception from your to_dict callable
    # e.__cause__ is also set for traceback chaining
```

**Causes fréquentes :**

- Le callable `to_dict` a reçu un type d'entrée inattendu
- Le callable a tenté d'accéder à un attribut inexistant sur l'objet en entrée
- Une erreur de validation Pydantic s'est produite dans `model_dump()`

**Récupération :** Corrigez l'implémentation de `to_dict` ou validez les données en
entrée avant la sérialisation.

## Gérer `ValueError`

Levée par l'encodeur Avro sous-jacent (fastavro) lorsque les données ne correspondent
pas au schema. Ce n'est **pas** une exception `apicurio-serdes` — elle provient
directement de fastavro.

```python
try:
    payload = serializer(data, ctx)
except ValueError as e:
    print(f"Data does not match schema: {e}")
```

Si `strict=True` est activé sur le serializer, `ValueError` est également levée lorsque
les données contiennent des champs supplémentaires non définis dans le schema.

**Récupération :** Assurez-vous que le dictionnaire de données possède tous les champs
requis avec les types corrects.

## Gérer `RuntimeError` (client fermé)

Levée lorsque vous appelez une méthode sur un client registry qui a déjà été fermé.

```python
try:
    payload = serializer(data, ctx)
except RuntimeError as e:
    if "closed" in str(e):
        print("Le client a été fermé — créez une nouvelle instance de client")
```

**Causes fréquentes :**

- Appeler `close()` ou sortir d'un gestionnaire de contexte, puis réutiliser le même
  client
- Partager un client entre threads/coroutines où un chemin le ferme prématurément

**Récupération :** Créez une nouvelle instance d'`ApicurioRegistryClient` ou
d'`AsyncApicurioRegistryClient`.

## Gérer `ValueError` (validation)

En plus des erreurs de validation de schema Avro provenant de fastavro, `ValueError` est
levée dans deux nouvelles situations :

- **Dépassement de l'identifiant de schema 32 bits** : avec le wire format
  `CONFLUENT_PAYLOAD`, l'identifiant de schema doit tenir dans un entier non signé de
  32 bits. Si l'identifiant attribué par le registry dépasse cette limite, utilisez
  `WireFormat.KAFKA_HEADERS` à la place.
- **Validation de la plage int64** : lorsque les en-têtes de réponse du registry
  contiennent un `globalId` ou `contentId` en dehors de la plage d'entiers signés de
  64 bits.

```python
try:
    payload = serializer(data, ctx)
except ValueError as e:
    if "32-bit" in str(e):
        print("L'identifiant de schema est trop grand pour CONFLUENT_PAYLOAD — passez à KAFKA_HEADERS")
    else:
        print(f"Les données ne correspondent pas au schema : {e}")
```

Si `strict=True` est activé sur le serializer, `ValueError` est également levée lorsque
les données contiennent des champs supplémentaires non définis dans le schema.

**Récupération :** Assurez-vous que le dictionnaire de données possède tous les champs
requis avec les types corrects, ou changez de wire format pour les grands identifiants
de schema.

## Tout assembler

```python
from apicurio_serdes._errors import (
    SchemaNotFoundError,
    RegistryConnectionError,
    SerializationError,
)

try:
    payload = serializer(data, ctx)
except SchemaNotFoundError as e:
    logger.error("Schema %s not found in group %s", e.artifact_id, e.group_id)
    raise
except RegistryConnectionError as e:
    logger.error("Registry unreachable at %s", e.url)
    raise
except SerializationError as e:
    logger.error("to_dict hook failed: %s", e.cause)
    raise
except RuntimeError as e:
    logger.error("Client is closed: %s", e)
    raise
except ValueError as e:
    logger.error("Validation failed: %s", e)
    raise
```
