import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import ListingGrid from "../components/ListingGrid";
import EmptyState from "../components/EmptyState";

// Manage your own listings: edit / mark sold / delete (plan §1 flow 4).
export default function MyListings() {
  const [listings, setListings] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get("/listings/mine").then(setListings).catch((e) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  if (error) return <EmptyState title="Couldn't load your listings" message={error} />;
  if (!listings) return <p className="py-16 text-center text-gray-500">Loading…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">My listings</h1>
        <Link
          to="/sell"
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          + New listing
        </Link>
      </div>
      <ListingGrid
        listings={listings}
        emptyTitle="You haven't listed anything yet"
        emptyMessage="Tap “New listing” to sell your first item."
      />
      <p className="text-xs text-gray-500">
        Open a listing to edit it, mark it sold, or delete it. Active listings expire after 14 days.
      </p>
    </div>
  );
}
