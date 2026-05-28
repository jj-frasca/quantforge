import numpy as np
import numpy.typing as npt

TRADING_DAYS = 252


class MonteCarloSimulator:
    """Geometric Brownian Motion price-path simulator (backtesting-spec.md §6).

    Notes:
        S_{t+1} = S_t * exp((mu - 0.5 sigma^2) dt + sigma sqrt(dt) Z). Because every factor is
        exp(...) > 0 and s0 > 0, all path values are strictly positive (§8 invariant #8).
        Cite Black & Scholes (1973). Seeded for determinism.
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
        if s0 <= 0:
            raise ValueError("s0 must be > 0")
        if sigma < 0:
            raise ValueError("sigma must be >= 0")
        if n_steps < 1:
            raise ValueError("n_steps must be >= 1")
        if n_paths < 1:
            raise ValueError("n_paths must be >= 1")

        rng = np.random.default_rng(seed)
        shocks = rng.standard_normal((n_paths, n_steps))
        drift = (mu - 0.5 * sigma**2) * dt
        diffusion = sigma * np.sqrt(dt) * shocks
        steps = np.exp(drift + diffusion)

        paths = np.empty((n_paths, n_steps + 1), dtype=np.float64)
        paths[:, 0] = s0
        paths[:, 1:] = s0 * np.cumprod(steps, axis=1)
        return paths
