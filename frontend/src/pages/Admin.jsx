import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import EmptyState from "../components/EmptyState";
import { formatDate, formatPrice } from "../format";

// Minimal moderation queue (plan §12): reported listings → dismiss, remove,
// or ban the seller.
export default function Admin() {
  const [reports, setReports] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get("/admin/reports").then(setReports).catch((e) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  const act = async (fn) => {
    setError("");
    try {
      await fn();
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  if (error && !reports) return <EmptyState title="Couldn't load reports" message={error} />;
  if (!reports) return <p className="py-16 text-center text-gray-500">Loading…</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Moderation queue</h1>
      {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {reports.length === 0 ? (
        <EmptyState title="All clear" message="No pending reports right now." />
      ) : (
        <ul className="space-y-3">
          {reports.map((r) => (
            <li
              key={r.id}
              className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-4 sm:flex-row"
            >
              <Link to={`/listing/${r.listing.id}`} className="flex flex-1 gap-3">
                {r.listing.images?.[0] && (
                  <img
                    src={r.listing.images[0].url}
                    alt=""
                    className="h-20 w-20 rounded border border-gray-200 object-cover"
                  />
                )}
                <div>
                  <p className="font-medium text-indigo-700 hover:underline">{r.listing.title}</p>
                  <p className="text-sm text-gray-600">{formatPrice(r.listing.price)}</p>
                  <p className="mt-1 text-sm text-red-700">
                    Report: “{r.reason}” — by {r.reporter.first_name}
                    {r.reporter.telegram_username ? ` (@${r.reporter.telegram_username})` : ""},{" "}
                    {formatDate(r.created_at)}
                  </p>
                </div>
              </Link>

              <div className="flex items-start gap-2">
                <button
                  onClick={() => act(() => api.post(`/admin/reports/${r.id}/dismiss`))}
                  className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100"
                >
                  Dismiss
                </button>
                <button
                  onClick={() => act(() => api.post(`/admin/listings/${r.listing.id}/remove`))}
                  className="rounded bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700"
                >
                  Remove listing
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
