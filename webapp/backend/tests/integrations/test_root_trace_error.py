from src.api.integrations.crystal_clear_adapter import root_trace_error


def test_root_error_detected_in_erigon_mapping():
    resp = {"trace": [{"traceAddress": [], "error": "Reverted", "type": "call"}]}
    assert root_trace_error(resp) == "Reverted"


def test_root_error_in_plain_list():
    assert root_trace_error([{"traceAddress": [], "error": "out of gas"}]) == "out of gas"


def test_success_and_child_errors_are_not_reverts():
    ok = {"trace": [{"traceAddress": []}, {"traceAddress": [0], "error": "Reverted"}]}
    assert root_trace_error(ok) is None
    assert root_trace_error({"trace": []}) is None
    assert root_trace_error(None) is None
