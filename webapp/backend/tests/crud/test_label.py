from datetime import datetime

from src.api.crud.label import (
    create_label,
    get_all_labels,
    get_label,
    get_labels,
    update_label,
)
from src.api.models.label import AddressList, LabelCreate, LabelUpdate


def test_create_and_get_label(session):
    # Create a label
    label_data = LabelCreate(address="0xABC123", label="Token A")
    created = create_label(session, label_data)

    assert created.address == "0xABC123"
    assert created.label == "Token A"

    # Fetch by address
    fetched = get_label(session, "0xABC123")
    assert fetched is not None
    assert fetched.address == "0xABC123"
    assert fetched.label == "Token A"

    # Fetch non-existent label returns None
    non_existent = get_label(session, "0xDEADBEF")
    assert non_existent is None


def test_get_all_labels(session):
    labels_data = [
        LabelCreate(address="0xAAA", label="Token A"),
        LabelCreate(address="0xBBB", label="Token B"),
    ]
    for data in labels_data:
        create_label(session, data)

    all_labels = get_all_labels(session)
    assert len(all_labels) == 2
    assert all_labels["0xAAA"] == "Token A"
    assert all_labels["0xBBB"] == "Token B"


def test_update_label(session):
    # Create a label
    label_data = LabelCreate(address="0x12345", label="Old Token")
    create_label(session, label_data)

    # Update label
    update_data = LabelUpdate(label="New Token")
    updated = update_label(session, "0x12345", update_data)

    assert updated.label == "New Token"
    assert updated.last_updated > updated.__dict__.get(
        "date_added", datetime.min
    )

    # Update non-existent label returns None
    result = update_label(session, "0xDEAD", update_data)
    assert result is None


def test_get_labels_multiple(session):
    labels_data = [
        LabelCreate(address="0xAAA", label="Token A"),
        LabelCreate(address="0xBBB", label="Token B"),
        LabelCreate(address="0xCCC", label="Token C"),
    ]
    for data in labels_data:
        create_label(session, data)

    addresses = AddressList(
        addresses=["0xAAA", "0xCCC", "0xDDD"]
    )  # one non-existent
    result = get_labels(session, addresses)

    assert isinstance(result, dict)
    assert len(result) == 2  # only existing addresses returned
    assert result["0xAAA"] == "Token A"
    assert result["0xCCC"] == "Token C"
    assert "0xDDD" not in result
