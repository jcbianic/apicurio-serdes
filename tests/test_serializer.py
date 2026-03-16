"""Step definitions for TS-001 through TS-007, TS-013 through TS-015: AvroSerializer scenarios."""

from __future__ import annotations

import struct
from typing import Any

import httpx
import pytest
import respx
from pytest_bdd import given, parsers, scenario, then, when

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes._errors import (
    RegistryConnectionError,
    ResolverError,
    SchemaNotFoundError,
    SerializationError,
)
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import (
    MessageField,
    SerializationContext,
    SerializedMessage,
    WireFormat,
)
from tests.conftest import (
    GLOBAL_ID,
    GROUP_ID,
    INVALID_USER_EVENT_MISSING_FIELD,
    REGISTRY_URL,
    USER_EVENT_SCHEMA_JSON,
    VALID_USER_EVENT,
    VALID_USER_EVENT_ALT,
    VALID_USER_EVENT_EXTRA_FIELDS,
    _not_found_route,
    _register_error_route,
    _register_route,
    _schema_route,
)

FEATURE = "../specs/001-avro-serializer/tests/features/avro_serialization.feature"
TO_DICT_FEATURE = "../specs/001-avro-serializer/tests/features/to_dict_hook.feature"


# ── Scenarios ──


@scenario(FEATURE, "Serialize valid dict produces Confluent wire format bytes")
def test_ts001_serialize_valid_dict() -> None:
    """TS-001."""


@scenario(
    FEATURE,
    "Two valid dicts serialized from the same schema share the same 4-byte identifier prefix",
)
def test_ts002_same_schema_same_prefix() -> None:
    """TS-002."""


@scenario(
    FEATURE,
    "Dict missing a required field raises an error before any bytes are produced",
)
def test_ts003_missing_field_raises_error() -> None:
    """TS-003."""


@scenario(FEATURE, "Artifact not found in the registry raises a SchemaNotFoundError")
def test_ts004_artifact_not_found() -> None:
    """TS-004."""


@scenario(
    FEATURE, "Registry unreachable raises a RegistryConnectionError wrapping the cause"
)
def test_ts005_registry_unreachable() -> None:
    """TS-005."""


@scenario(
    FEATURE,
    "Extra fields in input dict are silently dropped when strict mode is disabled",
)
def test_ts006_extra_fields_dropped() -> None:
    """TS-006."""


@scenario(
    FEATURE, "Extra fields in input dict raise ValueError when strict mode is enabled"
)
def test_ts007_strict_mode_rejects_extra() -> None:
    """TS-007."""


# ── Given steps ──


@given(
    parsers.cfparse('a SerializationContext for topic "{topic}" and field {field}'),
    target_fixture="ctx",
)
def given_serialization_context(topic: str, field: str) -> SerializationContext:
    return SerializationContext(topic=topic, field=MessageField[field])


@given(
    parsers.cfparse('an AvroSerializer configured with artifact_id "{artifact_id}"'),
    target_fixture="serializer",
)
def given_serializer_for_artifact(
    mock_registry: respx.MockRouter, artifact_id: str
) -> AvroSerializer:
    _not_found_route(mock_registry, artifact_id)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    return AvroSerializer(registry_client=client, artifact_id=artifact_id)


@given(
    parsers.cfparse("the registry returns HTTP 404 for that artifact"),
)
def given_registry_returns_404() -> None:
    # Already set up in the previous step via _not_found_route
    pass


@given(
    parsers.cfparse(
        "an ApicurioRegistryClient configured with an unreachable registry URL"
    ),
    target_fixture="unreachable_client",
)
def given_unreachable_client(mock_registry: respx.MockRouter) -> ApicurioRegistryClient:
    unreachable_url = "http://unreachable-host:9999/apis/registry/v3"
    mock_registry.get(url__startswith=unreachable_url).mock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    return ApicurioRegistryClient(url=unreachable_url, group_id=GROUP_ID)


@given(
    parsers.cfparse(
        'an AvroSerializer using that client with artifact_id "{artifact_id}"'
    ),
    target_fixture="serializer",
)
def given_serializer_with_unreachable(
    unreachable_client: ApicurioRegistryClient, artifact_id: str
) -> AvroSerializer:
    return AvroSerializer(registry_client=unreachable_client, artifact_id=artifact_id)


