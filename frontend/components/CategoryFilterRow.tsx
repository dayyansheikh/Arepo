import {
  CATEGORY_FILTERS,
  categoryTestId,
  type CategoryFilter,
} from "@/lib/categories";

export function CategoryFilterRow({
  value,
  onChange,
  label = "Category",
}: {
  value: string;
  onChange: (category: CategoryFilter) => void;
  label?: string;
}) {
  return (
    <div className="min-w-0 space-y-1.5" data-testid="category-filter">
      <div className="text-[12px] font-medium text-arepo-muted">{label}</div>
      <div className="w-full min-w-0 overflow-x-auto overscroll-x-contain pb-1">
        <div
          className="flex w-max min-w-full gap-1 border-b border-arepo-border"
          role="group"
          aria-label={label}
        >
          {CATEGORY_FILTERS.map((category) => {
            const active = value === category;
            return (
              <button
                key={category}
                type="button"
                aria-pressed={active}
                data-testid={`category-${categoryTestId(category)}`}
                onClick={() => onChange(category)}
                className={`focus-ring -mb-px shrink-0 border-b-2 px-2.5 py-2 text-[13px] font-medium transition-colors ${
                  active
                    ? "border-arepo-accent text-arepo-accentActive"
                    : "border-transparent text-arepo-muted hover:text-arepo-ink"
                }`}
              >
                {category}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
