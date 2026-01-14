import pytest

from api.core.exceptions import InputValidationError, InternalServerError
from api.services.analysis_service import (
    _process_node_labels,
    _validate_block_range,
    analyze_contract_dependencies,
    label_crud,
)


class DummyCallGraph:
    def __init__(self, nodes):
        self.nodes = {addr: {} for addr in nodes}


def test_validate_block_range_valid():
    _validate_block_range("10", "20")  # should not raise


def test_validate_block_range_invalid_range():
    with pytest.raises(ValueError) as exc:
        _validate_block_range("0", "1000")
    assert "Block range exceeds maximum" in str(exc.value)


def test_validate_block_range_non_integer():
    with pytest.raises(ValueError) as exc:
        _validate_block_range("foo", "bar")
    assert "invalid literal for int()" in str(exc.value)


def test_process_node_labels_with_existing_labels(session):
    # Insert label into DB
    label_crud.create_label(
        session, label_crud.LabelCreate(address="0xAAA", label="KnownLabel")
    )

    cg = DummyCallGraph(["0xAAA"])
    result = _process_node_labels(session, cg)

    assert result == {"0xAAA": "KnownLabel"}


def test_process_node_labels_with_missing_labels(session, monkeypatch):
    # No label in DB for 0xBBB
    monkeypatch.setattr(
        "api.services.analysis_service.cc.allium_client.get_labels",
        lambda addrs: {"0xbbb": "NewLabel"},
    )

    cg = DummyCallGraph(["0xBBB"])
    result = _process_node_labels(session, cg)

    # Label should now be stored in DB
    stored = label_crud.get_label(session, "0xBBB")
    assert stored is not None
    assert stored.label == "NewLabel"

    assert result == {"0xBBB": "NewLabel"}


def test_process_node_labels_missing_labels_not_found(session, monkeypatch):
    monkeypatch.setattr(
        "api.services.analysis_service.cc.allium_client.get_labels",
        lambda addrs: {},
    )

    cg = DummyCallGraph(["0xCCC"])
    result = _process_node_labels(session, cg)

    # Fallback: address used as label
    stored = label_crud.get_label(session, "0xCCC")
    assert stored is None  # nothing stored
    assert result == {"0xCCC": "0xCCC"}


def test_analyze_contract_dependencies_success(session, monkeypatch):
    dummy_cg = DummyCallGraph(["0xAAA"])
    monkeypatch.setattr(
        "api.services.analysis_service.cc.get_dependencies_full",
        lambda **kw: dummy_cg,
    )
    monkeypatch.setattr(
        "api.services.analysis_service.cc.allium_client.get_labels",
        lambda addrs: {"0xaaa": "Labelled"},
    )

    result = analyze_contract_dependencies(session, "0xAAA")
    assert isinstance(result, DummyCallGraph)
    assert result.nodes == {"0xAAA": "Labelled"}


def test_analyze_contract_dependencies_value_error(session, monkeypatch):
    def bad_call(**kw):
        raise ValueError("bad range")

    monkeypatch.setattr(
        "api.services.analysis_service.cc.get_dependencies_full", bad_call
    )

    with pytest.raises(InputValidationError):
        analyze_contract_dependencies(session, "0xAAA")


def test_analyze_contract_dependencies_internal_error(session, monkeypatch):
    def bad_call(**kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "api.services.analysis_service.cc.get_dependencies_full", bad_call
    )

    with pytest.raises(InternalServerError):
        analyze_contract_dependencies(session, "0xAAA")
