from src.backtest import run_backtest
from src.indicators import add_indicators
from src.signals import add_signal_scores
from tests.test_indicators import sample_frame


def test_backtest_returns_finite_core_metrics():
    frame = add_signal_scores(add_indicators(sample_frame(300)))
    result = run_backtest(frame, leverage=2, allow_short=True)
    assert result.trades >= 0
    assert -100 <= result.max_drawdown_pct <= 0
    assert result.equity_curve.iloc[-1] > 0