@given(
    parsers.cfparse(
        'an AvroSerializer configured with strict={strict_val} and artifact_id "{artifact_id}"'
    ),
    target_fixture="serializer",
)
def given_serializer_with_strict(
    mock_registry: respx.MockRouter, strict_val: str, artifact_id: str
) -> AvroSerializer:
    _schema_route(mock_registry, artifact_id)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    return AvroSerializer(
        registry_client=client,
        artifact_id=artifact_id,
        strict=strict_val == "True",
    )


# ── When steps ──


@when(
    "the serializer is called with a valid dict conforming to the schema",
    target_fixture="result_bytes",
)
def when_serialize_valid_dict(
    serializer: AvroSerializer, ctx: SerializationContext
) -> bytes:
    return serializer(VALID_USER_EVENT, ctx)


@when(
    "two different valid dicts conforming to the same schema are serialized",
    target_fixture="two_results",
)
def when_serialize_two_dicts(
    serializer: AvroSerializer, ctx: SerializationContext
) -> tuple[bytes, bytes]:
    return serializer(VALID_USER_EVENT, ctx), serializer(VALID_USER_EVENT_ALT, ctx)


@when(
    "the serializer is called with a dict that is missing a field required by the schema",
    target_fixture="missing_field_error",
)
def when_serialize_missing_field(
    serializer: AvroSerializer, ctx: SerializationContext
) -> ValueError:
    with pytest.raises(ValueError) as exc_info:
        serializer(INVALID_USER_EVENT_MISSING_FIELD, ctx)
    return exc_info.value


@when(
    "the serializer is called with a valid dict and a SerializationContext",
    target_fixture="call_error",
)
def when_serialize_triggers_error(
    serializer: AvroSerializer,
) -> Exception:
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    with pytest.raises((SchemaNotFoundError, RegistryConnectionError)) as exc_info:
        serializer(VALID_USER_EVENT, ctx)
    return exc_info.value


@when(
    "the serializer is called with a dict containing extra fields not present in the schema",
    target_fixture="extra_fields_result",
)
def when_serialize_extra_fields(
    serializer: AvroSerializer, ctx: SerializationContext
) -> bytes | ValueError:
    try:
        return serializer(VALID_USER_EVENT_EXTRA_FIELDS, ctx)
    except ValueError as exc:
        return exc


# ── Then steps ──


@then("the returned bytes begin with magic byte 0x00")
def then_magic_byte(result_bytes: bytes) -> None:
    assert result_bytes[0:1] == b"\x00"


@then("bytes at offset 1 through 4 contain a 4-byte big-endian schema identifier")
def then_4byte_id(result_bytes: bytes) -> None:
    schema_id = struct.unpack(">I", result_bytes[1:5])[0]
    assert schema_id == GLOBAL_ID


@then("the remaining bytes are a valid Avro binary payload")
def then_avro_payload(result_bytes: bytes) -> None:
    assert len(result_bytes) > 5


@then("both outputs share the same 4-byte schema identifier prefix")
def then_same_prefix(two_results: tuple[bytes, bytes]) -> None:
    assert two_results[0][0:5] == two_results[1][0:5]


@then("a ValueError is raised")
def then_value_error_raised_generic(missing_field_error: ValueError) -> None:
    assert isinstance(missing_field_error, ValueError)


@then("no bytes are produced")
def then_no_bytes() -> None:
    # The ValueError was raised before any bytes, so nothing to check
    pass


@then("a SchemaNotFoundError is raised")
def then_schema_not_found(call_error: Exception) -> None:
    assert isinstance(call_error, SchemaNotFoundError)


@then("the error message identifies the missing artifact and the group")
def then_error_has_artifact(call_error: SchemaNotFoundError) -> None:
    msg = str(call_error)
    assert "NonExistentSchema" in msg
    assert GROUP_ID in msg


@then("a RegistryConnectionError is raised")
def then_registry_connection_error(call_error: Exception) -> None:
    assert isinstance(call_error, RegistryConnectionError)


@then("the error message includes the registry URL")
def then_error_has_url(call_error: RegistryConnectionError) -> None:
    assert "unreachable-host" in str(call_error)


@then("valid Confluent-framed Avro bytes are returned")
def then_valid_bytes_returned(extra_fields_result: bytes | ValueError) -> None:
    assert isinstance(extra_fields_result, bytes)
    assert extra_fields_result[0:1] == b"\x00"
    assert len(extra_fields_result) > 5


