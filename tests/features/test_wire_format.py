"""Step definitions for wire_format.feature (deserializer) [T011, TS-016, TS-017, TS-018]."""

from __future__ import annotations

import struct
from typing import Any

import respx
from pytest_bdd import given, parsers, scenario, then, when

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroDeserializer
from apicurio_serdes.serialization import MessageField, SerializationContext
from tests.conftest import (
    GROUP_ID,
    REGISTRY_URL,
    VALID_USER_EVENT,
    _id_schema_route,
    _schema_route,
    make_confluent_bytes,
)

FEATURE = "../../specs/002-avro-deserializer/tests/features/wire_format.feature"


# ── Scenarios ──


@scenario(
    FEATURE,
    "Default use_id is contentId — 4-byte field is interpreted as a contentId",
)
def test_ts016_default_content_id() -> None:
    """TS-016."""


@scenario(
    FEATURE,
    'use_id="globalId" causes the 4-byte field to be interpreted as a globalId',
)
def test_ts017_global_id_mode() -> None:
    """TS-017."""


@scenario(
    FEATURE,
    "AvroDeserializer callable interface mirrors the confluent-kafka deserializer convention",
)
def test_ts018_callable_interface() -> None:
    """TS-018."""


# ── Background steps ──


@given(
    parsers.cfparse(
        "a configured ApicurioRegistryClient pointing at a registry that returns"
        ' globalId {global_id:d} and contentId {content_id:d} for artifact "{artifact_id}"'
    ),
    target_fixture="registry_client",
)
def given_client_with_ids(
    mock_registry: respx.MockRouter, global_id: int, content_id: int, artifact_id: str
) -> ApicurioRegistryClient:
    _schema_route(
        mock_registry, artifact_id, global_id=global_id, content_id=content_id
    )
    _id_schema_route(mock_registry, "contentId", content_id)
    _id_schema_route(mock_registry, "globalId", global_id)
    return ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


@given(
    parsers.cfparse('a SerializationContext for topic "{topic}" and field {field}'),
    target_fixture="ctx",
)
def given_ctx_wf(topic: str, field: str) -> SerializationContext:
    return SerializationContext(topic=topic, field=MessageField[field])


# ── Given steps ──


@given(
    parsers.cfparse(
        'an AvroDeserializer configured with use_id="{use_id}" and the client'
    ),
    target_fixture="deserializer",
)
def given_deserializer_with_use_id(
    registry_client: ApicurioRegistryClient, use_id: str
) -> AvroDeserializer:
    return AvroDeserializer(
        registry_client=registry_client,
        use_id=use_id,  # type: ignore[arg-type]
    )


@given(
    parsers.cfparse(
        "bytes whose magic byte is 0x00 and whose 4-byte field encodes"
        " the value {schema_id:d} as big-endian uint32"
    ),
    target_fixture="input_bytes",
)
def given_bytes_with_id(schema_id: int) -> bytes:
    return b"\x00" + struct.pack(">I", schema_id)


@given(
    "a valid Avro payload appended after the 5-byte header",
    target_fixture="input_bytes",
)
def given_with_avro_payload(input_bytes: bytes) -> bytes:
    avro_bytes = make_confluent_bytes(0, VALID_USER_EVENT)[5:]
    return input_bytes + avro_bytes


@given(
    "an AvroDeserializer instance bound to the client",
    target_fixture="deserializer",
)
def given_deserializer_instance(
    registry_client: ApicurioRegistryClient,
) -> AvroDeserializer:
    return AvroDeserializer(registry_client=registry_client)


@given(
    parsers.cfparse('valid Confluent-framed Avro bytes for artifact "{artifact_id}"'),
    target_fixture="input_bytes",
)
def given_valid_framed_bytes_for_artifact(artifact_id: str) -> bytes:
    return make_confluent_bytes(42, VALID_USER_EVENT)


# ── When steps ──


@when(
    "the deserializer is called with those bytes and the context",
    target_fixture="deser_result",
)
def when_call_deserializer(
    deserializer: AvroDeserializer,
    input_bytes: bytes,
    ctx: SerializationContext,
) -> Any:
    return deserializer(input_bytes, ctx)


@when(
    "the deserializer is called as deserializer(data, ctx) with those bytes and the SerializationContext",
    target_fixture="deser_result",
)
def when_call_as_callable(
    deserializer: AvroDeserializer,
    input_bytes: bytes,
    ctx: SerializationContext,
) -> Any:
    return deserializer(input_bytes, ctx)


# ── Then steps ──


@then(parsers.cfparse("the registry is queried for contentId {content_id:d}"))
def then_registry_queried_content_id_wf(
    mock_registry: respx.MockRouter, content_id: int
) -> None:
    called = any(
        r.call_count > 0
        for r in mock_registry.routes
        if f"contentIds/{content_id}" in str(getattr(r, "pattern", ""))
    )
    assert called, f"Registry was not queried for contentId {content_id}"


@then(parsers.cfparse("the registry is queried for globalId {global_id:d}"))
def then_registry_queried_global_id_wf(
    mock_registry: respx.MockRouter, global_id: int
) -> None:
    called = any(
        r.call_count > 0
        for r in mock_registry.routes
        if f"globalIds/{global_id}" in str(getattr(r, "pattern", ""))
    )
    assert called, f"Registry was not queried for globalId {global_id}"


@then("the decoded result is a Python dict")
def then_decoded_is_dict(deser_result: Any) -> None:
    assert isinstance(deser_result, dict)


@then("the return value is a Python dict")
def then_return_is_dict(deser_result: Any) -> None:
    assert isinstance(deser_result, dict)
