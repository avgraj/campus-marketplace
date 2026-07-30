import { useEffect, useState } from "react";
import { api } from "../api";
import FilterBar from "../components/FilterBar";
import ListingGrid from "../components/ListingGrid";

const PAGE_SIZE = 12;

export default function Home() {
  const [filters, setFilters] = useState({ sort: "newest", page: 1 });
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) {
      if (v !== undefined && v !== "") params.set(k, v);
    }
    params.set("page_size", PAGE_SIZE);
    api
      .get(`/listings?${params}`)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filters]);

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      <FilterBar value={filters} onChange={setFilters} />

      {loading ? (
        <p className="py-16 text-center text-gray-500">Loading listings…</p>
      ) : error ? (
        <p className="py-16 text-center text-red-600">{error}</p>
      ) : (
        <>
          <p className="text-sm text-gray-500">
            {data.total} {data.total === 1 ? "listing" : "listings"}
          </p>
          <ListingGrid
            listings={data.items}
            emptyMessage="Try a different search or filter — or be the first to list something."
          />

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                disabled={data.page <= 1}
                onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
                className="rounded border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-40"
              >
                ← Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {data.page} of {totalPages}
              </span>
              <button
                disabled={data.page >= totalPages}
                onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
                className="rounded border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