@then("no error is raised")
def then_no_error(extra_fields_result: bytes | ValueError) -> None:
    assert isinstance(extra_fields_result, bytes)


@then("a ValueError is raised before any bytes are produced")
def then_value_error_strict(extra_fields_result: bytes | ValueError) -> None:
    assert isinstance(extra_fields_result, ValueError)


# ── to_dict hook scenarios (TS-013, TS-014, TS-015) ──


@scenario(
    TO_DICT_FEATURE,
    "Provided to_dict callable is applied to the input before Avro encoding",
)
def test_ts013_to_dict_applied() -> None:
    """TS-013."""


@scenario(
    TO_DICT_FEATURE,
    "Absent to_dict callable means the plain dict is passed directly to the encoder",
)
def test_ts014_no_to_dict() -> None:
    """TS-014."""


@scenario(
    TO_DICT_FEATURE,
    "to_dict callable raising an exception is wrapped as a SerializationError",
)
def test_ts015_to_dict_error() -> None:
    """TS-015."""


# ── to_dict Given steps ──


class _UserEventObj:
    """Simple domain object for to_dict testing."""

    def __init__(self, user_id: str, country: str) -> None:
        self.userId = user_id
        self.country = country


@given(
    parsers.cfparse(
        'an AvroSerializer configured with a to_dict callable and artifact_id "{artifact_id}"'
    ),
    target_fixture="serializer",
)
def given_serializer_with_to_dict(
    mock_registry: respx.MockRouter, artifact_id: str
) -> AvroSerializer:
    _schema_route(mock_registry, artifact_id)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    return AvroSerializer(
        registry_client=client,
        artifact_id=artifact_id,
        to_dict=lambda obj, ctx: vars(obj),
    )


@given("the to_dict callable converts the input object to a valid dict")
def given_to_dict_converts() -> None:
    pass


@given(
    parsers.cfparse(
        'an AvroSerializer configured without a to_dict callable and artifact_id "{artifact_id}"'
    ),
    target_fixture="serializer",
)
def given_serializer_without_to_dict(
    mock_registry: respx.MockRouter, artifact_id: str
) -> AvroSerializer:
    _schema_route(mock_registry, artifact_id)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    return AvroSerializer(registry_client=client, artifact_id=artifact_id)


@given(
    "an AvroSerializer configured with a to_dict callable that raises a RuntimeError",
    target_fixture="serializer",
)
def given_serializer_with_failing_to_dict(
    mock_registry: respx.MockRouter,
) -> AvroSerializer:
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

    def bad_to_dict(data: Any, ctx: SerializationContext) -> dict[str, Any]:
        raise RuntimeError("conversion failed")

    return AvroSerializer(
        registry_client=client, artifact_id="UserEvent", to_dict=bad_to_dict
    )


# ── to_dict When steps ──


@when(
    "the serializer is called with a non-dict domain object",
    target_fixture="to_dict_result",
)
def when_serialize_domain_object(
    serializer: AvroSerializer, ctx: SerializationContext
) -> bytes:
    obj = _UserEventObj(user_id="abc-123", country="FR")
    return serializer(obj, ctx)


@when(
    "the serializer is called with a plain dict conforming to the schema",
    target_fixture="direct_dict_result",
)
def when_serialize_plain_dict(
    serializer: AvroSerializer, ctx: SerializationContext
) -> bytes:
    return serializer(VALID_USER_EVENT, ctx)


@when(
    "the serializer is called with an input object",
    target_fixture="to_dict_error",
)
def when_serialize_with_failing_to_dict(
    serializer: AvroSerializer, ctx: SerializationContext
) -> SerializationError:
    with pytest.raises(SerializationError) as exc_info:
        serializer(_UserEventObj(user_id="x", country="y"), ctx)
    return exc_info.value


# ── to_dict Then steps ──


@then("the to_dict callable is applied to the input first")
def then_to_dict_applied() -> None:
    pass


@then(
    "the resulting dict is Avro-encoded identically to serializing that dict directly"
)
def then_same_as_direct(to_dict_result: bytes, mock_registry: respx.MockRouter) -> None:
    # Serialize directly with a dict-only serializer to compare
    _schema_route(mock_registry, "UserEvent-compare")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    direct_ser = AvroSerializer(registry_client=client, artifact_id="UserEvent-compare")
    ctx = SerializationContext(topic="users", field=MessageField.VALUE)
    direct_bytes = direct_ser(VALID_USER_EVENT, ctx)
    # Avro payload (bytes 5+) should be identical
    assert to_dict_result[5:] == direct_bytes[5:]


