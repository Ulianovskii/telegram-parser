import { useCallback, useEffect, useRef, useState } from "react";

export type AuthUser = {
  id: string;
  name: string;
  username: string | null;
  telegram_id: string | null;
};
type SessionInfo = { user: AuthUser; csrf_token: string };
type AuthState =
  | { status: "loading" | "anonymous" | "error"; session: null }
  | { status: "authenticated"; session: SessionInfo };

// Mount ONCE above pages. Pass this result through props or a React Context.
// This hook is for the standalone same-origin React + FastAPI app, not a Windmill public URL.
export function useAuth() {
  const [state, setState] = useState<AuthState>({
    status: "loading",
    session: null,
  });
  const currentRequest = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    currentRequest.current?.abort();
    const controller = new AbortController();
    currentRequest.current = controller;
    setState({ status: "loading", session: null });
    try {
      const response = await fetch("/auth/me", {
        credentials: "same-origin",
        cache: "no-store",
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      if (response.status === 401) {
        setState({ status: "anonymous", session: null });
        return;
      }
      if (!response.ok) throw new Error("Session check failed");
      const session: SessionInfo = await response.json();
      if (!controller.signal.aborted)
        setState({ status: "authenticated", session });
    } catch {
      if (!controller.signal.aborted)
        setState({ status: "error", session: null });
    }
  }, []);

  useEffect(() => {
    void refresh();
    return () => currentRequest.current?.abort();
  }, [refresh]);

  const logout = useCallback(async () => {
    if (state.status !== "authenticated") return;
    const response = await fetch("/auth/logout", {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRF-Token": state.session.csrf_token },
    });
    if (!response.ok && response.status !== 401)
      throw new Error("Logout failed");
    currentRequest.current?.abort();
    setState({ status: "anonymous", session: null });
  }, [state]);

  return {
    status: state.status,
    user: state.session?.user ?? null,
    csrfToken: state.session?.csrf_token ?? null,
    refresh,
    logout,
    login: () => window.location.assign("/auth/telegram/start"),
  };
}
