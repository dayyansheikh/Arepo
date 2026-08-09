export const ALL_CATEGORY = "All" as const;

export const CATEGORY_FILTERS = [
  ALL_CATEGORY,
  "Geopolitics / War",
  "Economics / Macro",
  "Commodities",
  "Politics / Elections",
  "Crypto",
  "Technology / Business",
  "Sports",
  "Entertainment / Culture",
] as const;

export type CategoryFilter = (typeof CATEGORY_FILTERS)[number];

export function categoryTestId(category: CategoryFilter): string {
  return category.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
