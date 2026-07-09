"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { setToken, type UserProfile } from "@/lib/api";

interface AuthState {
  user: UserProfile | null;
  token: string | null;
  login: (token: string, user: UserProfile) => void;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  login: () => {},
  logout: () => {},
  isAuthenticated: false,
  isLoading: true,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("bsjp_token");
    const storedUser = localStorage.getItem("bsjp_user");
    if (stored && storedUser) {
      setTokenState(stored);
      setToken(stored);
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  const login = useCallback((t: string, u: UserProfile) => {
    setTokenState(t);
    setUser(u);
    setToken(t);
    localStorage.setItem("bsjp_token", t);
    localStorage.setItem("bsjp_user", JSON.stringify(u));
  }, []);

  const logout = useCallback(() => {
    setTokenState(null);
    setUser(null);
    setToken(null);
    localStorage.removeItem("bsjp_token");
    localStorage.removeItem("bsjp_user");
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, token, login, logout, isAuthenticated: !!token, isLoading }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
