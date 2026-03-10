# apicurio-serdes

**Bibliothèque de sérialisation Python pour Apicurio Registry, utilisant l'API native v3.**

## Le problème

Vous utilisez [Apicurio Registry](https://www.apicur.io/registry/) pour gérer vos schemas Avro. Vos producteurs Kafka sont écrits en Python. La recommandation habituelle consiste à configurer le `SchemaRegistryClient` de `confluent-kafka` pour qu'il pointe vers le endpoint de compatibilité d'Apicurio — mais en pratique, cela ne fonctionne pas :

- **Les groupes non par défaut sont invisibles.** `SchemaRegistryClient` ne peut pas envoyer l'en-tête `X-Registry-GroupId` qu'Apicurio exige pour les schemas stockés en dehors du groupe `default`.
- **Les références inter-artefacts échouent.** La couche de compatibilité ne résout pas les pointeurs `$ref` entre les artefacts Apicurio.

Si vos schemas se trouvent dans un groupe personnalisé — et dans tout déploiement Apicurio non trivial, c'est le cas — vous êtes bloqué.

## La solution

`apicurio-serdes` communique directement avec l'API v3 d'Apicurio, en contournant entièrement la couche de compatibilité. L'API est conçue pour correspondre aux conventions de `confluent-kafka` :

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

payload: bytes = serializer({"userId": "abc", "country": "FR"}, ctx)
```

C'est tout. `group_id` est un paramètre de premier ordre. Les références de schema se résolvent nativement contre le registry, et la sortie est compatible octet par octet avec tout consommateur au format Confluent.

## À qui s'adresse cette bibliothèque ?

Ingénieurs data et développeurs backend Python qui :

- Utilisent **Apicurio Registry 3.x** (autonome ou via Red Hat Service Registry)
- Produisent des messages Kafka sérialisés en **Avro**
- Ont besoin de schemas organisés dans des **groupes non par défaut**
- Veulent une **API familière** — si vous avez déjà utilisé les sérialiseurs de `confluent-kafka`, vous connaissez déjà cette bibliothèque

## Fonctionnalités clés

| Fonctionnalité | Description |
|----------------|-------------|
| **API native v3** | Appels directs à l'API REST d'Apicurio, sans contournement ccompat |
| **`group_id` comme citoyen de premier ordre** | Chaque recherche de schema passe par le bon groupe |
| **API compatible confluent-kafka** | Mêmes noms de classes et conventions d'appel que `confluent-kafka` |
| **Mise en cache des schemas** | Un seul appel HTTP par artefact, pas par message |
| **Choix du wire format** | `globalId` (par défaut) ou `contentId` dans l'en-tête Confluent |
| **hook `to_dict` personnalisés** | Sérialisez des dataclass, des modèles Pydantic ou tout autre objet |

## Démarrage rapide

Suivez le [Quickstart](getting-started/quickstart.md) pour sérialiser votre premier message en cinq minutes.

Vous utilisez déjà `confluent-kafka` ? Consultez le [Guide de migration](migration/from-confluent-kafka.md).

## Statut

| Composant | Statut |
|-----------|--------|
| `ApicurioRegistryClient` | Disponible |
| `AvroSerializer` | Disponible |
| `AvroDeserializer` | En cours |
| Client registry asynchrone | Planifié |
| Wire format via en-têtes Kafka | Planifié |
| Support Protobuf | Feuille de route |
| Support JSON Schema | Feuille de route |
