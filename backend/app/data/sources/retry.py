"""Bounded retry + pacing for vendor calls (ADR-031).

Vendor throttling is an expected operating condition, not an error: Yahoo rate-limits the shared
GitHub-runner egress IPs at the yfinance session bootstrap, so one hot minute can wipe out an entire
discovery shard. `Retrier` wraps a vendor call with exponential backoff and FULL JITTER on the
transient class, and enforces a floor on the interval between successive calls so a shard is polite
enough not to provoke the throttle in the first place.

Only `OSError` is treated as transient — that is what the adapters normalize every vendor and parse
failure into (`YFinanceAdapter.fetch_price_bars`). `ValueError` / `KeyError` are *data verdicts*
("this symbol has no usable bars") and are re-raised immediately; retrying them would burn the
shard's wall clock on names that can never succeed.

Defaults are a single attempt with no pacing — i.e. exactly the pre-ADR-031 behaviour, so CI and
every existing caller are unaffected until a driver opts in.
"""

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")

TRANSIENT = OSError


@dataclass(frozen=True)
class RetryPolicy:
    """attempts=1 + min_interval=0 is "no retry, no pacing" — the default everywhere except the
    cloud discovery drivers."""

    attempts: int = 1
    base_delay: float = 1.0
    max_delay: float = 60.0
    min_interval: float = 0.0

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("attempts must be at least 1")


CLOUD = RetryPolicy(attempts=4, base_delay=5.0, max_delay=60.0, min_interval=1.5)
"""The policy every scheduled cloud job uses (ADR-031). Four attempts backing off 5/10/20s under
full jitter recovers a throttled yfinance session bootstrap; the 1.5s floor between fetches keeps a
61-symbol shard from provoking the throttle at all. One definition so a calibration change from
observed yields lands everywhere at once."""


class Retrier:
    """Stateful across calls (it remembers when the last one started) so `min_interval` paces a
    whole universe sweep, not just the retries within one symbol. Not thread-safe — the shards are
    separate processes."""

    def __init__(
        self,
        policy: RetryPolicy,
        *,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self._policy = policy
        self._sleep = sleeper
        self._clock = clock
        self._jitter = jitter
        self._last_call: float | None = None

    def call(self, fn: Callable[[], T]) -> T:
        policy = self._policy
        for attempt in range(policy.attempts):
            self._pace()
            self._last_call = self._clock()
            try:
                return fn()
            except TRANSIENT:
                if attempt == policy.attempts - 1:
                    raise
                bound = min(policy.max_delay, policy.base_delay * 2**attempt)
                self._sleep(bound * self._jitter())
        raise AssertionError("unreachable")  # pragma: no cover - the loop always returns or raises

    def _pace(self) -> None:
        if self._last_call is None or self._policy.min_interval <= 0:
            return
        remaining = self._policy.min_interval - (self._clock() - self._last_call)
        if remaining > 0:
            self._sleep(remaining)
