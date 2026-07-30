import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "../api";

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
        /* backend unreachable */
      }
      try {
        setUser(await api.get("/auth/me"));
      } catch {
        setUser(null);
      }
      setLoading(false);
    })();
  }, []);

  const requestCode = useCallback(async (username) => {
    await api.post("/auth/code/request", { username });
  }, []);

  const verifyCode = useCallback(async (username, code) => {
    const me = await api.post("/auth/code/verify", { username, code });
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
    <AuthContext.Provider value={{ user, config, loading, requestCode, verifyCode, devLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
