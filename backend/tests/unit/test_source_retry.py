"""ADR-031: vendor throttling is an expected operating condition, not an error. `Retrier` wraps a
vendor call with bounded exponential backoff + FULL JITTER on the transient class (OSError — what
the adapters normalize vendor failures into) and enforces a minimum interval between calls. Every
clock/sleep/jitter source is injected so these tests never actually sleep."""

import pytest

from app.data.sources.retry import Retrier, RetryPolicy


class _Clock:
    """Monotonic fake: time only moves when something sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds

    def read(self) -> float:
        return self.now


def _retrier(policy: RetryPolicy, clock: _Clock, jitter: float = 1.0) -> Retrier:
    return Retrier(policy, sleeper=clock.sleep, clock=clock.read, jitter=lambda: jitter)


def test_default_policy_calls_once_and_never_sleeps() -> None:
    # The default MUST be today's behaviour so CI and every existing caller are unchanged.
    clock = _Clock()
    calls = []
    result = _retrier(RetryPolicy(), clock).call(lambda: calls.append(1) or "ok")
    assert result == "ok"
    assert len(calls) == 1
    assert clock.slept == []


def test_default_policy_propagates_the_error_without_retrying() -> None:
    clock = _Clock()
    calls = []

    def boom() -> str:
        calls.append(1)
        raise OSError("rate limited")

    with pytest.raises(OSError, match="rate limited"):
        _retrier(RetryPolicy(), clock).call(boom)
    assert len(calls) == 1


def test_retries_the_transient_class_and_returns_the_first_success() -> None:
    clock = _Clock()
    attempts = []

    def flaky() -> str:
        attempts.append(1)
        if len(attempts) < 3:
            raise OSError("Too Many Requests")
        return "bars"

    result = _retrier(RetryPolicy(attempts=4, base_delay=2.0), clock).call(flaky)
    assert result == "bars"
    assert len(attempts) == 3
    assert clock.slept == [2.0, 4.0]  # exponential: base * 2**n


def test_exhausting_the_attempts_reraises_the_last_error() -> None:
    clock = _Clock()
    attempts = []

    def always_throttled() -> str:
        attempts.append(1)
        raise OSError(f"throttled {len(attempts)}")

    with pytest.raises(OSError, match="throttled 3"):
        _retrier(RetryPolicy(attempts=3, base_delay=1.0), clock).call(always_throttled)
    assert len(attempts) == 3
    assert clock.slept == [1.0, 2.0]  # one sleep BETWEEN attempts, never after the last


def test_backoff_is_capped_by_max_delay() -> None:
    clock = _Clock()

    def always_throttled() -> str:
        raise OSError("throttled")

    with pytest.raises(OSError):
        _retrier(RetryPolicy(attempts=5, base_delay=10.0, max_delay=25.0), clock).call(
            always_throttled
        )
    assert clock.slept == [10.0, 20.0, 25.0, 25.0]  # 40 and 80 clamped to the cap


def test_full_jitter_scales_the_backoff_bound() -> None:
    # Ten shard jobs start against the vendor at the same instant; an unjittered schedule would
    # resynchronize every retry into the same moment and re-trigger the throttle. Full jitter
    # means the actual sleep is a uniform draw in [0, bound].
    clock = _Clock()

    def always_throttled() -> str:
        raise OSError("throttled")

    with pytest.raises(OSError):
        _retrier(RetryPolicy(attempts=3, base_delay=8.0), clock, jitter=0.25).call(always_throttled)
    assert clock.slept == [2.0, 4.0]  # 0.25 * [8, 16]


def test_a_data_verdict_is_not_retried() -> None:
    # ValueError/KeyError mean "this symbol's data is unusable" — a verdict, not a transient
    # condition. Retrying them would burn the shard's wall clock on names that can never succeed.
    clock = _Clock()
    attempts = []

    def bad_data() -> str:
        attempts.append(1)
        raise ValueError("no bars for DELISTED")

    with pytest.raises(ValueError, match="DELISTED"):
        _retrier(RetryPolicy(attempts=5, base_delay=1.0), clock).call(bad_data)
    assert len(attempts) == 1
    assert clock.slept == []


def test_min_interval_paces_successive_calls() -> None:
    clock = _Clock()
    retrier = _retrier(RetryPolicy(min_interval=1.5), clock)
    retrier.call(lambda: "a")
    retrier.call(lambda: "b")
    retrier.call(lambda: "c")
    assert clock.slept == [1.5, 1.5]  # first call is immediate; each later one waits the floor


def test_min_interval_only_waits_the_remainder_of_the_gap() -> None:
    clock = _Clock()
    retrier = _retrier(RetryPolicy(min_interval=2.0), clock)
    retrier.call(lambda: "a")
    clock.now += 1.25  # the hunt spent 1.25s backtesting the previous symbol
    retrier.call(lambda: "b")
    assert clock.slept == [pytest.approx(0.75)]


def test_min_interval_does_not_wait_when_the_gap_is_already_wide_enough() -> None:
    clock = _Clock()
    retrier = _retrier(RetryPolicy(min_interval=2.0), clock)
    retrier.call(lambda: "a")
    clock.now += 30.0
    retrier.call(lambda: "b")
    assert clock.slept == []


def test_min_interval_is_enforced_before_a_retry_too() -> None:
    # A backoff sleep already satisfies a shorter pacing floor — don't stack the two.
    clock = _Clock()
    attempts = []

    def flaky() -> str:
        attempts.append(1)
        if len(attempts) < 2:
            raise OSError("throttled")
        return "ok"

    _retrier(RetryPolicy(attempts=2, base_delay=5.0, min_interval=1.0), clock).call(flaky)
    assert clock.slept == [5.0]


def test_attempts_below_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        RetryPolicy(attempts=0)
