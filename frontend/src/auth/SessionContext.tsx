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
  SIGNED_OUT_EVENT,
  clearToken,
  getToken,
  login as apiLogin,
  logout as apiLogout,
  restoreSession,
} from "../api/client";

export type SessionStatus = "checking" | "signed-out" | "signed-in";

export type SessionValue = {
  status: SessionStatus;
  email: string | null;
  role: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>("checking");
  const [email, setEmail] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!getToken()) {
      setStatus("signed-out");
      return;
    }
    restoreSession()
      .then((info) => {
        if (cancelled) return;
        setEmail(info.user.email);
        setRole(info.user.role);
        setStatus("signed-in");
      })
      .catch(() => {
        clearToken();
        if (!cancelled) setStatus("signed-out");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onSignedOut = () => {
      setEmail(null);
      setRole(null);
      setStatus("signed-out");
    };
    window.addEventListener(SIGNED_OUT_EVENT, onSignedOut);
    return () => window.removeEventListener(SIGNED_OUT_EVENT, onSignedOut);
  }, []);

  const signIn = useCallback(async (nextEmail: string, password: string) => {
    const result = await apiLogin(nextEmail, password);
    setEmail(result.user.email);
    setRole(result.user.role);
    setStatus("signed-in");
  }, []);

  const signOut = useCallback(async () => {
    await apiLogout();
    setEmail(null);
    setRole(null);
    setStatus("signed-out");
  }, []);

  const value = useMemo<SessionValue>(
    () => ({ status, email, role, signIn, signOut }),
    [status, email, role, signIn, signOut],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside a SessionProvider");
  return value;
}
