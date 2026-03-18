"""Unit tests for AvroDeserializer [T012, T019, FR-001 through FR-012]."""

from __future__ import annotations

import struct
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
import respx

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes._errors import DeserializationError, RegistryConnectionError
from apicurio_serdes.avro import AvroDeserializer
from apicurio_serdes.serialization import MessageField, SerializationContext
from tests.conftest import (
    GROUP_ID,
    REGISTRY_URL,
    VALID_USER_EVENT,
    _id_not_found_route,
    _id_schema_route,
    make_confluent_bytes,
)

CONTENT_ID = 42


def _make_client(mock_registry: respx.MockRouter) -> ApicurioRegistryClient:
    _id_schema_route(mock_registry, "globalId", CONTENT_ID)
    return ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


def _ctx() -> SerializationContext:
    return SerializationContext(topic="test", field=MessageField.VALUE)


# ── FR-001, FR-002: __init__ and __call__ ──


def test_init_stores_client(mock_registry: respx.MockRouter) -> None:
    """AvroDeserializer stores registry_client [FR-001]."""
    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client)
    assert deser.registry_client is client


def test_init_default_use_id(mock_registry: respx.MockRouter) -> None:
    """Default use_id is 'globalId'."""
    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client)
    assert deser.use_id == "globalId"


def test_default_use_id_matches_serializer(mock_registry: respx.MockRouter) -> None:
    """Default deserializer resolves via globalId endpoint, matching serializer default."""
    global_route = _id_schema_route(mock_registry, "globalId", CONTENT_ID)
    content_route = _id_schema_route(mock_registry, "contentId", CONTENT_ID)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    deser = AvroDeserializer(registry_client=client)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    deser(data, _ctx())
    assert global_route.called
    assert not content_route.called


def test_init_explicit_use_id_global(mock_registry: respx.MockRouter) -> None:
    """use_id can be set to 'globalId' [FR-006]."""
    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client, use_id="globalId")
    assert deser.use_id == "globalId"


def test_call_valid_decode(mock_registry: respx.MockRouter) -> None:
    """Valid Confluent-framed bytes decode to original dict [FR-001, FR-002]."""
    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    result = deser(data, _ctx())
    assert result == VALID_USER_EVENT


# ── FR-003: bad magic byte ──


def test_call_bad_magic_byte(mock_registry: respx.MockRouter) -> None:
    """Non-0x00 magic byte raises DeserializationError immediately [FR-003]."""
    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client)
    bad_bytes = b"\x01" + struct.pack(">I", CONTENT_ID) + b"\x00\x00"
    with pytest.raises(DeserializationError, match="magic"):
        deser(bad_bytes, _ctx())


# ── FR-004: too short ──


def test_call_empty_input(mock_registry: respx.MockRouter) -> None:
    """Empty input raises DeserializationError [FR-004]."""
    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client)
    with pytest.raises(DeserializationError):
        deser(b"", _ctx())


def test_call_input_too_short(mock_registry: respx.MockRouter) -> None:
    """Input shorter than 5 bytes raises DeserializationError [FR-004]."""
    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client)
    with pytest.raises(DeserializationError):
        deser(b"\x00\x00\x00\x01", _ctx())


# ── FR-005: schema lookup (unknown ID) ──


def test_call_unknown_schema_id(mock_registry: respx.MockRouter) -> None:
    """Unknown schema ID raises SchemaNotFoundError [FR-005, FR-010]."""
    from apicurio_serdes._errors import SchemaNotFoundError

    _id_not_found_route(mock_registry, "globalId", 9999)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    deser = AvroDeserializer(registry_client=client)
    bad_bytes = make_confluent_bytes(9999, VALID_USER_EVENT)
    with pytest.raises(SchemaNotFoundError):
        deser(bad_bytes, _ctx())


# ── FR-011: corrupt payload ──


def test_call_corrupt_payload(mock_registry: respx.MockRouter) -> None:
    """Corrupt Avro payload raises DeserializationError [FR-011]."""
    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client)
    corrupt = b"\x00" + struct.pack(">I", CONTENT_ID) + b"\xff\xff\xff"
    with pytest.raises(DeserializationError, match="decode"):
        deser(corrupt, _ctx())


# ── FR-012: network error ──


def test_call_network_error(mock_registry: respx.MockRouter) -> None:
    """Network failure during schema lookup raises RegistryConnectionError [FR-012]."""
    import httpx

    mock_registry.get(url__startswith=f"{REGISTRY_URL}/ids/").mock(
        side_effect=httpx.ConnectError("refused")
    )
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    deser = AvroDeserializer(registry_client=client)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    with pytest.raises(RegistryConnectionError):
        deser(data, _ctx())


# ── T019: Thread safety ──