@then("the dict is used directly for Avro encoding with no transformation applied")
def then_no_transformation(direct_dict_result: bytes) -> None:
    assert isinstance(direct_dict_result, bytes)
    assert direct_dict_result[0:1] == b"\x00"
    assert len(direct_dict_result) > 5


@then("a SerializationError is raised")
def then_serialization_error(to_dict_error: SerializationError) -> None:
    assert isinstance(to_dict_error, SerializationError)


@then("the SerializationError includes the original RuntimeError as its cause")
def then_error_has_cause(to_dict_error: SerializationError) -> None:
    assert isinstance(to_dict_error.__cause__, RuntimeError)


@then("the error message identifies the failed conversion")
def then_error_msg_conversion(to_dict_error: SerializationError) -> None:
    assert (
        "to_dict" in str(to_dict_error).lower()
        or "conversion" in str(to_dict_error).lower()
    )


# ── Additional coverage tests ──


def test_strict_mode_valid_data_passes(mock_registry: respx.MockRouter) -> None:
    """strict=True with conforming data produces valid bytes (branch 92->98)."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    serializer = AvroSerializer(
        registry_client=client, artifact_id="UserEvent", strict=True
    )
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    result = serializer(VALID_USER_EVENT, ctx)
    assert result[0:1] == b"\x00"
    assert len(result) > 5


# ── T005: wire_format parameter and serialize() CONFLUENT_PAYLOAD path ──


def test_serialize_confluent_payload_returns_serialized_message(
    mock_registry: respx.MockRouter,
) -> None:
    """serialize() with CONFLUENT_PAYLOAD returns a SerializedMessage whose payload
    starts with magic byte 0x00 and whose headers dict is empty."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    serializer = AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
        wire_format=WireFormat.CONFLUENT_PAYLOAD,
    )
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    result = serializer.serialize(VALID_USER_EVENT, ctx)
    assert isinstance(result, SerializedMessage)
    assert result.payload[0:1] == b"\x00"
    assert result.headers == {}


def test_serialize_default_wire_format_is_confluent_payload(
    mock_registry: respx.MockRouter,
) -> None:
    """AvroSerializer created without wire_format defaults to CONFLUENT_PAYLOAD."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    serializer = AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
    )
    assert serializer.wire_format == WireFormat.CONFLUENT_PAYLOAD


def test_serialize_confluent_payload_matches_call(
    mock_registry: respx.MockRouter,
) -> None:
    """serialize().payload and __call__() return identical bytes."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    serializer = AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
    )
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    serialized_msg = serializer.serialize(VALID_USER_EVENT, ctx)
    call_bytes = serializer(VALID_USER_EVENT, ctx)
    assert serialized_msg.payload == call_bytes


def test_wire_format_param_stored_on_instance(
    mock_registry: respx.MockRouter,
) -> None:
    """wire_format=KAFKA_HEADERS is stored on the serializer instance."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    serializer = AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
        wire_format=WireFormat.KAFKA_HEADERS,
    )
    assert serializer.wire_format == WireFormat.KAFKA_HEADERS


def test_call_raises_type_error_for_kafka_headers(
    mock_registry: respx.MockRouter,
) -> None:
    """__call__ raises TypeError when wire_format is KAFKA_HEADERS."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    serializer = AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
        wire_format=WireFormat.KAFKA_HEADERS,
    )
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    with pytest.raises(TypeError, match="use serialize\\(\\)"):
        serializer(VALID_USER_EVENT, ctx)


def test_invalid_wire_format_raises_value_error(
    mock_registry: respx.MockRouter,
) -> None:
    """Passing an invalid wire_format value raises ValueError."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(ValueError):
        AvroSerializer(
            registry_client=client,
            artifact_id="UserEvent",
            wire_format="not_valid",  # type: ignore[arg-type]
        )


def test_invalid_use_id_raises_value_error(
    mock_registry: respx.MockRouter,
) -> None:
    """Passing an invalid use_id value raises ValueError (M-001)."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(ValueError, match="use_id must be"):
        AvroSerializer(
            registry_client=client,
            artifact_id="UserEvent",
            use_id="badValue",  # type: ignore[arg-type]
        )


