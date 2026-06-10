import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { api } from '../lib/api';
import type { User, Tenant, LoginRequest, LoginResponse } from '../types';

interface AuthContextType {
  user: User | null;
  tenant: Tenant | null;
  tenants: Tenant[];
  login: (data: LoginRequest) => Promise<void>;
  logout: () => void;
  selectTenant: (tenant: Tenant) => void;
  loadTenants: () => Promise<void>;
  loading: boolean;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('jwt_token');
    const storedUser = localStorage.getItem('user');
    const storedTenant = localStorage.getItem('tenant');
    if (token && storedUser) {
      setUser(JSON.parse(storedUser));
      if (storedTenant) setTenant(JSON.parse(storedTenant));
    }
  }, []);

  const login = useCallback(async (data: LoginRequest) => {
    setLoading(true);
    setError(null);
    try {
      const { data: response } = await api.post<LoginResponse>('/auth/login', data);
      localStorage.setItem('jwt_token', response.access_token);
      localStorage.setItem('user', JSON.stringify(response.user));
      setUser(response.user);
      await loadTenants();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('user');
    localStorage.removeItem('tenant');
    setUser(null);
    setTenant(null);
    window.location.href = '/login';
  }, []);

  const selectTenant = useCallback((t: Tenant) => {
    setTenant(t);
    localStorage.setItem('tenant', JSON.stringify(t));
  }, []);

  const loadTenants = useCallback(async () => {
    try {
      const { data } = await api.get<Tenant[]>('/tenants/');
      setTenants(Array.isArray(data) ? data : [data]);
    } catch {
      if (user?.tenant_id) {
        const t = { id: user.tenant_id, name: user.email, is_active: true };
        setTenants([t]);
        if (!tenant) selectTenant(t);
      }
    }
  }, [user, tenant, selectTenant]);

  return (
    <AuthContext.Provider value={{ user, tenant, tenants, login, logout, selectTenant, loadTenants, loading, error }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
