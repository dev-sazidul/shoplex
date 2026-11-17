"use client";

import { createContext, useContext, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { ApiError, AuthenticatedUser, AuthTokens, PortalRole } from "@shoplex/types";

interface LoginResult extends AuthTokens {
  user: AuthenticatedUser;
}

interface SessionContextValue {
  user: AuthenticatedUser | null;
  tokens: AuthTokens | null;
  login: (email: string, password: string) => Promise<AuthenticatedUser>;
  logout: () => Promise<void>;
  apiFetch: (path: string, init?: RequestInit) => Promise<Response>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

function apiBase() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
}

async function errorMessage(response: Response) {
  const data = await response.json().catch(() => ({})) as ApiError;
  if (data.detail) return data.detail;
  const firstError = Object.values(data).find((value) => Array.isArray(value) && typeof value[0] === "string") as string[] | undefined;
  return firstError?.[0] ?? "The request could not be completed.";
}

export function SessionProvider({ children, portalRole, allowRoles = [] }: { children: ReactNode; portalRole: PortalRole; allowRoles?: PortalRole[] }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const refreshPromise = useRef<Promise<AuthTokens | null> | null>(null);

  async function login(email: string, password: string) {
    const response = await fetch(`${apiBase()}/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) throw new Error(await errorMessage(response));
    const result = await response.json() as LoginResult;
    if (!result.user.roles.includes(portalRole) && !allowRoles.some((role) => result.user.roles.includes(role))) {
      await fetch(`${apiBase()}/auth/logout/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${result.access}` },
        body: JSON.stringify({ refresh: result.refresh }),
      });
      throw new Error(`This account does not have ${portalRole} portal access.`);
    }
    setUser(result.user);
    setTokens({ access: result.access, refresh: result.refresh });
    return result.user;
  }

  async function refreshSession(current: AuthTokens) {
    if (!refreshPromise.current) {
      refreshPromise.current = fetch(`${apiBase()}/auth/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: current.refresh }),
      }).then(async (response) => {
        if (!response.ok) return null;
        const rotated = await response.json() as AuthTokens;
        setTokens(rotated);
        return rotated;
      }).finally(() => {
        refreshPromise.current = null;
      });
    }
    return refreshPromise.current;
  }

  async function apiFetch(path: string, init: RequestInit = {}) {
    if (!tokens) throw new Error("Sign in to continue.");
    const makeRequest = (access: string) => {
      const headers = new Headers(init.headers);
      headers.set("Authorization", `Bearer ${access}`);
      if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
      return fetch(`${apiBase()}${path}`, { ...init, headers });
    };
    let response = await makeRequest(tokens.access);
    if (response.status === 401) {
      const refreshed = await refreshSession(tokens);
      if (!refreshed) {
        setTokens(null);
        setUser(null);
        throw new Error("Your session expired. Please sign in again.");
      }
      response = await makeRequest(refreshed.access);
    }
    return response;
  }

  async function logout() {
    if (!tokens) return;
    const response = await fetch(`${apiBase()}/auth/logout/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${tokens.access}` },
      body: JSON.stringify({ refresh: tokens.refresh }),
    });
    if (!response.ok && response.status !== 401) throw new Error(await errorMessage(response));
    setTokens(null);
    setUser(null);
  }

  return <SessionContext.Provider value={{ user, tokens, login, logout, apiFetch }}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used within a SessionProvider.");
  return value;
}
