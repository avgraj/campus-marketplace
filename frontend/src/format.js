export const CONDITION_LABELS = {
  new: "New",
  like_new: "Like new",
  used: "Used",
  for_parts: "For parts",
};

export function formatPrice(price) {
  return `₹${Number(price).toLocaleString("en-IN")}`;
}

// Backend datetimes are naive UTC — append Z so Date parses them as UTC.
export function formatDate(iso) {
  const d = new Date(iso?.endsWith?.("Z") ? iso : `${iso}Z`);
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