def test_concurrent_deserialization_single_http_call(
    mock_registry: respx.MockRouter,
) -> None:
    """Concurrent deserialization with same schema ID triggers exactly 1 HTTP call [TS-012, NFR-001]."""
    route = _id_schema_route(mock_registry, "globalId", CONTENT_ID)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    deser = AvroDeserializer(registry_client=client)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    ctx = SerializationContext(topic="concurrent", field=MessageField.VALUE)

    def _call(_: int) -> dict[str, Any]:
        return deser(data, ctx)  # type: ignore[return-value]

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(_call, range(20)))

    assert all(r == VALID_USER_EVENT for r in results)
    assert route.call_count == 1


# ── T021: from_dict hook unit tests ──


def test_from_dict_applied(mock_registry: respx.MockRouter) -> None:
    """from_dict callable is applied to decoded dict [FR-008]."""
    from dataclasses import dataclass

    @dataclass
    class UserEvent:
        userId: str
        country: str

    def from_dict(d: dict[str, Any], ctx: SerializationContext) -> UserEvent:
        return UserEvent(**d)

    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client, from_dict=from_dict)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    result = deser(data, _ctx())
    assert isinstance(result, UserEvent)
    assert result.userId == "abc-123"
    assert result.country == "FR"


def test_from_dict_absent_returns_dict(mock_registry: respx.MockRouter) -> None:
    """Absent from_dict returns plain dict [FR-008]."""
    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    result = deser(data, _ctx())
    assert isinstance(result, dict)
    assert result == VALID_USER_EVENT


def test_from_dict_error_wrapped(mock_registry: respx.MockRouter) -> None:
    """from_dict exception wrapped as DeserializationError with cause [FR-009]."""

    def bad_hook(d: dict[str, Any], ctx: SerializationContext) -> Any:
        raise RuntimeError("hook failed")

    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client, from_dict=bad_hook)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    with pytest.raises(DeserializationError, match="from_dict") as exc_info:
        deser(data, _ctx())
    assert isinstance(exc_info.value.__cause__, RuntimeError)


# ── Reader schema (schema evolution) ──

# Writer schema: single field
_WRITER_SCHEMA: dict[str, Any] = {
    "type": "record",
    "name": "UserEvent",
    "namespace": "com.example",
    "fields": [
        {"name": "userId", "type": "string"},
    ],
}

# Reader schema: adds an evolved field with a default
_READER_SCHEMA: dict[str, Any] = {
    "type": "record",
    "name": "UserEvent",
    "namespace": "com.example",
    "fields": [
        {"name": "userId", "type": "string"},
        {"name": "version", "type": "string", "default": "v1"},
    ],
}


class TestReaderSchema:
    """Reader schema support — Avro schema evolution."""

    def test_no_reader_schema_returns_writer_fields_only(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """Default (reader_schema=None) decodes using writer schema — no evolution."""
        _id_schema_route(mock_registry, "globalId", CONTENT_ID, schema=_WRITER_SCHEMA)
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        deser = AvroDeserializer(registry_client=client)
        data = make_confluent_bytes(CONTENT_ID, {"userId": "u1"}, schema=_WRITER_SCHEMA)
        result = deser(data, _ctx())
        assert result == {"userId": "u1"}
        assert "version" not in result

    def test_reader_schema_fills_default_for_added_field(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """reader_schema causes fastavro to fill added field with its default."""
        _id_schema_route(mock_registry, "globalId", CONTENT_ID, schema=_WRITER_SCHEMA)
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        deser = AvroDeserializer(registry_client=client, reader_schema=_READER_SCHEMA)
        data = make_confluent_bytes(CONTENT_ID, {"userId": "u1"}, schema=_WRITER_SCHEMA)
        result = deser(data, _ctx())
        assert result == {"userId": "u1", "version": "v1"}

    def test_incompatible_reader_schema_raises_deserialization_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """Incompatible reader/writer schemas wrap fastavro error as DeserializationError."""
        _incompatible_reader: dict[str, Any] = {
            "type": "record",
            "name": "UserEvent",
            "namespace": "com.example",
            "fields": [
                {"name": "userId", "type": "string"},
                # required field with no default — cannot be filled from writer schema
                {"name": "required_field", "type": "string"},
            ],
        }
        _id_schema_route(mock_registry, "globalId", CONTENT_ID, schema=_WRITER_SCHEMA)
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        deser = AvroDeserializer(
            registry_client=client, reader_schema=_incompatible_reader
        )
        data = make_confluent_bytes(CONTENT_ID, {"userId": "u1"}, schema=_WRITER_SCHEMA)
        with pytest.raises(DeserializationError, match="Avro decode failure"):
            deser(data, _ctx())
