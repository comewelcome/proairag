import { useState, useEffect } from 'react';
import { Shield, Trash2 } from 'lucide-react';
import { api } from '../lib/api';
import { EmptyState } from '../components/common/EmptyState';
import { toast } from 'sonner';
import type { Tenant } from '../types';

export function AdminTenants() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const { data } = await api.get<Tenant[]>('/admin/tenants/');
      setTenants(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les tenants');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (tenant: Tenant) => {
    if (!confirm(`Supprimer le tenant "${tenant.name}" ? Cette action est irreversible.`)) return;
    try {
      await api.delete(`/admin/tenants/${tenant.id}`);
      toast.success('Tenant supprime');
      load();
    } catch {
      toast.error('Erreur lors de la suppression du tenant');
    }
  };

  if (loading) return <div className="p-6 text-text-muted">Chargement...</div>;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-text">Tenants</h2>
          <p className="text-text-muted text-sm mt-1">Gerez les entreprises du systeme</p>
        </div>
      </div>

      {tenants.length === 0 ? (
        <EmptyState
          icon={<Shield size={48} />}
          title="Aucun tenant"
          description="Aucun tenant n'a ete cree"
        />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Nom</th>
                <th className="text-left text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Email Admin</th>
                <th className="text-left text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Statut</th>
                <th className="text-right text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((tenant) => (
                <tr key={tenant.id} className="border-b border-border/50 hover:bg-bg-card/50 transition-colors">
                  <td className="px-4 py-3">
                    <span className="font-medium text-text">{tenant.name}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-text-muted text-sm">-</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${tenant.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                      {tenant.is_active ? 'Actif' : 'Inactif'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(tenant)}
                      className="btn-danger text-sm px-3 py-1.5 inline-flex items-center gap-1.5"
                    >
                      <Trash2 size={14} />
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