def test_strict_mode_non_record_schema_raises_value_error(
    mock_registry: respx.MockRouter,
) -> None:
    """strict=True with a non-record schema raises ValueError."""
    non_record_schema = {"type": "string"}
    _schema_route(mock_registry, "StringSchema", schema=non_record_schema)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    serializer = AvroSerializer(
        registry_client=client, artifact_id="StringSchema", strict=True
    )
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    with pytest.raises(ValueError, match="strict mode requires a record schema"):
        serializer("hello", ctx)


def test_parsed_schema_none_raises_runtime_error(
    mock_registry: respx.MockRouter,
) -> None:
    """Defensive guard: _parsed_schema=None raises RuntimeError."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    serializer = AvroSerializer(registry_client=client, artifact_id="UserEvent")
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    # Force schema fetch then corrupt internal state
    serializer(VALID_USER_EVENT, ctx)
    serializer._parsed_schema = None
    with pytest.raises(RuntimeError, match="_parsed_schema unexpectedly None"):
        serializer.serialize(VALID_USER_EVENT, ctx)


# ── artifact_resolver construction validation tests ──


def test_both_artifact_id_and_resolver_raises_value_error() -> None:
    """Providing both artifact_id and artifact_resolver raises ValueError."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(ValueError, match="mutually exclusive"):
        AvroSerializer(
            registry_client=client,
            artifact_id="UserEvent",
            artifact_resolver=lambda ctx: "UserEvent",
        )


def test_neither_artifact_id_nor_resolver_raises_value_error() -> None:
    """Providing neither artifact_id nor artifact_resolver raises ValueError."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(ValueError, match="required"):
        AvroSerializer(registry_client=client)


def test_artifact_id_only_constructs_successfully() -> None:
    """artifact_id only constructs without error (existing behaviour)."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    ser = AvroSerializer(registry_client=client, artifact_id="UserEvent")
    assert ser.artifact_id == "UserEvent"


def test_artifact_resolver_only_constructs_successfully() -> None:
    """artifact_resolver only constructs without error (new behaviour)."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    resolver = lambda ctx: "UserEvent"  # noqa: E731
    AvroSerializer(registry_client=client, artifact_resolver=resolver)


# ── artifact_resolver serialize path integration tests ──


def test_topic_id_strategy_calls_registry_with_derived_artifact_id(
    mock_registry: respx.MockRouter,
) -> None:
    """TopicIdStrategy resolves to 'orders-value'; registry called with that ID."""
    from apicurio_serdes.avro import TopicIdStrategy

    _schema_route(mock_registry, "orders-value")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    ser = AvroSerializer(registry_client=client, artifact_resolver=TopicIdStrategy())
    ctx = SerializationContext(topic="orders", field=MessageField.VALUE)
    result = ser(VALID_USER_EVENT, ctx)
    assert result[0:1] == b"\x00"
    assert len(result) > 5


def test_simple_topic_id_strategy_calls_registry_with_topic(
    mock_registry: respx.MockRouter,
) -> None:
    """SimpleTopicIdStrategy resolves to 'orders'; registry called with that ID."""
    from apicurio_serdes.avro import SimpleTopicIdStrategy

    _schema_route(mock_registry, "orders")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    ser = AvroSerializer(
        registry_client=client, artifact_resolver=SimpleTopicIdStrategy()
    )
    ctx = SerializationContext(topic="orders", field=MessageField.VALUE)
    result = ser(VALID_USER_EVENT, ctx)
    assert result[0:1] == b"\x00"
    assert len(result) > 5


def test_lambda_resolver_equivalent_to_static_artifact_id(
    mock_registry: respx.MockRouter,
) -> None:
    """lambda ctx: 'UserEvent' resolver behaves like artifact_id='UserEvent'."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    ser = AvroSerializer(
        registry_client=client, artifact_resolver=lambda ctx: "UserEvent"
    )
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    result = ser(VALID_USER_EVENT, ctx)
    assert result[0:1] == b"\x00"
    assert len(result) > 5


def test_resolver_called_once_schema_cached(
    mock_registry: respx.MockRouter,
) -> None:
    """Serializing twice with the same resolver calls the registry exactly once."""
    route = _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    call_count = 0

    def counting_resolver(ctx: SerializationContext) -> str:
        nonlocal call_count
        call_count += 1
        return "UserEvent"

    ser = AvroSerializer(registry_client=client, artifact_resolver=counting_resolver)
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    ser(VALID_USER_EVENT, ctx)
    ser(VALID_USER_EVENT, ctx)
    assert call_count == 1
    assert route.call_count == 1


