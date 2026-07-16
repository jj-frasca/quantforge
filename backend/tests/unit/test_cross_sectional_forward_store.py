"""Persistent cross-sectional forward book (ADR-025). JSON-file store for the frozen factor
positions + their latest forward score / lifecycle status — the portfolio-level analog of
JsonFilePaperPortfolio, reviewable in git."""

from datetime import UTC, datetime
from pathlib import Path

from app.research.cross_sectional.forward import CrossSectionalPosition
from app.research.cross_sectional.forward_store import JsonFileCrossSectionalBook

_NOW = datetime(2024, 6, 1, tzinfo=UTC)


def _position(strategy: str = "xs_momentum", status: str = "open") -> CrossSectionalPosition:
    return CrossSectionalPosition(
        strategy_name=strategy,
        parameters={"lookback": 126, "skip": 0, "quantile": 0.2},
        universe_symbols=["A", "B", "C"],
        cost_rate=0.001,
        frozen_at=_NOW,
        status=status,  # type: ignore[arg-type]
    )


def test_book_is_empty_before_first_write(tmp_path: Path) -> None:
    book = JsonFileCrossSectionalBook(tmp_path / "absent.json")
    assert book.positions() == []


def test_book_round_trips_through_the_file(tmp_path: Path) -> None:
    path = tmp_path / "xs_book.json"
    book = JsonFileCrossSectionalBook(path)
    book.save([_position("xs_momentum"), _position("xs_reversal", status="retired")])

    reloaded = JsonFileCrossSectionalBook(path)
    positions = reloaded.positions()
    assert [p.strategy_name for p in positions] == ["xs_momentum", "xs_reversal"]
    assert [p.status for p in positions] == ["open", "retired"]
    assert path.read_text().endswith("\n")  # trailing newline satisfies end-of-file-fixer
