import {
  STRATEGY_CATEGORIES,
  type StrategyCatalog,
  type StrategyCategory,
  type StrategySchema,
} from '../../types/strategies'

/**
 * Group a catalog by `category` while preserving the canonical category order from
 * STRATEGY_CATEGORIES (Trend → Mean Reversion → Breakout → Combination). Within each
 * category, entries keep their catalog order — that's the order strategies were added,
 * which matches the order they appear in the backend catalog.py.
 *
 * Returns an array of `{ category, entries }` ready to feed into <optgroup>. Empty
 * categories are omitted so we don't render a useless heading.
 */
export function groupByCategory(
  catalog: StrategyCatalog,
): { category: StrategyCategory; entries: StrategySchema[] }[] {
  const buckets = new Map<StrategyCategory, StrategySchema[]>()
  for (const entry of catalog) {
    const list = buckets.get(entry.category) ?? []
    list.push(entry)
    buckets.set(entry.category, list)
  }
  return STRATEGY_CATEGORIES.filter((category) => buckets.has(category)).map((category) => ({
    category,
    entries: buckets.get(category) ?? [],
  }))
}