def test_resolver_raising_exception_wraps_as_resolver_error(
    mock_registry: respx.MockRouter,
) -> None:
    """A resolver that raises is wrapped in ResolverError."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

    def bad_resolver(ctx: SerializationContext) -> str:
        raise RuntimeError("resolver failed")

    ser = AvroSerializer(registry_client=client, artifact_resolver=bad_resolver)
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    with pytest.raises(ResolverError, match="resolver failed") as exc_info:
        ser(VALID_USER_EVENT, ctx)
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_resolver_returning_non_str_raises_resolver_error(
    mock_registry: respx.MockRouter,
) -> None:
    """A resolver returning a non-str raises ResolverError."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    ser = AvroSerializer(registry_client=client, artifact_resolver=lambda ctx: None)  # type: ignore[arg-type, return-value]
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    with pytest.raises(ResolverError, match="non-empty str"):
        ser(VALID_USER_EVENT, ctx)


def test_confluent_payload_schema_id_exceeds_uint32_raises_value_error(
    mock_registry: respx.MockRouter,
) -> None:
    """Schema ID > 2^32-1 in CONFLUENT_PAYLOAD mode raises ValueError."""
    from apicurio_serdes._client import CachedSchema

    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    serializer = AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
        wire_format=WireFormat.CONFLUENT_PAYLOAD,
    )
    ctx = SerializationContext(topic="test", field=MessageField.VALUE)
    # Trigger schema fetch so _schema is populated
    serializer(VALID_USER_EVENT, ctx)
    # Inject an overflowing global_id via a new CachedSchema
    original = serializer._schema
    assert original is not None
    serializer._schema = CachedSchema(
        schema=original.schema,
        global_id=2**32,
        content_id=original.content_id,
    )
    with pytest.raises(ValueError, match="unsigned 32-bit limit"):
        serializer.serialize(VALID_USER_EVENT, ctx)


# ── auto-register tests ──


