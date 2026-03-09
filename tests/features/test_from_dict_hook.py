"""BDD step definitions for from_dict_hook.feature [T020, TS-013 through TS-015]."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import respx
from pytest_bdd import given, parsers, scenario, then, when

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes._errors import DeserializationError
from apicurio_serdes.avro import AvroDeserializer
from apicurio_serdes.serialization import MessageField, SerializationContext
from tests.conftest import (
    GROUP_ID,
    REGISTRY_URL,
    VALID_USER_EVENT,
    _id_schema_route,
    make_confluent_bytes,
)

FEATURE = "../../specs/002-avro-deserializer/tests/features/from_dict_hook.feature"

CONTENT_ID_42 = 42


@dataclass
class UserEvent:
    """Domain object for testing from_dict hook."""

    userId: str
    country: str


# ── Scenarios ──


@scenario(
    FEATURE,
    "Provided from_dict callable is applied to the decoded dict before returning",
)
def test_ts013_from_dict_applied() -> None:
    """TS-013."""


@scenario(
    FEATURE,
    "Absent from_dict callable returns the decoded dict directly with no transformation",
)
def test_ts014_no_from_dict() -> None:
    """TS-014."""


@scenario(
    FEATURE,
    "from_dict callable raising an exception is wrapped as a DeserializationError",
)
def test_ts015_from_dict_error() -> None:
    """TS-015."""


# ── Background steps ──


@given(
    parsers.cfparse(
        "a configured ApicurioRegistryClient pointing at a registry that holds"
        ' a known Avro schema with contentId {content_id:d} for artifact "{artifact_id}"'
    ),
    target_fixture="registry_client",
)
def given_client_fdh(
    mock_registry: respx.MockRouter, content_id: int, artifact_id: str
) -> ApicurioRegistryClient:
    _id_schema_route(mock_registry, "contentId", content_id)
    return ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


@given(
    "valid Confluent-framed Avro bytes produced for that schema",
    target_fixture="input_bytes",
)
def given_valid_bytes() -> bytes:
    return make_confluent_bytes(CONTENT_ID_42, VALID_USER_EVENT)


# ── TS-013 steps ──


@given(
    "an AvroDeserializer configured with a from_dict callable that constructs a UserEvent dataclass",
    target_fixture="deserializer",
)
def given_deserializer_with_from_dict(
    registry_client: ApicurioRegistryClient,
) -> AvroDeserializer:
    def from_dict(d: dict[str, Any], ctx: SerializationContext) -> UserEvent:
        return UserEvent(**d)

    return AvroDeserializer(registry_client=registry_client, from_dict=from_dict)


@given(
    parsers.cfparse('a SerializationContext for topic "{topic}" and field {field}'),
    target_fixture="ctx",
)
def given_ctx_fdh(topic: str, field: str) -> SerializationContext:
    return SerializationContext(topic=topic, field=MessageField[field])


@when(
    "the deserializer is called with the valid Avro bytes and the context",
    target_fixture="deser_result",
)
def when_deserialize(
    deserializer: AvroDeserializer,
    input_bytes: bytes,
    ctx: SerializationContext,
) -> Any:
    try:
        return deserializer(input_bytes, ctx)
    except Exception as exc:
        return exc


@then("the from_dict callable is applied to the decoded dict")
def then_from_dict_applied(deser_result: Any) -> None:
    assert not isinstance(deser_result, Exception)


@then("the returned value is a UserEvent dataclass instance, not a plain dict")
def then_is_user_event(deser_result: Any) -> None:
    assert isinstance(deser_result, UserEvent)
    assert deser_result.userId == VALID_USER_EVENT["userId"]
    assert deser_result.country == VALID_USER_EVENT["country"]


# ── TS-014 steps ──


@given(
    "an AvroDeserializer configured without a from_dict callable",
    target_fixture="deserializer",
)
def given_deserializer_no_from_dict(
    registry_client: ApicurioRegistryClient,
) -> AvroDeserializer:
    return AvroDeserializer(registry_client=registry_client)


@then("the returned value is a plain Python dict")
def then_is_dict(deser_result: Any) -> None:
    assert isinstance(deser_result, dict)


@then("no transformation is applied")
def then_no_transform(deser_result: Any) -> None:
    assert deser_result == VALID_USER_EVENT


# ── TS-015 steps ──


@given(
    "an AvroDeserializer configured with a from_dict callable that raises a RuntimeError",
    target_fixture="deserializer",
)
def given_deserializer_with_failing_from_dict(
    registry_client: ApicurioRegistryClient,
) -> AvroDeserializer:
    def bad_from_dict(d: dict[str, Any], ctx: SerializationContext) -> Any:
        raise RuntimeError("conversion failed")

    return AvroDeserializer(registry_client=registry_client, from_dict=bad_from_dict)


@then("a DeserializationError is raised")
def then_deserialization_error(deser_result: Any) -> None:
    assert isinstance(deser_result, DeserializationError)


@then("the DeserializationError includes the original RuntimeError as its cause")
def then_has_cause(deser_result: Any) -> None:
    assert isinstance(deser_result, DeserializationError)
    assert isinstance(deser_result.__cause__, RuntimeError)


@then("the error message identifies the failed conversion")
def then_error_msg_conversion(deser_result: Any) -> None:
    assert (
        "from_dict" in str(deser_result).lower()
        or "conversion" in str(deser_result).lower()
    )
