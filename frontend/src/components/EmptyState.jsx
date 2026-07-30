// Designed empty/error states rather than blank screens (plan §16).
export default function EmptyState({ title, message, children }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-gray-300 bg-white px-6 py-16 text-center">
      <p className="text-lg font-semibold text-gray-700">{title}</p>
      {message && <p className="max-w-md text-sm text-gray-500">{message}</p>}
      {children}
    </div>
  );
}
