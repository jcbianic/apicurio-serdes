"""Unit tests for AvroDeserializer [T012, FR-001 through FR-012]."""

from __future__ import annotations

import struct
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
    _id_schema_route(mock_registry, "contentId", CONTENT_ID)
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
    """Default use_id is 'contentId' [FR-006]."""
    client = _make_client(mock_registry)
    deser = AvroDeserializer(registry_client=client)
    assert deser.use_id == "contentId"


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

    _id_not_found_route(mock_registry, "contentId", 9999)
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

    mock_registry.get(
        url__startswith=f"{REGISTRY_URL}/ids/"
    ).mock(side_effect=httpx.ConnectError("refused"))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    deser = AvroDeserializer(registry_client=client)
    data = make_confluent_bytes(CONTENT_ID, VALID_USER_EVENT)
    with pytest.raises(RegistryConnectionError):
        deser(data, _ctx())
