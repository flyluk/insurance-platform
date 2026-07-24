import { createContext, useContext, useMemo, useState, ReactNode } from "react";
import api from "../api/client";

type AuthUser = {
  email: string;
  role: string;
  full_name: string;
};

type SessionPayload = {
  access_token: string;
  email: string;
  role: string;
  full_name: string;
  party_id?: string | null;
};

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  impersonating: boolean;
  login: (email: string, password: string) => Promise<void>;
  adoptSession: (data: SessionPayload, opts?: { keepAdminReturn?: boolean }) => void;
  returnToAdmin: () => boolean;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readUser(): AuthUser | null {
  const raw = localStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [user, setUser] = useState<AuthUser | null>(() => readUser());
  const [impersonating, setImpersonating] = useState(
    () => Boolean(localStorage.getItem("admin_return_token")),
  );

  function persistSession(data: SessionPayload) {
    localStorage.setItem("token", data.access_token);
    const u = { email: data.email, role: data.role, full_name: data.full_name };
    localStorage.setItem("user", JSON.stringify(u));
    setToken(data.access_token);
    setUser(u);
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      impersonating,
      async login(email, password) {
        const { data } = await api.post("/auth/login", { email, password });
        localStorage.removeItem("admin_return_token");
        localStorage.removeItem("admin_return_user");
        setImpersonating(false);
        persistSession(data);
      },
      adoptSession(data, opts) {
        if (opts?.keepAdminReturn && token && user?.role === "admin" && !impersonating) {
          localStorage.setItem("admin_return_token", token);
          localStorage.setItem("admin_return_user", JSON.stringify(user));
          setImpersonating(true);
        }
        persistSession(data);
      },
      returnToAdmin() {
        const adminToken = localStorage.getItem("admin_return_token");
        const adminUserRaw = localStorage.getItem("admin_return_user");
        if (!adminToken || !adminUserRaw) return false;
        const adminUser = JSON.parse(adminUserRaw) as AuthUser;
        localStorage.setItem("token", adminToken);
        localStorage.setItem("user", JSON.stringify(adminUser));
        localStorage.removeItem("admin_return_token");
        localStorage.removeItem("admin_return_user");
        setToken(adminToken);
        setUser(adminUser);
        setImpersonating(false);
        return true;
      },
      logout() {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        localStorage.removeItem("admin_return_token");
        localStorage.removeItem("admin_return_user");
        setToken(null);
        setUser(null);
        setImpersonating(false);
      },
    }),
    [user, token, impersonating],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("AuthProvider missing");
  return ctx;
}
