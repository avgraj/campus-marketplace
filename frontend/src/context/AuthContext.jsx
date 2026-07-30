import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "../api";

// Holds the current user + public config and login/logout actions.
// Context + hooks is enough state management at this scale (plan §10).

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [config, setConfig] = useState({
    community_name: "Campus Marketplace",
    telegram_bot_username: "",
    dev_mode: false,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setConfig(await api.get("/config/public"));
      } catch {
        /* backend unreachable — defaults shown */
      }
      try {
        setUser(await api.get("/auth/me"));
      } catch {
        setUser(null);
      }
      setLoading(false);
    })();
  }, []);

  const loginWithTelegram = useCallback(async (tgPayload) => {
    const me = await api.post("/auth/telegram/callback", tgPayload);
    setUser(me);
    return me;
  }, []);

  const devLogin = useCallback(async (username, asAdmin = false) => {
    const me = await api.post("/auth/dev-login", { username, as_admin: asAdmin });
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, config, loading, loginWithTelegram, devLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
