import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, imageUrl } from "../api";
import { useAuth } from "../context/AuthContext";
import EmptyState from "../components/EmptyState";
import SafetyNote from "../components/SafetyNote";
import { CONDITION_LABELS, formatDate, formatPrice } from "../format";

export default function ListingDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [listing, setListing] = useState(null);
  const [error, setError] = useState("");
  const [activeImage, setActiveImage] = useState(0);
  const [reportSent, setReportSent] = useState(false);

  useEffect(() => {
    api
      .get(`/listings/${id}`)
      .then((l) => {
        setListing(l);
        // Free virality when a listing link is shared (plan §16, OG tags).
        document.title = `${l.title} — Campus Marketplace`;
        document
          .querySelector('meta[property="og:title"]')
          ?.setAttribute("content", `${l.title} (${formatPrice(l.price)})`);
        document
          .querySelector('meta[property="og:description"]')
          ?.setAttribute("content", l.description.slice(0, 160));
      })
      .catch((e) => setError(e.message));
    return () => {
      document.title = "Campus Marketplace";
    };
  }, [id]);

  const [copied, setCopied] = useState(false);

  // Telegram contact (plan §8). Deep links are unreliable on mobile — try
  // native app first, fall back to web, and copy username as a last resort.
  const telegramContact = useMemo(() => {
    if (!listing?.seller?.telegram_username) return null;
    const text = `Hi! I'm interested in your listing "${listing.title}" (${formatPrice(
      listing.price
    )}) on Campus Marketplace — is it still available?`;
    return {
      username: listing.seller.telegram_username,
      text,
      webUrl: `https://t.me/${listing.seller.telegram_username}?text=${encodeURIComponent(text)}`,
      appUrl: `tg://resolve?domain=${listing.seller.telegram_username}&text=${encodeURIComponent(text)}`,
    };
  }, [listing]);

  const handleContact = () => {
    if (!telegramContact) return;
    navigator.clipboard.writeText(`@${telegramContact.username}`).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
    window.location.href = telegramContact.appUrl;
    setTimeout(() => {
      window.open(telegramContact.webUrl, "_blank");
    }, 800);
  };

  if (error) {
    return <EmptyState title="Listing unavailable" message={error} />;
  }
  if (!listing) {
    return <p className="py-16 text-center text-gray-500">Loading…</p>;
  }

  const handleReport = async () => {
    const reason = window.prompt("Why are you reporting this listing?");
    if (!reason) return;
    try {
      await api.post(`/listings/${id}/report`, { reason });
      setReportSent(true);
    } catch (e) {
      alert(e.message);
    }
  };

  const handleMarkSold = async () => {
    await api.post(`/listings/${listing.id}/mark-sold`);
    setListing((l) => ({ ...l, status: "sold" }));
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete this listing? This cannot be undone.")) return;
    await api.del(`/listings/${listing.id}`);
    navigate("/my-listings");
  };

  const images = listing.images ?? [];

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Gallery */}
      <div>
        <div className="aspect-square overflow-hidden rounded-lg border border-gray-200 bg-white">
          {images.length ? (
            <img
              src={imageUrl(images[activeImage]?.url)}
              alt={listing.title}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-6xl text-gray-300">📦</div>
          )}
        </div>
        {images.length > 1 && (
          <div className="mt-2 flex gap-2">
            {images.map((img, idx) => (
              <button
                key={img.id}
                onClick={() => setActiveImage(idx)}
                className={`h-16 w-16 overflow-hidden rounded border ${
                  idx === activeImage ? "border-indigo-500" : "border-gray-200"
                }`}
                aria-label={`Photo ${idx + 1}`}
              >
                <img src={imageUrl(img.url)} alt="" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Details */}
      <div className="space-y-4">
        <div>
          <div className="flex items-start justify-between gap-3">
            <h1 className="text-2xl font-bold">{listing.title}</h1>
            {listing.status === "sold" && (
              <span className="rounded bg-amber-100 px-2 py-1 text-sm font-medium text-amber-800">
                Sold
              </span>
            )}
          </div>
          <p className="mt-1 text-3xl font-bold text-indigo-600">
            {formatPrice(listing.price)}
            {listing.is_negotiable && (
              <span className="ml-2 text-sm font-normal text-gray-500">negotiable</span>
            )}
          </p>
        </div>

        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-600">
          <div>
            <dt className="inline font-medium">Condition: </dt>
            <dd className="inline">{CONDITION_LABELS[listing.condition]}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Category: </dt>
            <dd className="inline">{listing.category.name}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Listed: </dt>
            <dd className="inline">{formatDate(listing.created_at)}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Seller: </dt>
            <dd className="inline">{listing.seller.first_name}</dd>
          </div>
        </dl>

        <p className="whitespace-pre-line rounded-lg border border-gray-200 bg-white p-4 text-sm leading-relaxed">
          {listing.description}
        </p>

        {/* Contact — gated behind login (plan §8) */}
        {listing.is_mine ? (
          <div className="flex flex-wrap gap-2">
            <Link
              to={`/sell?edit=${listing.id}`}
              className="rounded border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-100"
            >
              Edit
            </Link>
            {listing.status === "active" && (
              <button
                onClick={handleMarkSold}
                className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
              >
                Mark as sold
              </button>
            )}
            <button
              onClick={handleDelete}
              className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        ) : user ? (
          telegramContact ? (
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleContact}
                className="inline-flex items-center gap-2 rounded bg-sky-500 px-5 py-2.5 font-medium text-white hover:bg-sky-600"
              >
                <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current" aria-hidden>
                  <path d="M9.04 15.5 8.9 19c.4 0 .57-.17.78-.38l1.87-1.79 3.88 2.85c.71.4 1.22.2 1.4-.66L19.4 5.98c.23-1.04-.38-1.45-1.07-1.2L3.9 11.03c-1.02.4-1 .97-.17 1.23l3.7 1.15 8.59-5.4c.4-.27.78-.12.47.15l-6.45 5.83z" />
                </svg>
                Message seller on Telegram
              </button>
              {copied && (
                <span className="text-xs text-green-600">Username copied to clipboard</span>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500">This seller can't be contacted right now.</p>
          )
        ) : (
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-900">
            <Link to="/login" className="font-semibold underline">
              Log in with Telegram
            </Link>{" "}
            to contact the seller. Browsing is public — contact stays inside the community.
          </div>
        )}

        <SafetyNote />

        {user && !listing.is_mine && (
          <button
            onClick={handleReport}
            disabled={reportSent}
            className="text-sm text-gray-500 underline hover:text-red-600 disabled:no-underline"
          >
            {reportSent ? "Reported — thanks, a moderator will look at it." : "Report this listing"}
          </button>
        )}
      </div>
    </div>
  );
}
