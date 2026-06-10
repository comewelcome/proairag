import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { useAuth } from '../hooks/useAuth';
import { Building2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, loading, error } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login({ email, password });
      toast.success('Connexion reussie');
      navigate({ to: '/' });
    } catch {
      toast.error(error || 'Erreur de connexion');
    }
  };

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-2">
            <Building2 className="text-accent" size={32} />
          </div>
          <h1 className="text-2xl font-bold text-text">ProAiRag</h1>
          <p className="text-text-muted mt-1">Hybrid Multi-Tenant RAG</p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-base"
                placeholder="votre@email.com"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Mot de passe</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-base"
                placeholder="••••••••"
                required
              />
            </div>
            {error && (
              <div className="flex items-center gap-2 text-error text-sm">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}
            <button type="submit" disabled={loading} className="w-full btn-primary py-2.5">
              {loading ? 'Connexion...' : 'Se connecter'}
            </button>
          </form>
        </div>

        <p className="text-center text-text-muted/50 text-xs mt-4">
          ProAiRag v0.1.0
        </p>
      </div>
    </div>
  );
}
