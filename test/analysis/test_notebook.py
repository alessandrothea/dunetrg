import pytest

from dunetrg.analysis.notebook import StopExecution, stop


def test_stop_raises_stop_execution():
    with pytest.raises(StopExecution):
        stop("because")


def test_reason_is_the_exception_message():
    with pytest.raises(StopExecution) as excinfo:
        stop("because")
    print(f"message: {str(excinfo.value)!r}, expected: 'because'")
    assert str(excinfo.value) == "because"


def test_traceback_is_replaced_by_a_one_line_message():
    # IPython renders an exception through _render_traceback_; a short list
    # keeps the notebook output free of a traceback.
    rendered = StopExecution("because")._render_traceback_()
    print(f"rendered: {rendered}, expected one line mentioning the reason")
    assert rendered == ["Execution stopped: because"]

    rendered = StopExecution()._render_traceback_()
    print(f"rendered (no reason): {rendered}, expected: ['Execution stopped.']")
    assert rendered == ["Execution stopped."]
