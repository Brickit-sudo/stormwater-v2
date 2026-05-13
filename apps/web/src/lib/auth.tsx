"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  ApiError,
  demoOrganizationId,
  getCurrentAuth,
  loginWithPassword,
  logoutCurrentUser,
} from "./api";
import type { AuthUser } from "./types";

const frontendAuthEnabled =
  process.env.NEXT_PUBLIC_AUTH_ENABLED?.trim().toLowerCase() === "true";

type AuthContextValue = {
  authEnabled: boolean;
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(frontendAuthEnabled);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!frontendAuthEnabled) {
      setUser(null);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await getCurrentAuth();
      setUser(response.user);
    } catch (caught) {
      setUser(null);
      if (caught instanceof ApiError && caught.status === 401) {
        setError(null);
      } else {
        setError(caught instanceof Error ? caught.message : "Unable to verify session.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refresh();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await loginWithPassword({ email, password });
    if (!response.user) {
      throw new Error("Login did not return a user.");
    }
    setUser(response.user);
    setError(null);
    return response.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutCurrentUser();
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      authEnabled: frontendAuthEnabled,
      user,
      loading,
      error,
      refresh,
      login,
      logout,
    }),
    [error, loading, login, logout, refresh, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}

export function useOrganizationId(): string {
  const { authEnabled, user } = useAuth();
  if (!authEnabled) {
    return demoOrganizationId;
  }
  return user?.default_organization_id ?? "";
}
