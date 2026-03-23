import pytest

from src.api.core.exceptions import InputValidationError, InternalServerError
from src.api.models.label import LabelCreate
from src.api.services.analysis_service import (
    _process_node_labels,
    _validate_block_range,
    analyze_contract_dependencies,
    label_crud,
)


class _FakeClient:
    def __init__(self, labels=None, network_latest=None, network_range=None):
        self._labels = labels or {}
        self._network_latest = network_latest
        self._network_range = network_range

    def get_labels(self, _addresses):
        return self._labels

    def get_contract_dependencies_latest(self, address, block_range):
        _ = (address, block_range)
        return self._network_latest

    def get_contract_dependencies(self, address, from_block, to_block):
        _ = (address, from_block, to_block)
        return self._network_range


def test_validate_block_range_valid():
    _validate_block_range("10", "20")


def test_validate_block_range_invalid_range():
    with pytest.raises(ValueError) as exc:
        _validate_block_range("0", "1000")
    assert "Block range exceeds maximum" in str(exc.value)


def test_validate_block_range_non_integer():
    with pytest.raises(ValueError) as exc:
        _validate_block_range("foo", "bar")
    assert "Invalid block number" in str(exc.value)


def test_process_node_labels_with_existing_labels(session):
    label_crud.create_label(
        session, LabelCreate(address="0xAAA", label="KnownLabel")
    )
    network = {"nodes": ["0xAAA"]}

    result = _process_node_labels(
        session=session,
        client=_FakeClient(labels={}),
        network=network,
    )

    assert result == {"0xAAA": "KnownLabel"}


def test_process_node_labels_with_missing_labels(session):
    network = {"nodes": ["0xBBB"]}
    result = _process_node_labels(
        session=session,
        client=_FakeClient(labels={"0xbbb": "NewLabel"}),
        network=network,
    )

    assert result == {"0xBBB": "NewLabel"}
    stored = label_crud.get_label(session, "0xBBB")
    assert stored is not None
    assert stored.label == "NewLabel"


def test_process_node_labels_missing_labels_not_found(session):
    network = {"nodes": ["0xCCC"]}
    result = _process_node_labels(
        session=session,
        client=_FakeClient(labels={}),
        network=network,
    )

    assert result == {"0xCCC": "0xCCC"}
    assert label_crud.get_label(session, "0xCCC") is None


def test_analyze_contract_dependencies_success_with_range(session, monkeypatch):
    fake_network = {
        "nodes": ["0xAAA", "0xBBB"],
        "edges": [{"source": "0xAAA", "target": "0xBBB", "types": {"CALL": 1}}],
    }

    monkeypatch.setattr(
        "src.api.services.analysis_service.AlliumClient",
        lambda _api_key: _FakeClient(network_range=fake_network),
    )

    result = analyze_contract_dependencies(
        session,
        "0xAAA",
        from_block="1",
        to_block="10",
    )

    assert result["nodes"]["0xAAA"] == "0xAAA"
    assert result["edges"][0]["risk"] == "Low"


def test_analyze_contract_dependencies_value_error(session):
    with pytest.raises(InputValidationError):
        analyze_contract_dependencies(session, "0xAAA", from_block="0", to_block="1000")


def test_analyze_contract_dependencies_internal_error_on_empty_network(session, monkeypatch):
    monkeypatch.setattr(
        "src.api.services.analysis_service.AlliumClient",
        lambda _api_key: _FakeClient(network_range=None),
    )

    with pytest.raises(InternalServerError):
        analyze_contract_dependencies(
            session,
            "0xAAA",
            from_block="1",
            to_block="10",
        )
