from src.indicators import add_indicators
from src.signals import add_signal_scores, latest_signal
from tests.test_indicators import sample_frame


def test_signal_score_has_expected_range():
    frame = add_signal_scores(add_indicators(sample_frame()))
    assert frame["long_score"].between(0, 4).all()
    assert frame["short_score"].between(0, 4).all()
    signal = latest_signal(frame, allow_short=True)
    assert signal.decision in {"LONG SETUP", "SHORT SETUP", "NEUTRAL / WAIT", "EXIT / AVOID"}
    assert signal.direction in {"LONG", "SHORT", "NONE"}
    assert len(signal.reasons) >= 4
