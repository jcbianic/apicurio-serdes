"""Step definitions for WireFormat API scenarios [TS-020..TS-024].

RED phase: these tests import WireFormat which does not yet exist in
production code.  They are expected to fail with ImportError until
the production code is written.
"""

from __future__ import annotations

from typing import Any

import pytest
import respx
from pytest_bdd import given, parsers, scenario, then, when

# Imports that will fail until production code is written (RED phase).
# WireFormat does not yet exist in apicurio_serdes or apicurio_serdes.serialization.
from apicurio_serdes import ApicurioRegistryClient, WireFormat
from apicurio_serdes.avro import AvroSerializer
from tests.conftest import (
    GROUP_ID,
    REGISTRY_URL,
    _schema_route,
)

FEATURES_BASE = "../../specs/004-kafka-headers-wire-format/tests/features"
FEATURE = f"{FEATURES_BASE}/wire_format_api.feature"


# ── Scenarios ──


@scenario(FEATURE, "WireFormat is importable from the library top-level namespace")
def test_ts020_wire_format_importable() -> None:
    """TS-020."""


@scenario(
    FEATURE,
    "WireFormat enum exposes CONFLUENT_PAYLOAD and KAFKA_HEADERS members",
)
def test_ts021_wire_format_enum_members() -> None:
    """TS-021."""


@scenario(
    FEATURE,
    "AvroSerializer accepts wire_format=WireFormat.KAFKA_HEADERS without error",
)
def test_ts022_serializer_accepts_kafka_headers() -> None:
    """TS-022."""


@scenario(
    FEATURE,
    "AvroSerializer defaults to CONFLUENT_PAYLOAD when no wire_format is specified",
)
def test_ts023_serializer_defaults_confluent_payload() -> None:
    """TS-023."""


@scenario(
    FEATURE,
    "Passing an invalid wire_format value raises an error at construction",
)
def test_ts024_invalid_wire_format_raises() -> None:
    """TS-024."""


# ── Given steps ──


@given("the apicurio_serdes package is installed")
def given_package_installed() -> None:
    """Verify the package is importable (implicit by reaching this step)."""


@given(
    "the WireFormat enum is imported from apicurio_serdes",
    target_fixture="wire_format_cls",
)
def given_wire_format_imported() -> type:
    """Return the WireFormat enum class."""
    return WireFormat


# ── When steps ──


@when(
    "a developer imports WireFormat from apicurio_serdes",
    target_fixture="imported_wire_format",
)
def when_import_wire_format() -> type:
    import apicurio_serdes

    return apicurio_serdes.WireFormat


@when(
    "a developer inspects the WireFormat enum members",
    target_fixture="wire_format_members",
)
def when_inspect_members(wire_format_cls: type) -> dict[str, Any]:
    return {member.name: member for member in wire_format_cls}  # type: ignore[attr-defined]


@when(
    "a developer configures AvroSerializer with wire_format=WireFormat.KAFKA_HEADERS",
    target_fixture="serializer_result",
)
def when_configure_kafka_headers(mock_registry: respx.MockRouter) -> dict[str, Any]:
    result: dict[str, Any] = {"error": None, "serializer": None}
    artifact_id = "WireFormatTest"
    _schema_route(mock_registry, artifact_id)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    try:
        serializer = AvroSerializer(
            registry_client=client,
            artifact_id=artifact_id,
            wire_format=WireFormat.KAFKA_HEADERS,
        )
        result["serializer"] = serializer
    except (TypeError, ValueError) as exc:
        result["error"] = exc
    return result


@when(
    "a developer creates AvroSerializer without a wire_format argument",
    target_fixture="default_serializer",
)
def when_create_without_wire_format(mock_registry: respx.MockRouter) -> AvroSerializer:
    artifact_id = "DefaultWireFormatTest"
    _schema_route(mock_registry, artifact_id)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    return AvroSerializer(
        registry_client=client,
        artifact_id=artifact_id,
    )


@when(
    parsers.cfparse(
        'a developer creates AvroSerializer with an invalid wire_format value "{value}"'
    ),
    target_fixture="construction_error",
)
def when_create_with_invalid_wire_format(
    mock_registry: respx.MockRouter, value: str
) -> ValueError | None:
    artifact_id = "InvalidWireFormatTest"
    _schema_route(mock_registry, artifact_id)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(ValueError) as exc_info:
        AvroSerializer(
            registry_client=client,
            artifact_id=artifact_id,
            wire_format=value,  # type: ignore[arg-type]
        )
    return exc_info.value


# ── Then steps ──


@then("the import succeeds without error")
def then_import_succeeds(imported_wire_format: type) -> None:
    assert imported_wire_format is not None


@then("WireFormat is accessible as apicurio_serdes.WireFormat")
def then_accessible_from_namespace(imported_wire_format: type) -> None:
    import apicurio_serdes

    assert hasattr(apicurio_serdes, "WireFormat")
    assert apicurio_serdes.WireFormat is imported_wire_format


@then("WireFormat.CONFLUENT_PAYLOAD is a valid member")
def then_confluent_payload_member(wire_format_members: dict[str, Any]) -> None:
    assert "CONFLUENT_PAYLOAD" in wire_format_members


@then("WireFormat.KAFKA_HEADERS is a valid member")
def then_kafka_headers_member(wire_format_members: dict[str, Any]) -> None:
    assert "KAFKA_HEADERS" in wire_format_members


@then("no TypeError is raised")
def then_no_type_error(serializer_result: dict[str, Any]) -> None:
    assert not isinstance(serializer_result["error"], TypeError)


@then("no ValueError is raised")
def then_no_value_error(serializer_result: dict[str, Any]) -> None:
    assert not isinstance(serializer_result["error"], ValueError)


@then("the serializer is configured in KAFKA_HEADERS mode")
def then_configured_kafka_headers(serializer_result: dict[str, Any]) -> None:
    serializer = serializer_result["serializer"]
    assert serializer is not None
    assert serializer.wire_format == WireFormat.KAFKA_HEADERS


@then("the serializer defaults to WireFormat.CONFLUENT_PAYLOAD mode")
def then_defaults_confluent_payload(default_serializer: AvroSerializer) -> None:
    assert default_serializer.wire_format == WireFormat.CONFLUENT_PAYLOAD


@then("a ValueError is raised at construction time")
def then_value_error_raised(construction_error: ValueError | None) -> None:
    assert construction_error is not None
    assert isinstance(construction_error, ValueError)
