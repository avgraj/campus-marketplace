import ListingCard from "./ListingCard";
import EmptyState from "./EmptyState";

export default function ListingGrid({ listings, emptyTitle = "No listings found", emptyMessage }) {
  if (!listings.length) {
    return <EmptyState title={emptyTitle} message={emptyMessage} />;
  }
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {listings.map((l) => (
        <ListingCard key={l.id} listing={l} />
      ))}
    </div>
  );
}
