import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { authApi } from "../api/auth";
import { clearAuth, getStoredUser, getToken, User } from "../api/client";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  logout: () => void;
  clearSession: () => void;
  refreshUser: () => Promise<void>;
  login: (email: string, password: string) => Promise<User>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  logout: () => {},
  clearSession: () => {},
  refreshUser: async () => {},
  login: async () => {
    throw new Error("AuthProvider not mounted");
  },
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(getStoredUser());
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    if (!getToken()) {
      setUser(null);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      clearAuth();
      setUser(null);
    }
  };

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    setUser(res.user);
    return res.user;
  };

  useEffect(() => {
    refreshUser().finally(() => setLoading(false));
  }, []);

  const clearSession = () => {
    clearAuth();
    setUser(null);
  };

  const logout = () => {
    clearSession();
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, loading, logout, clearSession, refreshUser, login }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
