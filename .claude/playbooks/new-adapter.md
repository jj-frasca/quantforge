## Session: Implement [VENDOR] DataSourceAdapter

**Agent to invoke**: data-engineer
**Cold memory to read first**: .claude/context/data-contracts.md

**Entry criteria**:
- [ ] DataSourceAdapter ABC exists (backend/app/data/sources/base.py) with passing tests
- [ ] Canonical PriceBar / FundamentalData models exist
- [ ] DataQualityEngine exists (so ingested data can be gated)
- [ ] All previous tests passing

**Today's task**:
Implement [VENDOR]Adapter in backend/app/data/sources/[vendor].py.

It fetches raw [VENDOR] data and NORMALIZES at ingestion into canonical PriceBar
(UTC coercion enforced, Decimal OHLC, adj_factor applied exactly once). It must not
leak vendor-specific shapes downstream and must not normalize at query time (ADR-004/005).
API key (if any): [env var via app/config.py — never hardcoded].

**Files to read first**:
- backend/app/data/sources/base.py (the ABC contract)
- backend/app/data/sources/yfinance.py (reference adapter)
- backend/app/data/models/ (PriceBar/FundamentalData)

**Start in plan mode**: read the ABC and the yfinance adapter, confirm the field mapping,
propose the normalizer before writing code.

**Exit criteria**:
- [ ] Implements DataSourceAdapter fully; returns canonical models only
- [ ] UTC coercion enforced; invalid timestamps raise ValidationError (not a soft flag)
- [ ] adj_factor applied once; Decimal (not float) for prices
- [ ] Tests use synthetic fixtures; any live call is marked @pytest.mark.live
- [ ] adapter_version set (feeds ExperimentManifest reproducibility)
- [ ] Commit follows COMMIT_TEMPLATE.md
