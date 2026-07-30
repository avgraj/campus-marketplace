import { useEffect, useState } from "react";
import { api } from "../api";
import { CONDITION_LABELS } from "../format";

const inputCls =
  "rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none";

// Search + category/price/condition filters + sort (plan §9).
export default function FilterBar({ value, onChange }) {
  const [categories, setCategories] = useState([]);
  const [q, setQ] = useState(value.q || "");

  useEffect(() => {
    api.get("/categories").then(setCategories).catch(() => setCategories([]));
  }, []);

  const set = (patch) => onChange({ ...value, ...patch, page: 1 });

  const submitSearch = (e) => {
    e.preventDefault();
    set({ q });
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-3">
      <form onSubmit={submitSearch} className="flex gap-2">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search books, cycles, furniture…"
          className={`${inputCls} flex-1`}
          aria-label="Search listings"
        />
        <button
          type="submit"
          className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Search
        </button>
      </form>

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={value.category || ""}
          onChange={(e) => set({ category: e.target.value || undefined })}
          className={inputCls}
          aria-label="Category"
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.slug}>
              {c.name}
            </option>
          ))}
        </select>

        <select
          value={value.condition || ""}
          onChange={(e) => set({ condition: e.target.value || undefined })}
          className={inputCls}
          aria-label="Condition"
        >
          <option value="">Any condition</option>
          {Object.entries(CONDITION_LABELS).map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>

        <input
          type="number"
          min="0"
          placeholder="Min ₹"
          value={value.min_price ?? ""}
          onChange={(e) => set({ min_price: e.target.value || undefined })}
          className={`${inputCls} w-24`}
          aria-label="Minimum price"
        />
        <input
          type="number"
          min="0"
          placeholder="Max ₹"
          value={value.max_price ?? ""}
          onChange={(e) => set({ max_price: e.target.value || undefined })}
          className={`${inputCls} w-24`}
          aria-label="Maximum price"
        />

        <select
          value={value.sort || "newest"}
          onChange={(e) => set({ sort: e.target.value })}
          className={`${inputCls} ml-auto`}
          aria-label="Sort by"
        >
          <option value="newest">Newest first</option>
          <option value="price_asc">Price: low to high</option>
          <option value="price_desc">Price: high to low</option>
        </select>
      </div>
    </div>
  );
}
