from math import isfinite

import numpy as np
import numpy.typing as npt

TRADING_DAYS = 252
_MIN_POSITIVE_FLOAT = float(np.nextafter(0.0, 1.0))


class MonteCarloSimulator:
    """Geometric Brownian Motion price-path simulator (backtesting-spec.md §6).

    Notes:
        S_{t+1} = S_t * exp((mu - 0.5 sigma^2) dt + sigma sqrt(dt) Z). Because every factor is
        exp(...) > 0 and s0 > 0, all path values are strictly positive (§8 invariant #8).
        Cite Black & Scholes (1973). Seeded for determinism. Finite parameters and positive time
        increments are required; nonrepresentable upper paths raise rather than becoming evidence.
    """

    def simulate(
        self,
        s0: float,
        mu: float,
        sigma: float,
        n_steps: int,
        n_paths: int,
        seed: int | None = None,
        dt: float = 1.0 / TRADING_DAYS,
    ) -> npt.NDArray[np.float64]:
        if not all(isfinite(value) for value in (s0, mu, sigma, dt)):
            raise ValueError("simulation parameters must be finite")
        if s0 <= 0:
            raise ValueError("s0 must be > 0")
        if sigma < 0:
            raise ValueError("sigma must be >= 0")
        if n_steps < 1:
            raise ValueError("n_steps must be >= 1")
        if n_paths < 1:
            raise ValueError("n_paths must be >= 1")
        if dt <= 0:
            raise ValueError("dt must be > 0")

        try:
            with np.errstate(over="ignore", under="ignore", invalid="ignore"):
                drift = (mu - 0.5 * sigma**2) * dt
        except (OverflowError, FloatingPointError) as error:
            raise ValueError("GBM arithmetic must remain finite") from error
        if not isfinite(drift):
            raise ValueError("GBM arithmetic must remain finite")

        rng = np.random.default_rng(seed)
        shocks = rng.standard_normal((n_paths, n_steps))
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            diffusion = sigma * np.sqrt(dt) * shocks
            steps = np.exp(drift + diffusion)
            paths = np.empty((n_paths, n_steps + 1), dtype=np.float64)
            paths[:, 0] = s0
            paths[:, 1:] = s0 * np.cumprod(steps, axis=1)
        # Every factor is exp(...) > 0 in exact arithmetic, but a sufficiently extreme sigma over
        # many steps drives the true compounded value below float64's smallest representable
        # double, which np.cumprod floors to exactly 0.0 (FINDING-051/ADR-123). Clamp to the
        # smallest positive double so the class's own strict-positivity invariant (§8 #8) holds by
        # construction rather than silently failing at extreme-but-valid parameters. ADR-173
        # distinguishes this smallest subnormal from finfo.tiny, the smallest NORMAL float.
        paths = np.maximum(paths, _MIN_POSITIVE_FLOAT)
        if not np.isfinite(paths).all():
            raise ValueError("simulated paths must remain finite")
        return paths
