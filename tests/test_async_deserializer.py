"""Tests for AsyncAvroDeserializer."""

from __future__ import annotations

import struct
from typing import Any

import pytest
import respx

from apicurio_serdes._async_client import AsyncApicurioRegistryClient
from apicurio_serdes._errors import DeserializationError, RegistryConnectionError
from apicurio_serdes.avro import AsyncAvroDeserializer
from apicurio_serdes.serialization import MessageField, SerializationContext
from tests.conftest import (
    GROUP_ID,
    INCOMPATIBLE_READER_SCHEMA,
    READER_SCHEMA_EVOLUTION,
    REGISTRY_URL,
    VALID_USER_EVENT,
    WRITER_SCHEMA_EVOLUTION,
    _id_schema_route,
    _schema_route,
    make_confluent_bytes,
)

CONTENT_ID = 42


def _make_async_client(mock_registry: respx.MockRouter) -> AsyncApicurioRegistryClient:
    url = f"{REGISTRY_URL}/ids/globalIds/{CONTENT_ID}"
    import json

    import httpx

    from tests.conftest import USER_EVENT_SCHEMA_JSON

    mock_registry.get(url).mock(
        return_value=httpx.Response(200, content=json.dumps(USER_EVENT_SCHEMA_JSON))
    )
    return AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


def _ctx() -> SerializationContext:
    return SerializationContext(topic="test", field=MessageField.VALUE)


# ── init ──


async def test_init_stores_client(mock_registry: respx.MockRouter) -> None:
    """AsyncAvroDeserializer stores registry_client."""
    client = _make_async_client(mock_registry)
    deser = AsyncAvroDeserializer(registry_client=client)
    assert deser.registry_client is client


async def test_init_default_use_id(mock_registry: respx.MockRouter) -> None:
    """Default use_id is 'globalId'."""
    client = _make_async_client(mock_registry)
    deser = AsyncAvroDeserializer(registry_client=client)
    assert deser.use_id == "globalId"


async def test_init_explicit_use_id_global(mock_registry: respx.MockRouter) -> None:
    """use_id can be set to 'globalId'."""
    client = _make_async_client(mock_registry)
    deser = AsyncAvroDeserializer(registry_client=client, use_id="globalId")
    assert deser.use_id == "globalId"


# ── successful decode ──


async def test_call_valid_decode(mock_registry: respx.MockRouter) -> None:
    """Valid Confluent-framed bytes decode to original dict."""
    client = _make_async_client(mock_registry)
    deser = AsyncAvroDeserializer(registry_client=client)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    result = await deser(data, _ctx())
    assert result == VALID_USER_EVENT


# ── magic byte validation ──


async def test_call_bad_magic_byte(mock_registry: respx.MockRouter) -> None:
    """Non-0x00 magic byte raises DeserializationError immediately."""
    client = _make_async_client(mock_registry)
    deser = AsyncAvroDeserializer(registry_client=client)
    bad_bytes = b"\x01" + struct.pack(">I", CONTENT_ID) + b"\x00\x00"
    with pytest.raises(DeserializationError, match="magic"):
        await deser(bad_bytes, _ctx())


# ── length validation ──


async def test_call_empty_input(mock_registry: respx.MockRouter) -> None:
    """Empty input raises DeserializationError."""
    client = _make_async_client(mock_registry)
    deser = AsyncAvroDeserializer(registry_client=client)
    with pytest.raises(DeserializationError):
        await deser(b"", _ctx())


async def test_call_input_too_short(mock_registry: respx.MockRouter) -> None:
    """Input shorter than 5 bytes raises DeserializationError."""
    client = _make_async_client(mock_registry)
    deser = AsyncAvroDeserializer(registry_client=client)
    with pytest.raises(DeserializationError):
        await deser(b"\x00\x00\x00\x01", _ctx())


# ── schema not found ──


