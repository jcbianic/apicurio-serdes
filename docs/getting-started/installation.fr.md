# Installation

## Prérequis

- Python 3.10 ou version ultérieure
- Apicurio Registry 3.x

## Installer depuis PyPI

```bash
pip install apicurio-serdes
```

## Vérifier l'installation

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

print("apicurio-serdes is ready.")
```

## Utilisation avec confluent-kafka

`apicurio-serdes` est indépendant du client Kafka. Voici un exemple minimal de producteur avec `confluent-kafka` :

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
ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)

producer.produce(
    "user-events",
    value=serializer({"userId": "abc", "country": "FR"}, ctx),
)
producer.flush()
```

## Apicurio Registry en local pour le développement

Pour le développement en local, vous pouvez lancer Apicurio Registry avec Docker :

```bash
docker run -it -p 8080:8080 quay.io/apicurio/apicurio-registry:latest
```

L'API v3 sera accessible à l'adresse `http://localhost:8080/apis/registry/v3`.
