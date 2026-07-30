import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import TelegramLoginButton from "../components/TelegramLoginButton";

export default function Login() {
  const { user, config, loginWithTelegram, devLogin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || "/";

  const [error, setError] = useState("");
  const [devName, setDevName] = useState("devuser");
  const [devAdmin, setDevAdmin] = useState(false);

  if (user) {
    navigate(from, { replace: true });
    return null;
  }

  const finish = async (fn) => {
    setError("");
    try {
      await fn();
      navigate(from, { replace: true });
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="mx-auto max-w-md space-y-6 rounded-lg border border-gray-200 bg-white p-8 text-center">
      <div>
        <h1 className="text-2xl font-bold">Log in</h1>
        <p className="mt-2 text-sm text-gray-600">
          We use Telegram instead of passwords — your identity comes from an account you already
          have, and membership in the community group is checked automatically.
        </p>
      </div>

      {config.telegram_bot_username ? (
        <TelegramLoginButton
          botUsername={config.telegram_bot_username}
          onAuth={(tgUser) => finish(() => loginWithTelegram(tgUser))}
        />
      ) : (
        !config.dev_mode && (
          <p className="text-sm text-gray-500">Telegram login isn't configured on this server yet.</p>
        )
      )}

      {config.dev_mode && (
        <div className="space-y-3 rounded-lg border border-dashed border-gray-300 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
            Dev mode — no Telegram needed
          </p>
          <input
            value={devName}
            onChange={(e) => setDevName(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="dev username"
            aria-label="Dev username"
          />
          <label className="flex items-center justify-center gap-2 text-xs text-gray-500">
            <input type="checkbox" checked={devAdmin} onChange={(e) => setDevAdmin(e.target.checked)} />
            log in as admin
          </label>
          <button
            onClick={() => finish(() => devLogin(devName, devAdmin))}
            className="w-full rounded bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-900"
          >
            Continue as {devName || "dev user"}
          </button>
        </div>
      )}

      {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <p className="text-xs text-gray-400">
        No password is ever created or stored. Sessions can be revoked instantly by a moderator.
      </p>
    </div>
  );
}
