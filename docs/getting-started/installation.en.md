# Installation

## Requirements

- Python 3.10 or newer
- Apicurio Registry 3.x

## Install from PyPI

```bash
pip install apicurio-serdes
```

## Verify the installation

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

print("apicurio-serdes is ready.")
```

## Using with confluent-kafka

`apicurio-serdes` is Kafka-client-agnostic. Here is a minimal producer example with `confluent-kafka`:

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

## Local Apicurio Registry for development

For local development you can run Apicurio Registry with Docker:

```bash
docker run -it -p 8080:8080 quay.io/apicurio/apicurio-registry:latest
```

The v3 API will be available at `http://localhost:8080/apis/registry/v3`.
