# Sérialisation personnalisée avec `to_dict`

Par défaut, `AvroSerializer` attend un simple `dict` Python en entrée. Si votre application utilise des dataclasses, des modèles Pydantic ou d'autres objets métier, passez un callable `to_dict` pour les convertir avant l'encodage Avro.

## Signature de `to_dict`

```python
def to_dict(data: Any, ctx: SerializationContext) -> dict[str, Any]:
    ...
```

Le callable reçoit deux arguments :

- **`data`** — l'objet que vous avez passé au serializer
- **`ctx`** — le `SerializationContext` avec les métadonnées `topic` et `field`

Il doit retourner un simple `dict` dont les clés et valeurs correspondent au schema Avro.

## Avec des dataclasses

```python
from dataclasses import dataclass, asdict

@dataclass
class UserEvent:
    userId: str
    country: str

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    to_dict=lambda obj, ctx: asdict(obj),
)

event = UserEvent(userId="abc-123", country="FR")
payload = serializer(event, ctx)
```

## Avec des modèles Pydantic

```python
from pydantic import BaseModel

class UserEvent(BaseModel):
    userId: str
    country: str

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    to_dict=lambda obj, ctx: obj.model_dump(),
)

event = UserEvent(userId="abc-123", country="FR")
payload = serializer(event, ctx)
```

## Hooks sensibles au contexte

Le paramètre `ctx` contient le nom du topic et le type de champ (`KEY` ou `VALUE`). Utilisez-le lorsqu'un même hook doit se comporter différemment selon le contexte :

```python
from apicurio_serdes.serialization import MessageField

def to_dict(obj, ctx):
    d = obj.model_dump()
    if ctx.field == MessageField.KEY:
        # For message keys, only include the identifier
        return {"userId": d["userId"]}
    return d

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    to_dict=to_dict,
)
```

## Quand l'utiliser

Utilisez `to_dict` lorsque :

- Vos données ne sont pas déjà un `dict` (dataclasses, modèles Pydantic, classes attrs)
- Vous devez transformer ou filtrer des champs avant la sérialisation
- Vous avez besoin d'une logique de sérialisation différente pour les clés et les valeurs

Ne définissez pas `to_dict` si vos données sont déjà un simple `dict` conforme au schema.

## Gestion des erreurs

Si le callable `to_dict` lève une exception, `AvroSerializer` l'encapsule dans une `SerializationError` en conservant l'exception d'origine via `__cause__` :

```python
from apicurio_serdes._errors import SerializationError

try:
    payload = serializer(bad_data, ctx)
except SerializationError as e:
    print(f"to_dict failed: {e.cause}")
    # e.__cause__ is the original exception
```

Cela permet de distinguer les erreurs du hook des erreurs de validation du schema Avro (qui lèvent une `ValueError`).
