import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Users, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../lib/api';
import { Modal } from '../components/common/Modal';
import { EmptyState } from '../components/common/EmptyState';
import { toast } from 'sonner';
import type { Tenant } from '../types';

interface AdminUser {
  id: string;
  email: string;
  full_name?: string;
  is_tenant_admin: boolean;
}

export function AdminUsers() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [tenantDropdown, setTenantDropdown] = useState(false);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [formEmail, setFormEmail] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [formName, setFormName] = useState('');
  const [formIsAdmin, setFormIsAdmin] = useState(false);

  const loadTenants = async () => {
    try {
      const { data } = await api.get<Tenant[]>('/admin/tenants/');
      const t = Array.isArray(data) ? data : [];
      setTenants(t);
      if (t.length > 0 && !selectedTenant) {
        setSelectedTenant(t[0].id);
      }
    } catch {
      toast.error('Impossible de charger les tenants');
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    if (!selectedTenant) return;
    try {
      const { data } = await api.get<AdminUser[]>(`/admin/tenants/${selectedTenant}/users/`);
      setUsers(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les utilisateurs');
    }
  };

  useEffect(() => { loadTenants(); }, []);
  useEffect(() => { loadUsers(); }, [selectedTenant]);

  const openCreate = () => {
    setEditing(null);
    setFormEmail('');
    setFormPassword('');
    setFormName('');
    setFormIsAdmin(false);
    setModalOpen(true);
  };

  const openEdit = (user: AdminUser) => {
    setEditing(user);
    setFormEmail(user.email);
    setFormPassword('');
    setFormName(user.full_name || '');
    setFormIsAdmin(user.is_tenant_admin);
    setModalOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTenant) return;
    try {
      const payload = {
        email: formEmail,
        full_name: formName,
        is_tenant_admin: formIsAdmin,
      };
      if (editing) {
        const body: Record<string, unknown> = payload;
        if (formPassword) body.password = formPassword;
        await api.put(`/admin/tenants/${selectedTenant}/users/${editing.id}`, body);
        toast.success('Utilisateur modifie');
      } else {
        await api.post(`/admin/tenants/${selectedTenant}/users/`, { ...payload, password: formPassword });
        toast.success('Utilisateur cree');
      }
      setModalOpen(false);
      loadUsers();
    } catch {
      toast.error('Erreur lors de la sauvegarde');
    }
  };

  const handleDelete = async (user: AdminUser) => {
    if (!confirm(`Supprimer l'utilisateur "${user.email}" ?`)) return;
    try {
      await api.delete(`/admin/tenants/${selectedTenant}/users/${user.id}`);
      toast.success('Utilisateur supprime');
      loadUsers();
    } catch {
      toast.error('Erreur lors de la suppression');
    }
  };

  if (loading) return <div className="p-6 text-text-muted">Chargement...</div>;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-text">Utilisateurs</h2>
          <p className="text-text-muted text-sm mt-1">Gerez les utilisateurs par tenant</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Tenant selector */}
          <div className="relative">
            <button
              onClick={() => setTenantDropdown(!tenantDropdown)}
              className="btn-secondary flex items-center gap-2"
            >
              {tenants.find(t => t.id === selectedTenant)?.name || 'Selectionner un tenant'}
              {tenantDropdown ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            {tenantDropdown && (
              <div className="absolute right-0 top-full mt-1 bg-bg-card border border-border rounded-lg shadow-xl z-10 min-w-[200px] max-h-60 overflow-y-auto">
                {tenants.map(t => (
                  <button
                    key={t.id}
                    onClick={() => { setSelectedTenant(t.id); setTenantDropdown(false); }}
                    className="w-full text-left px-3 py-2 text-sm text-text hover:bg-bg-card/80"
                  >
                    {t.name}
                  </button>
                ))}
              </div>
            )}
          </div>
          {selectedTenant && (
            <button onClick={openCreate} className="btn-primary flex items-center gap-2">
              <Plus size={18} />
              Ajouter un utilisateur
            </button>
          )}
        </div>
      </div>

      {!selectedTenant ? (
        <EmptyState
          icon={<Users size={48} />}
          title="Aucun tenant selectionne"
          description="Selectionnez un tenant pour voir ses utilisateurs"
        />
      ) : users.length === 0 ? (
        <EmptyState
          icon={<Users size={48} />}
          title="Aucun utilisateur"
          description="Ajoutez le premier utilisateur a ce tenant"
          action={<button onClick={openCreate} className="btn-primary flex items-center gap-2"><Plus size={16} /> Ajouter</button>}
        />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Email</th>
                <th className="text-left text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Nom</th>
                <th className="text-left text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Admin tenant</th>
                <th className="text-right text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-border/50 hover:bg-bg-card/50 transition-colors">
                  <td className="px-4 py-3">
                    <span className="text-text text-sm">{user.email}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-medium text-text">{user.full_name || '-'}</span>
                  </td>
                  <td className="px-4 py-3">
                    {user.is_tenant_admin ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-accent/10 text-accent">Oui</span>
                    ) : (
                      <span className="text-text-muted text-sm">Non</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button onClick={() => openEdit(user)} className="btn-secondary text-sm px-3 py-1.5">
                        <Edit size={16} />
                      </button>
                      <button onClick={() => handleDelete(user)} className="btn-danger text-sm px-3 py-1.5">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Modifier l\'utilisateur' : 'Nouvel utilisateur'}>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Email *</label>
            <input className="input-base" type="email" value={formEmail} onChange={(e) => setFormEmail(e.target.value)} required disabled={!!editing} />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Password{editing ? ' (laissez vide pour ne pas changer)' : ' *'}
            </label>
            <input className="input-base" type="password" value={formPassword} onChange={(e) => setFormPassword(e.target.value)} required={!editing} />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Nom</label>
            <input className="input-base" value={formName} onChange={(e) => setFormName(e.target.value)} />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="isAdmin"
              checked={formIsAdmin}
              onChange={(e) => setFormIsAdmin(e.target.checked)}
              className="rounded border-border bg-bg-secondary text-accent"
            />
            <label htmlFor="isAdmin" className="text-sm text-text">Admin tenant</label>
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">Annuler</button>
            <button type="submit" className="btn-primary">Enregistrer</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
