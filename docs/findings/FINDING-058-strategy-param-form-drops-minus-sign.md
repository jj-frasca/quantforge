# FINDING-058: Typing a negative parameter value can be wiped mid-keystroke

- **Severity:** Medium
- **Status:** Resolved by ADR-130
- **Found:** 2026-09-24, autonomous session 106 (cold-directory audit of `frontend/src/features/
  strategies/`, `StrategyParamForm.tsx` cold since 2026-06-18)
- **Affects:** `StrategyParamForm` (`frontend/src/features/strategies/StrategyParamForm.tsx`),
  consumed by `BacktestResultsPage` and `CompareConfigsPage`

## Finding

`StrategyParamForm` renders one `<input type="number">` per catalog `ParamSchema`, fully controlled
by React: `value={Number.isFinite(stored) ? stored : ''}`, where `stored` comes from parsing the
input's raw text on every keystroke. The Williams %R strategy's `oversold`/`overbought` parameters
(`backend/app/research/strategies/catalog.py`) are the only catalog params whose entire valid range
is negative (defaults -80/-20, minimums -99/-49) — every usable value starts with a `-`.

`parseFloat('-')` (and `parseInt('-', 10)`) is `NaN`, so the moment a user types a lone `-` as the
first character of a negative value, the parsed `stored` value becomes `NaN`, `display` falls back
to `''`, and React's controlled re-render reassigns the input's `value` DOM property to `''` on the
very next render. An `input[type=number]`'s value-sanitization algorithm — confirmed live against a
real Chrome for Testing build via Playwright, not inferred from jsdom alone — visibly erases
whatever the user had just typed the moment script assigns an unparseable string to `.value`; a
plain, uncontrolled number input does NOT lose the character (the browser keeps showing it via an
internal "user interface value" distinct from the script-readable IDL `.value`, which legitimately
reads `""` for an in-progress invalid number in both cases). So the bug is specifically that this
component's *controlled* `value` prop forces that erasing reassignment on every keystroke, including
while the field is focused and being actively typed into.

Net effect: typing `-85` into the oversold/overbought fields character-by-character can flash the
field back to empty after the first keystroke. In practice a real user's next keystroke still lands
correctly (confirmed the final committed value ends up right either way), so this is a visible
flicker/papercut rather than data loss — but it is a real, reachable UX defect on the one strategy
whose params are unusable without typing a negative number.

## Verification note

jsdom cannot represent the distinction this bug hinges on: a bare `<input type="number">` with zero
React involvement also reads `.value === ""` immediately after typing `-` in jsdom AND in real
Chromium (confirmed both). What differs is only observable via real rendering — verified directly
with Playwright/Chrome for Testing this session (screenshot before/after a script-level
`el.value = ''` assignment shows the visible `-` character disappearing). No jsdom-expressible unit
assertion for the flicker itself was found; `StrategyParamForm.test.tsx` documents this explicitly
rather than silently shipping a fix with an assertion that doesn't actually exercise it.

## Reproduction (real browser, Playwright)

```
navigate to data:text/html,<input type="number">
click the input, press "-"           -> screenshot shows "-" rendered; el.value reads ""
evaluate: el.value = ''              -> screenshot shows the "-" is now gone
```

The second step is exactly what the old controlled `value={display}` prop did on every keystroke
whose parse produced `NaN`.
