import { useRef, useState } from "react";
import imageCompression from "browser-image-compression";
import { api } from "../api";

// Client-side compress → server validates/re-encodes/strips EXIF (plan §7).
const MAX_IMAGES = 5;

export default function ImageUploader({ urls, onChange }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const handleFiles = async (files) => {
    setError("");
    const remaining = MAX_IMAGES - urls.length;
    const selected = Array.from(files).slice(0, remaining);
    if (files.length > remaining) {
      setError(`You can attach at most ${MAX_IMAGES} photos.`);
    }
    if (!selected.length) return;

    setBusy(true);
    try {
      for (const file of selected) {
        // Keep free storage quota and upload times sane before the bytes
        // even leave the browser.
        const compressed = await imageCompression(file, {
          maxSizeMB: 1,
          maxWidthOrHeight: 1600,
          useWebWorker: true,
        });
        const formData = new FormData();
        formData.append("file", compressed, file.name);
        const { url } = await api.upload("/uploads/image", formData);
        onChange((prev) => [...prev, url]);
      }
    } catch (e) {
      setError(e.message || "Upload failed — please try a different photo.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const removeAt = (idx) => onChange((prev) => prev.filter((_, i) => i !== idx));

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        {urls.map((url, idx) => (
          <div key={url} className="relative h-24 w-24 overflow-hidden rounded border border-gray-200">
            <img src={url} alt={`Upload ${idx + 1}`} className="h-full w-full object-cover" />
            <button
              type="button"
              onClick={() => removeAt(idx)}
              aria-label={`Remove photo ${idx + 1}`}
              className="absolute right-1 top-1 rounded-full bg-black/60 px-1.5 text-xs text-white hover:bg-black/80"
            >
              ✕
            </button>
          </div>
        ))}

        {urls.length < MAX_IMAGES && (
          <button
            type="button"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
            className="flex h-24 w-24 items-center justify-center rounded border border-dashed border-gray-300 text-2xl text-gray-400 hover:border-indigo-400 hover:text-indigo-500 disabled:opacity-50"
          >
            {busy ? "…" : "+"}
          </button>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={(e) => handleFiles(e.target.files)}
      />
      <p className="mt-1 text-xs text-gray-500">
        {urls.length}/{MAX_IMAGES} photos — at least 1 required. Photos are compressed and stripped
        of location metadata before publishing.
      </p>
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  );
}
