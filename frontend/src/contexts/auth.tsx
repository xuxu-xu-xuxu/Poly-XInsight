"use client";
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { useRouter } from "next/navigation";

interface User {
  user_id: string;
  username: string;
}

interface AuthContext {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthContext | null>(null);
const TOKEN_KEY = "poly_xinsight_token";

function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  else sessionStorage.removeItem(TOKEN_KEY);
}

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Restore session on mount
  useEffect(() => {
    const stored = getStoredToken();
    if (stored) {
      setTokenState(stored);
      fetch("/api/auth/me", { headers: { Authorization: `Bearer ${stored}` } })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (data) setUser({ user_id: data.user_id, username: data.username });
          else { setToken(null); setTokenState(null); }
        })
        .catch(() => { setToken(null); setTokenState(null); })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const resp = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "登录失败");
    }
    const data = await resp.json();
    setToken(data.token);
    setTokenState(data.token);
    setUser({ user_id: data.user_id, username: data.username });
    router.push("/");
  }, [router]);

  const register = useCallback(async (username: string, password: string) => {
    const resp = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "注册失败");
    }
    const data = await resp.json();
    setToken(data.token);
    setTokenState(data.token);
    setUser({ user_id: data.user_id, username: data.username });
    router.push("/");
  }, [router]);

  const logout = useCallback(() => {
    setToken(null);
    setTokenState(null);
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthCtx.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