class TestAutoRegister:
    """Tests for AvroSerializer auto_register feature."""

    def test_auto_register_true_without_schema_raises_value_error(self) -> None:
        """auto_register=True without schema= raises ValueError at construction."""
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(ValueError, match="schema"):
            AvroSerializer(
                registry_client=client,
                artifact_id="UserEvent",
                auto_register=True,
            )

    def test_invalid_if_exists_raises_value_error(self) -> None:
        """Invalid if_exists value raises ValueError at construction."""
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(ValueError, match="if_exists"):
            AvroSerializer(
                registry_client=client,
                artifact_id="UserEvent",
                auto_register=True,
                schema=USER_EVENT_SCHEMA_JSON,
                if_exists="UPSERT",
            )

    def test_auto_register_false_with_schema_accepted(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """auto_register=False with schema= constructs without error (schema ignored)."""
        _schema_route(mock_registry, "UserEvent")
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        ser = AvroSerializer(
            registry_client=client,
            artifact_id="UserEvent",
            auto_register=False,
            schema=USER_EVENT_SCHEMA_JSON,
        )
        assert ser is not None

    def test_auto_register_get_404_then_post_200_succeeds(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """GET 404 + POST 200 with auto_register=True returns framed bytes."""
        _not_found_route(mock_registry, "UserEvent")
        _register_route(mock_registry, "UserEvent")
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        ser = AvroSerializer(
            registry_client=client,
            artifact_id="UserEvent",
            auto_register=True,
            schema=USER_EVENT_SCHEMA_JSON,
        )
        ctx = SerializationContext(topic="test", field=MessageField.VALUE)
        result = ser.serialize(VALID_USER_EVENT, ctx)
        assert result.payload[0:1] == b"\x00"
        assert len(result.payload) > 5

    def test_auto_register_second_serialize_is_cache_hit(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """Second serialize call after auto-register is a cache hit (no extra HTTP)."""
        not_found = _not_found_route(mock_registry, "UserEvent")
        reg_route = _register_route(mock_registry, "UserEvent")
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        ser = AvroSerializer(
            registry_client=client,
            artifact_id="UserEvent",
            auto_register=True,
            schema=USER_EVENT_SCHEMA_JSON,
        )
        ctx = SerializationContext(topic="test", field=MessageField.VALUE)
        result1 = ser.serialize(VALID_USER_EVENT, ctx)
        result2 = ser.serialize(VALID_USER_EVENT, ctx)
        # Registry called exactly once for GET (404) and once for POST
        assert not_found.call_count == 1
        assert reg_route.call_count == 1
        # Both results are valid framed bytes (serialization worked)
        assert result1.payload[0:1] == b"\x00"
        assert result2.payload[0:1] == b"\x00"

    def test_auto_register_false_get_404_propagates_schema_not_found(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """auto_register=False: GET 404 raises SchemaNotFoundError unchanged."""
        from apicurio_serdes._errors import SchemaNotFoundError

        _not_found_route(mock_registry, "UserEvent")
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        ser = AvroSerializer(
            registry_client=client,
            artifact_id="UserEvent",
        )
        ctx = SerializationContext(topic="test", field=MessageField.VALUE)
        with pytest.raises(SchemaNotFoundError):
            ser.serialize(VALID_USER_EVENT, ctx)

    def test_auto_register_post_409_raises_schema_registration_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """GET 404 + POST 409 raises SchemaRegistrationError."""
        from apicurio_serdes._errors import SchemaRegistrationError

        _not_found_route(mock_registry, "UserEvent")
        _register_error_route(mock_registry, 409)
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        ser = AvroSerializer(
            registry_client=client,
            artifact_id="UserEvent",
            auto_register=True,
            schema=USER_EVENT_SCHEMA_JSON,
        )
        ctx = SerializationContext(topic="test", field=MessageField.VALUE)
        with pytest.raises(SchemaRegistrationError):
            ser.serialize(VALID_USER_EVENT, ctx)

    def test_auto_register_post_network_error_raises_registry_connection_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """GET 404 + POST network error raises RegistryConnectionError."""
        from apicurio_serdes._errors import RegistryConnectionError

        _not_found_route(mock_registry, "UserEvent")
        mock_registry.post(
            url__startswith=f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts"
        ).mock(side_effect=httpx.ConnectError("refused"))
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        ser = AvroSerializer(
            registry_client=client,
            artifact_id="UserEvent",
            auto_register=True,
            schema=USER_EVENT_SCHEMA_JSON,
        )
        ctx = SerializationContext(topic="test", field=MessageField.VALUE)
        with pytest.raises(RegistryConnectionError):
            ser.serialize(VALID_USER_EVENT, ctx)

    def test_auto_register_if_exists_default_is_find_or_create_version(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """Default if_exists='FIND_OR_CREATE_VERSION' is forwarded as ifExists=FIND_OR_CREATE_VERSION."""
        _not_found_route(mock_registry, "UserEvent")
        reg_route = _register_route(mock_registry, "UserEvent", if_exists="FIND_OR_CREATE_VERSION")
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        ser = AvroSerializer(
            registry_client=client,
            artifact_id="UserEvent",
            auto_register=True,
            schema=USER_EVENT_SCHEMA_JSON,
        )
        ctx = SerializationContext(topic="test", field=MessageField.VALUE)
        ser.serialize(VALID_USER_EVENT, ctx)
        assert reg_route.call_count == 1

    def test_auto_register_if_exists_fail_forwarded(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """if_exists='FAIL' is forwarded as ifExists=FAIL."""
        _not_found_route(mock_registry, "UserEvent")
        reg_route = _register_route(mock_registry, "UserEvent", if_exists="FAIL")
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        ser = AvroSerializer(
            registry_client=client,
            artifact_id="UserEvent",
            auto_register=True,
            schema=USER_EVENT_SCHEMA_JSON,
            if_exists="FAIL",
        )
        ctx = SerializationContext(topic="test", field=MessageField.VALUE)
        ser.serialize(VALID_USER_EVENT, ctx)
        assert reg_route.call_count == 1

    def test_auto_register_with_artifact_resolver(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """auto_register=True works with artifact_resolver."""
        from apicurio_serdes.avro import TopicIdStrategy

        _not_found_route(mock_registry, "test-value")
        _register_route(mock_registry, "test-value")
        client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        ser = AvroSerializer(
            registry_client=client,
            artifact_resolver=TopicIdStrategy(),
            auto_register=True,
            schema=USER_EVENT_SCHEMA_JSON,
        )
        ctx = SerializationContext(topic="test", field=MessageField.VALUE)
        result = ser.serialize(VALID_USER_EVENT, ctx)
        assert result.payload[0:1] == b"\x00"
