import { Link } from "react-router-dom";
import { CONDITION_LABELS, formatDate, formatPrice } from "../format";
import { imageUrl } from "../api";

export default function ListingCard({ listing }) {
  const cover = imageUrl(listing.images?.[0]?.url);
  return (
    <Link
      to={`/listing/${listing.id}`}
      className="group flex flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm transition hover:shadow-md"
    >
      <div className="aspect-square w-full bg-gray-100">
        {cover ? (
          <img
            src={cover}
            alt={listing.title}
            loading="lazy"
            className="h-full w-full object-cover transition group-hover:scale-[1.02]"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-4xl text-gray-300">📦</div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1 p-3">
        <p className="line-clamp-2 text-sm font-medium text-gray-900">{listing.title}</p>
        <p className="text-base font-bold text-indigo-600">
          {formatPrice(listing.price)}
          {listing.is_negotiable && (
            <span className="ml-1 text-xs font-normal text-gray-500">(negotiable)</span>
          )}
        </p>
        <div className="mt-auto flex items-center justify-between pt-1 text-xs text-gray-500">
          <span className="rounded bg-gray-100 px-1.5 py-0.5">
            {CONDITION_LABELS[listing.condition] ?? listing.condition}
          </span>
          <span>{formatDate(listing.created_at)}</span>
        </div>
        {listing.status === "sold" && (
          <span className="mt-1 w-fit rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800">
            Sold
          </span>
        )}
      </div>
    </Link>
  );
}
