import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { user, config, requestCode, verifyCode, devLogin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || "/";

  const [step, setStep] = useState("username"); // "username" | "code" | "success"
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [devName, setDevName] = useState("devuser");
  const [devAdmin, setDevAdmin] = useState(false);

  if (user) {
    navigate(from, { replace: true });
    return null;
  }

  const botLink = config.telegram_bot_username
    ? `https://t.me/${config.telegram_bot_username}`
    : null;

  const handleSendCode = async (e) => {
    e.preventDefault();
    if (!username.trim()) return;
    setError("");
    setBusy(true);
    try {
      await requestCode(username.trim());
      setStep("code");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleVerifyCode = async (e) => {
    e.preventDefault();
    if (!code.trim()) return;
    setError("");
    setBusy(true);
    try {
      const me = await verifyCode(username.trim(), code.trim());
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleDev = async () => {
    setError("");
    setBusy(true);
    try {
      await devLogin(devName, devAdmin);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const inputCls =
    "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none";

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
        <h1 className="text-2xl font-bold">Log in</h1>
        <p className="mt-2 text-sm text-gray-600">
          Your identity comes from Telegram — the bot sends you a one-time code.
        </p>

        <div className="mt-4 rounded-lg border border-indigo-100 bg-indigo-50 p-3 text-left text-xs text-indigo-900">
          <strong>First time?</strong> Open{" "}
          <a
            href={botLink || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono font-semibold underline"
          >
            @{config.telegram_bot_username || "cmpmarketplace_bot"}
          </a>{" "}
          in Telegram and press <strong>Start</strong> (one tap). Then come back here.
        </div>

        <form onSubmit={handleSendCode} className={`mt-5 space-y-3 ${step === "code" ? "hidden" : ""}`}>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Your Telegram username"
            className={inputCls}
            required
            autoFocus
            autoComplete="username"
          />
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded bg-indigo-600 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {busy ? "Sending…" : "Send code via Telegram"}
          </button>
        </form>

        <form onSubmit={handleVerifyCode} className={`mt-5 space-y-3 ${step === "code" ? "" : "hidden"}`}>
          <p className="text-sm text-gray-600">
            Code sent to <strong>@{username}</strong> in Telegram. Enter it below.
          </p>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="6-digit code"
            maxLength={6}
            className={inputCls + " text-center text-lg tracking-widest"}
            required
            autoFocus
            autoComplete="one-time-code"
            inputMode="numeric"
          />
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded bg-indigo-600 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {busy ? "Verifying…" : "Verify & log in"}
          </button>
          <button
            type="button"
            onClick={() => { setStep("username"); setCode(""); setError("") }}
            className="text-xs text-gray-500 underline"
          >
            ← Use a different username
          </button>
        </form>

        {error && (
          <p className="mt-4 rounded bg-red-50 p-3 text-left text-sm text-red-700">{error}</p>
        )}
      </div>

      {config.dev_mode && (
        <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-4 text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
            Dev mode
          </p>
          <input
            value={devName}
            onChange={(e) => setDevName(e.target.value)}
            className="mt-2 w-full rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="dev username"
          />
          <label className="mt-2 flex items-center justify-center gap-2 text-xs text-gray-500">
            <input type="checkbox" checked={devAdmin} onChange={(e) => setDevAdmin(e.target.checked)} />
            log in as admin
          </label>
          <button
            onClick={handleDev}
            disabled={busy}
            className="mt-2 w-full rounded bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-900 disabled:opacity-50"
          >
            {busy ? "…" : "Continue as " + (devName || "dev user")}
          </button>
        </div>
      )}
    </div>
  );
}
