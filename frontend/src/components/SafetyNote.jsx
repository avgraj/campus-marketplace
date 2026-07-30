// Visible meetup-safety note (plan §12) — costs nothing, standard for F2F.
export default function SafetyNote() {
  return (
    <aside className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
      <p className="font-semibold">Stay safe when meeting up</p>
      <ul className="mt-1 list-inside list-disc space-y-0.5">
        <li>Meet in a public campus spot, in daylight where possible</li>
        <li>Bring a friend for higher-value items</li>
        <li>Inspect the item before you pay</li>
      </ul>
    </aside>
  );
}
