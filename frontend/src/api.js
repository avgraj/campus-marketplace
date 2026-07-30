// Fetch wrapper — always sends the session cookie (credentials: "include")
// and the X-Requested-With header the backend requires on mutations (CSRF
// defense-in-depth, plan §11).

const BASE = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Request failed (${status})`);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, formData } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: "include",
    headers: {
      "X-Requested-With": "fetch",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : formData,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : `Request failed (${res.status})`;
    throw new ApiError(res.status, detail);
  }
  return data;
}

// Images are served from the backend. Relative paths like /uploads/xxx.webp
// need the backend origin prepended so they work from the Vercel frontend.
export function imageUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${BASE}${path}`;
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  del: (path) => request(path, { method: "DELETE" }),
  upload: (path, formData) => request(path, { method: "POST", formData }),
};
