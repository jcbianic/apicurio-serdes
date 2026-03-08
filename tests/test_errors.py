"""Tests for DeserializationError and SchemaNotFoundError.from_id [T002, T003]."""

from __future__ import annotations

import pytest

from apicurio_serdes._errors import DeserializationError, SchemaNotFoundError


# ── T002: DeserializationError ──


def test_deserialization_error_message() -> None:
    """DeserializationError stores the message [TS-003]."""
    err = DeserializationError("bad magic byte")
    assert "bad magic byte" in str(err)


def test_deserialization_error_no_cause() -> None:
    """DeserializationError without cause has no __cause__ [TS-005]."""
    err = DeserializationError("short input")
    assert err.__cause__ is None


def test_deserialization_error_with_cause() -> None:
    """DeserializationError wraps cause and sets __cause__ [TS-006]."""
    original = ValueError("decode failed")
    err = DeserializationError("Avro decode failure", cause=original)
    assert err.__cause__ is original


def test_deserialization_error_cause_attribute() -> None:
    """DeserializationError.cause attribute is accessible [TS-007]."""
    original = RuntimeError("oops")
    err = DeserializationError("from_dict failed", cause=original)
    assert err.cause is original


def test_deserialization_error_is_exception() -> None:
    """DeserializationError is raised and caught as Exception [TS-015]."""
    with pytest.raises(DeserializationError, match="bad magic"):
        raise DeserializationError("bad magic byte")


# ── T003: SchemaNotFoundError.from_id ──


def test_schema_not_found_from_id_message_content_id() -> None:
    """from_id creates error with id_type and id_value in message [TS-004]."""
    err = SchemaNotFoundError.from_id("contentId", 42)
    assert "contentId" in str(err)
    assert "42" in str(err)


def test_schema_not_found_from_id_message_global_id() -> None:
    """from_id creates error with globalId in message [TS-004]."""
    err = SchemaNotFoundError.from_id("globalId", 7)
    assert "globalId" in str(err)
    assert "7" in str(err)


def test_schema_not_found_from_id_type_attribute() -> None:
    """from_id sets id_type attribute [TS-004]."""
    err = SchemaNotFoundError.from_id("globalId", 7)
    assert err.id_type == "globalId"


def test_schema_not_found_from_id_value_attribute() -> None:
    """from_id sets id_value attribute [TS-004]."""
    err = SchemaNotFoundError.from_id("contentId", 9999)
    assert err.id_value == 9999


def test_schema_not_found_from_id_returns_correct_type() -> None:
    """from_id returns a SchemaNotFoundError instance."""
    err = SchemaNotFoundError.from_id("contentId", 9999)
    assert isinstance(err, SchemaNotFoundError)