async def test_call_unknown_schema_id(mock_registry: respx.MockRouter) -> None:
    """Unknown schema ID raises SchemaNotFoundError."""
    import httpx

    from apicurio_serdes._errors import SchemaNotFoundError

    mock_registry.get(f"{REGISTRY_URL}/ids/globalIds/9999").mock(
        return_value=httpx.Response(404)
    )
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    deser = AsyncAvroDeserializer(registry_client=client)
    bad_bytes = make_confluent_bytes(9999, VALID_USER_EVENT)
    with pytest.raises(SchemaNotFoundError):
        await deser(bad_bytes, _ctx())


# ── corrupt payload ──


async def test_call_corrupt_payload(mock_registry: respx.MockRouter) -> None:
    """Corrupt Avro payload raises DeserializationError."""
    client = _make_async_client(mock_registry)
    deser = AsyncAvroDeserializer(registry_client=client)
    corrupt = b"\x00" + struct.pack(">I", CONTENT_ID) + b"\xff\xff\xff"
    with pytest.raises(DeserializationError, match="decode"):
        await deser(corrupt, _ctx())


# ── network error ──


async def test_call_network_error(mock_registry: respx.MockRouter) -> None:
    """Network failure during schema lookup raises RegistryConnectionError."""
    import httpx

    mock_registry.get(url__startswith=f"{REGISTRY_URL}/ids/").mock(
        side_effect=httpx.ConnectError("refused")
    )
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    deser = AsyncAvroDeserializer(registry_client=client)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    with pytest.raises(RegistryConnectionError):
        await deser(data, _ctx())


# ── from_dict hook ──


async def test_from_dict_applied(mock_registry: respx.MockRouter) -> None:
    """from_dict callable is applied to decoded dict."""
    from dataclasses import dataclass

    @dataclass
    class UserEvent:
        userId: str
        country: str

    def from_dict(d: dict[str, Any], ctx: SerializationContext) -> UserEvent:
        return UserEvent(**d)

    client = _make_async_client(mock_registry)
    deser = AsyncAvroDeserializer(registry_client=client, from_dict=from_dict)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    result = await deser(data, _ctx())
    assert isinstance(result, UserEvent)
    assert result.userId == "abc-123"
    assert result.country == "FR"


async def test_from_dict_absent_returns_dict(mock_registry: respx.MockRouter) -> None:
    """Absent from_dict returns plain dict."""
    client = _make_async_client(mock_registry)
    deser = AsyncAvroDeserializer(registry_client=client)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    result = await deser(data, _ctx())
    assert isinstance(result, dict)
    assert result == VALID_USER_EVENT


async def test_from_dict_error_wrapped(mock_registry: respx.MockRouter) -> None:
    """from_dict exception wrapped as DeserializationError with cause."""

    def bad_hook(d: dict[str, Any], ctx: SerializationContext) -> Any:
        raise RuntimeError("hook failed")

    client = _make_async_client(mock_registry)
    deser = AsyncAvroDeserializer(registry_client=client, from_dict=bad_hook)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    with pytest.raises(DeserializationError, match="from_dict") as exc_info:
        await deser(data, _ctx())
    assert isinstance(exc_info.value.__cause__, RuntimeError)


# ── schema caching ──


async def test_schema_cached_after_first_call(
    mock_registry: respx.MockRouter,
) -> None:
    """Schema is fetched once and cached for subsequent calls."""
    import json

    import httpx

    from tests.conftest import USER_EVENT_SCHEMA_JSON

    url = f"{REGISTRY_URL}/ids/globalIds/{CONTENT_ID}"
    route = mock_registry.get(url).mock(
        return_value=httpx.Response(200, content=json.dumps(USER_EVENT_SCHEMA_JSON))
    )
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    deser = AsyncAvroDeserializer(registry_client=client)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)

    await deser(data, _ctx())
    await deser(data, _ctx())

    assert route.call_count == 1


# ── globalId mode ──


async def test_call_with_content_id_mode(mock_registry: respx.MockRouter) -> None:
    """Deserializer with use_id='contentId' resolves via contentId endpoint."""
    import json

    import httpx

    from tests.conftest import USER_EVENT_SCHEMA_JSON

    content_id = 7
    mock_registry.get(f"{REGISTRY_URL}/ids/contentIds/{content_id}").mock(
        return_value=httpx.Response(200, content=json.dumps(USER_EVENT_SCHEMA_JSON))
    )
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    deser = AsyncAvroDeserializer(registry_client=client, use_id="contentId")
    data = make_confluent_bytes(content_id, VALID_USER_EVENT)
    result = await deser(data, _ctx())
    assert result == VALID_USER_EVENT


