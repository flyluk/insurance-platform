import { createContext, useContext, useMemo, useState, ReactNode } from "react";
import api from "../api/client";

type AuthUser = {
  email: string;
  role: string;
  full_name: string;
  party_id: string | null;
};

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const ALLOWED = new Set(["policyholder", "admin"]);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem("holder_portal_token"));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const raw = localStorage.getItem("holder_portal_user");
    return raw ? JSON.parse(raw) : null;
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      async login(email, password) {
        const { data } = await api.post("/auth/login", { email, password });
        if (!ALLOWED.has(data.role)) {
          throw new Error("This portal is for policyholders only");
        }
        if (data.role === "policyholder" && !data.party_id) {
          throw new Error("Account is not linked to a customer profile");
        }
        localStorage.setItem("holder_portal_token", data.access_token);
        const u: AuthUser = {
          email: data.email,
          role: data.role,
          full_name: data.full_name,
          party_id: data.party_id ?? null,
        };
        localStorage.setItem("holder_portal_user", JSON.stringify(u));
        setToken(data.access_token);
        setUser(u);
      },
      logout() {
        localStorage.removeItem("holder_portal_token");
        localStorage.removeItem("holder_portal_user");
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
