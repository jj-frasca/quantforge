# ADR-130: Keep strategy param inputs uncontrolled while focused

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 106
- **Resolves:** FINDING-058

## Context

`StrategyParamForm`'s numeric inputs are fully React-controlled, deriving `value` from the parsed
numeric state on every keystroke. Williams %R's `oversold`/`overbought` params are the only catalog
params whose entire valid range is negative, so every usable value there starts with `-`. A lone `-`
parses to `NaN`, and the controlled re-render then reassigns the input's `.value` to `''` — which a
real `input[type=number]` visibly enacts by erasing whatever the user just typed, confirmed live
against Chrome for Testing (see FINDING-058). The field flickers empty mid-typing on the one
strategy where typing a negative number is mandatory.

## Options Considered

1. **Make the input uncontrolled (`defaultValue` + a ref) and use a `useEffect` to push
   externally-driven value changes (preset clicks, strategy switch) into the DOM, gated on
   `document.activeElement !== inputEl` so it never fights the browser's own in-progress typing
   state.**
   - Pro: keeps `type="number"` and its native `min`/`max`/`step` — currently the *only* client-side
     range enforcement in this form (`allParamsValid` only checks `Number.isFinite`, not bounds).
     Small, local diff; no change to the parse/validation logic or the wire format.
   - Con: one more indirection (ref + effect) than a plain controlled input.
2. **Switch the input to `type="text"` with `inputMode="decimal"`/`"numeric"`.**
   - Con: loses native `min`/`max`/`step` browser-level constraint validation entirely (would need a
     new client-side bounds check to replace it — currently nothing does this), and changes
     `jest-dom`'s `toHaveValue` semantics for every existing consumer test
     (`BacktestResultsPage.test.tsx` asserts `toHaveValue(20)` as a number, which relies on
     `type="number"` typing). Bigger blast radius for a narrower win.
3. **Track the raw text in local component state (`useState<string | null>`) instead of deriving
   `display` from the parsed value, still passing it through the `value` prop.**
   - Con: tried first; does not work. React still reassigns `.value` via the controlled `value` prop
     on every render regardless of focus, so the sanitizing reassignment (and the visible erase)
     still happens — confirmed by reproducing the bug with this approach in place before abandoning
     it for option 1.

Chose option 1: smallest change that actually stops the erasing reassignment, no loss of existing
native range enforcement, no change to any consumer's test assertions.

## Decision

`ParamInput` (extracted from `StrategyParamForm`'s inline map body) uses `defaultValue` instead of
`value`, keeps a `ref` to the `<input>`, and syncs the DOM node's `.value` from the `value` prop only
inside a `useEffect` gated on `document.activeElement !== inputRef.current` — i.e., only for
externally-driven changes (a preset click, a strategy switch reusing the same param name), never as
a reaction to the field's own `onChange` while it still has focus. The parse/validation logic
(`parseInt`/`parseFloat`, `NaN` for an empty field) is unchanged.

## Consequences

- Typing a negative value into Williams %R's oversold/overbought fields no longer flickers empty
  mid-entry (verified live with Playwright against Chrome for Testing — see FINDING-058).
- Preset-click and strategy-switch value updates still land correctly (the effect still fires
  whenever the field isn't the one being edited) — `BacktestResultsPage.test.tsx`'s preset and
  strategy-switch tests pass unmodified.
- Native `min`/`max`/`step` browser-level validation is unchanged.
- No jsdom-expressible unit test exists for the exact flicker mechanism (jsdom's `input[type=number]`
  can't represent the "user interface value vs. IDL value" distinction the bug and fix both hinge
  on — confirmed the same read of `""` happens in jsdom for both the buggy and fixed code). The
  existing end-to-end "type -85, the committed value is -85" test still guards the basic behavior;
  `StrategyParamForm.test.tsx` documents the gap explicitly rather than shipping a hollow assertion.

## Reversal

Revert `ParamInput` to a single controlled `<input value={display} onChange={...} />` deriving
`display` from `Number.isFinite(stored) ? stored : ''`. Not recommended — reintroduces
FINDING-058's flicker on Williams %R's oversold/overbought fields.