async def test_call_with_global_id_mode(mock_registry: respx.MockRouter) -> None:
    """Deserializer with use_id='globalId' resolves via globalId endpoint."""
    import json

    import httpx

    from tests.conftest import USER_EVENT_SCHEMA_JSON

    global_id = 7
    mock_registry.get(f"{REGISTRY_URL}/ids/globalIds/{global_id}").mock(
        return_value=httpx.Response(200, content=json.dumps(USER_EVENT_SCHEMA_JSON))
    )
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    deser = AsyncAvroDeserializer(registry_client=client, use_id="globalId")
    data = make_confluent_bytes(global_id, VALID_USER_EVENT)
    result = await deser(data, _ctx())
    assert result == VALID_USER_EVENT


# ── package export ──


def test_async_avro_deserializer_importable_from_avro_package() -> None:
    """AsyncAvroDeserializer is importable from apicurio_serdes.avro."""
    from apicurio_serdes.avro import AsyncAvroDeserializer as Imported

    assert Imported is AsyncAvroDeserializer


# ── signature parity ──


def test_async_deserializer_init_signature_matches_sync() -> None:
    """AsyncAvroDeserializer.__init__ has the same parameter names as AvroDeserializer."""
    import inspect

    from apicurio_serdes.avro import AvroDeserializer

    sync_params = set(inspect.signature(AvroDeserializer.__init__).parameters) - {
        "self"
    }
    async_params = set(inspect.signature(AsyncAvroDeserializer.__init__).parameters) - {
        "self"
    }
    assert sync_params == async_params


# ── Reader schema (schema evolution) ──


