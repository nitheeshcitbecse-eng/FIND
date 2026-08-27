import React, { createContext, useContext, useEffect, useState } from 'react';
import { api, getToken, login as apiLogin, setToken, User } from './api';

type AuthState = {
  user: User | null;
  loading: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthState>({
  user: null,
  loading: true,
  signIn: async () => {},
  signOut: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const token = await getToken();
      if (token) {
        try {
          setUser(await api.me());
        } catch {
          await setToken(null);
        }
      }
      setLoading(false);
    })();
  }, []);

  const signIn = async (username: string, password: string) => {
    await apiLogin(username, password);
    setUser(await api.me());
  };

  const signOut = async () => {
    await setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);