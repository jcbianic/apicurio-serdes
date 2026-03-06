"""Step definitions for TS-008: group_id is required for ApicurioRegistryClient."""

from __future__ import annotations

import pytest
from pytest_bdd import scenario, then, when

from apicurio_serdes import ApicurioRegistryClient


@scenario(
    "../../specs/001-avro-serializer/tests/features/avro_serialization.feature",
    "group_id is a required parameter for ApicurioRegistryClient",
)
def test_group_id_required() -> None:
    """TS-008."""


@when(
    "an ApicurioRegistryClient is constructed without providing a group_id",
    target_fixture="construction_error",
)
def when_client_without_group_id() -> ValueError:
    with pytest.raises(ValueError) as exc_info:
        ApicurioRegistryClient(url="http://registry:8080/apis/registry/v3", group_id="")
    return exc_info.value


@then("a ValueError is raised indicating that group_id is required")
def then_value_error_raised(construction_error: ValueError) -> None:
    assert "group_id" in str(construction_error)