class TestReaderSchema:
    """Reader schema support — Avro schema evolution (async)."""

    async def test_no_reader_schema_returns_writer_fields_only(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """Default (reader_schema=None) decodes using writer schema — no evolution."""
        _id_schema_route(
            mock_registry, "globalId", CONTENT_ID, schema=WRITER_SCHEMA_EVOLUTION
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        deser = AsyncAvroDeserializer(registry_client=client)
        data = make_confluent_bytes(
            CONTENT_ID, {"userId": "u1"}, schema=WRITER_SCHEMA_EVOLUTION
        )
        result = await deser(data, _ctx())
        assert result == {"userId": "u1"}
        assert "version" not in result

    async def test_reader_schema_fills_default_for_added_field(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """reader_schema causes fastavro to fill added field with its default."""
        _id_schema_route(
            mock_registry, "globalId", CONTENT_ID, schema=WRITER_SCHEMA_EVOLUTION
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        deser = AsyncAvroDeserializer(
            registry_client=client, reader_schema=READER_SCHEMA_EVOLUTION
        )
        data = make_confluent_bytes(
            CONTENT_ID, {"userId": "u1"}, schema=WRITER_SCHEMA_EVOLUTION
        )
        result = await deser(data, _ctx())
        assert result == {"userId": "u1", "version": "v1"}

    async def test_incompatible_reader_schema_raises_deserialization_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """Incompatible reader/writer schemas wrap fastavro error as DeserializationError."""
        _id_schema_route(
            mock_registry, "globalId", CONTENT_ID, schema=WRITER_SCHEMA_EVOLUTION
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        deser = AsyncAvroDeserializer(
            registry_client=client, reader_schema=INCOMPATIBLE_READER_SCHEMA
        )
        data = make_confluent_bytes(
            CONTENT_ID, {"userId": "u1"}, schema=WRITER_SCHEMA_EVOLUTION
        )
        with pytest.raises(DeserializationError, match="Avro decode failure"):
            await deser(data, _ctx())


class TestUseLatestVersion:
    """AsyncAvroDeserializer use_latest_version feature."""

    def test_use_latest_version_without_artifact_raises(self) -> None:
        """use_latest_version=True without artifact_id or artifact_resolver raises ValueError."""
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(ValueError, match="artifact_id or artifact_resolver"):
            AsyncAvroDeserializer(registry_client=client, use_latest_version=True)

    def test_use_latest_version_with_reader_schema_raises(self) -> None:
        """use_latest_version=True + reader_schema raises ValueError (mutually exclusive)."""
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(ValueError, match="mutually exclusive"):
            AsyncAvroDeserializer(
                registry_client=client,
                artifact_id="UserEvent",
                use_latest_version=True,
                reader_schema=READER_SCHEMA_EVOLUTION,
            )

    def test_artifact_id_and_resolver_raises(self) -> None:
        """artifact_id + artifact_resolver raises ValueError (mutually exclusive)."""
        from apicurio_serdes.avro import SimpleTopicIdStrategy

        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(ValueError, match="mutually exclusive"):
            AsyncAvroDeserializer(
                registry_client=client,
                artifact_id="UserEvent",
                artifact_resolver=SimpleTopicIdStrategy(),
                use_latest_version=True,
            )

    def test_artifact_id_without_use_latest_version_raises(self) -> None:
        """artifact_id without use_latest_version=True raises ValueError."""
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(ValueError, match="use_latest_version"):
            AsyncAvroDeserializer(registry_client=client, artifact_id="UserEvent")

    async def test_use_latest_version_with_artifact_id_fills_default(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """use_latest_version=True + artifact_id uses latest schema as reader schema."""
        _schema_route(mock_registry, "UserEvent", schema=READER_SCHEMA_EVOLUTION)
        _id_schema_route(
            mock_registry, "globalId", CONTENT_ID, schema=WRITER_SCHEMA_EVOLUTION
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        deser = AsyncAvroDeserializer(
            registry_client=client,
            artifact_id="UserEvent",
            use_latest_version=True,
        )
        data = make_confluent_bytes(
            CONTENT_ID, {"userId": "u1"}, schema=WRITER_SCHEMA_EVOLUTION
        )
        result = await deser(data, _ctx())
        assert result == {"userId": "u1", "version": "v1"}

    async def test_use_latest_version_with_artifact_resolver_fills_default(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """use_latest_version=True + artifact_resolver uses latest schema as reader schema."""
        from apicurio_serdes.avro import SimpleTopicIdStrategy

        _schema_route(mock_registry, "test", schema=READER_SCHEMA_EVOLUTION)
        _id_schema_route(
            mock_registry, "globalId", CONTENT_ID, schema=WRITER_SCHEMA_EVOLUTION
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        deser = AsyncAvroDeserializer(
            registry_client=client,
            artifact_resolver=SimpleTopicIdStrategy(),
            use_latest_version=True,
        )
        data = make_confluent_bytes(
            CONTENT_ID, {"userId": "u1"}, schema=WRITER_SCHEMA_EVOLUTION
        )
        result = await deser(data, _ctx())
        assert result == {"userId": "u1", "version": "v1"}

    async def test_use_latest_version_reader_schema_cached(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """use_latest_version=True: second call does not re-fetch the latest schema."""
        schema_route = _schema_route(
            mock_registry, "UserEvent", schema=READER_SCHEMA_EVOLUTION
        )
        _id_schema_route(
            mock_registry, "globalId", CONTENT_ID, schema=WRITER_SCHEMA_EVOLUTION
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        deser = AsyncAvroDeserializer(
            registry_client=client,
            artifact_id="UserEvent",
            use_latest_version=True,
        )
        data = make_confluent_bytes(
            CONTENT_ID, {"userId": "u1"}, schema=WRITER_SCHEMA_EVOLUTION
        )
        await deser(data, _ctx())
        await deser(data, _ctx())
        assert schema_route.call_count == 1

    async def test_use_latest_version_false_is_backward_compatible(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """use_latest_version=False (default) with no artifact params works as before."""
        _id_schema_route(mock_registry, "globalId", CONTENT_ID)
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        deser = AsyncAvroDeserializer(registry_client=client)
        data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
        result = await deser(data, _ctx())
        assert result == VALID_USER_EVENT
