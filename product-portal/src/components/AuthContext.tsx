import { createContext, useContext, useMemo, useState, ReactNode } from "react";
import api from "../api/client";

type AuthUser = {
  email: string;
  role: string;
  full_name: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const ALLOWED = new Set(["product", "admin"]);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem("product_portal_token"));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const raw = localStorage.getItem("product_portal_user");
    return raw ? JSON.parse(raw) : null;
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      async login(email, password) {
        const { data } = await api.post("/auth/login", { email, password });
        if (!ALLOWED.has(data.role)) {
          throw new Error("Only product or admin roles can use Product Studio");
        }
        localStorage.setItem("product_portal_token", data.access_token);
        const u = { email: data.email, role: data.role, full_name: data.full_name };
        localStorage.setItem("product_portal_user", JSON.stringify(u));
        setToken(data.access_token);
        setUser(u);
      },
      logout() {
        localStorage.removeItem("product_portal_token");
        localStorage.removeItem("product_portal_user");
        setToken(null);
        setUser(null);
      },
    }),
    [user, token]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("AuthProvider missing");
  return ctx;
}
