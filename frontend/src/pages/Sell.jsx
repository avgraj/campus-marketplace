import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import ImageUploader from "../components/ImageUploader";
import { CONDITION_LABELS } from "../format";

const inputCls =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none";

// Create form (/sell) and edit form (/sell?edit=<id>) in one — plan §6 rules
// are enforced server-side; this page mirrors them for fast feedback.
export default function Sell() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editId = searchParams.get("edit");
  const { user } = useAuth();

  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({
    title: "",
    description: "",
    price: "",
    category_id: "",
    condition: "used",
    is_negotiable: false,
  });
  const [imageUrls, setImageUrls] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(!editId);

  useEffect(() => {
    api.get("/categories").then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    if (!editId) return;
    api
      .get(`/listings/${editId}`)
      .then((l) => {
        setForm({
          title: l.title,
          description: l.description,
          price: String(l.price),
          category_id: String(l.category.id),
          condition: l.condition,
          is_negotiable: l.is_negotiable,
        });
        setImageUrls(l.images.map((i) => i.url));
        setLoaded(true);
      })
      .catch((e) => setError(e.message));
  }, [editId]);

  const set = (field) => (e) =>
    setForm((f) => ({ ...f, [field]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!imageUrls.length) {
      setError("Add at least one photo.");
      return;
    }
    setBusy(true);
    const payload = {
      title: form.title.trim(),
      description: form.description.trim(),
      price: Number(form.price),
      category_id: Number(form.category_id),
      condition: form.condition,
      is_negotiable: form.is_negotiable,
      image_urls: imageUrls,
    };
    try {
      const saved = editId
        ? await api.put(`/listings/${editId}`, payload)
        : await api.post("/listings", payload);
      navigate(`/listing/${saved.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  if (!loaded) return <p className="py-16 text-center text-gray-500">Loading…</p>;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-4 text-2xl font-bold">{editId ? "Edit listing" : "Sell an item"}</h1>

      {!user?.telegram_username && (
        <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          You need a public Telegram <strong>@username</strong> to publish — buyers contact you
          through it. Set one in Telegram → Settings → Username.
        </p>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-gray-200 bg-white p-5">
        <div>
          <label htmlFor="title" className="mb-1 block text-sm font-medium">
            Title
          </label>
          <input
            id="title"
            value={form.title}
            onChange={set("title")}
            required
            minLength={5}
            maxLength={120}
            placeholder="e.g. Engineering Mathematics textbook (4th ed.)"
            className={inputCls}
          />
        </div>

        <div>
          <label htmlFor="description" className="mb-1 block text-sm font-medium">
            Description
          </label>
          <textarea
            id="description"
            value={form.description}
            onChange={set("description")}
            required
            minLength={20}
            maxLength={1000}
            rows={4}
            placeholder="Condition, age, reason for selling, pickup spot…"
            className={inputCls}
          />
          <p className="mt-1 text-xs text-gray-500">{form.description.length}/1000</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="price" className="mb-1 block text-sm font-medium">
              Price (₹)
            </label>
            <input
              id="price"
              type="number"
              min="1"
              max="1000000"
              step="0.01"
              value={form.price}
              onChange={set("price")}
              required
              className={inputCls}
            />
          </div>
          <div>
            <label htmlFor="category" className="mb-1 block text-sm font-medium">
              Category
            </label>
            <select id="category" value={form.category_id} onChange={set("category_id")} required className={inputCls}>
              <option value="">Choose…</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="condition" className="mb-1 block text-sm font-medium">
              Condition
            </label>
            <select id="condition" value={form.condition} onChange={set("condition")} required className={inputCls}>
              {Object.entries(CONDITION_LABELS).map(([k, label]) => (
                <option key={k} value={k}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-end gap-2 pb-2 text-sm">
            <input type="checkbox" checked={form.is_negotiable} onChange={set("is_negotiable")} />
            Price is negotiable
          </label>
        </div>

        <div>
          <span className="mb-1 block text-sm font-medium">Photos</span>
          <ImageUploader urls={imageUrls} onChange={setImageUrls} />
        </div>

        {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded bg-indigo-600 py-2.5 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {busy ? "Publishing…" : editId ? "Save changes" : "Publish listing"}
        </button>
      </form>
    </div>
  );
}
