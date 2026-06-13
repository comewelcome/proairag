import { useState, useEffect } from 'react';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../lib/api';
import { EmptyState } from '../components/common/EmptyState';
import { toast } from 'sonner';
import type { Tenant, DocumentItem } from '../types';

export function AdminDocuments() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [tenantDropdown, setTenantDropdown] = useState(false);

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

  const loadDocs = async () => {
    if (!selectedTenant) return;
    try {
      const { data } = await api.get<DocumentItem[]>(`/admin/tenants/${selectedTenant}/documents/`);
      setDocuments(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les documents');
    }
  };

  useEffect(() => { loadTenants(); }, []);
  useEffect(() => { loadDocs(); }, [selectedTenant]);

  if (loading) return <div className="p-6 text-text-muted">Chargement...</div>;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-text">Documents</h2>
          <p className="text-text-muted text-sm mt-1">Vue des documents par tenant</p>
        </div>
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
      </div>

      {!selectedTenant ? (
        <EmptyState
          icon={<FileText size={48} />}
          title="Aucun tenant selectionne"
          description="Selectionnez un tenant pour voir ses documents"
        />
      ) : documents.length === 0 ? (
        <EmptyState
          icon={<FileText size={48} />}
          title="Aucun document"
          description="Aucun document n'a ete importe pour ce tenant"
        />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Titre</th>
                <th className="text-left text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Service</th>
                <th className="text-left text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Source</th>
                <th className="text-left text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Type</th>
                <th className="text-left text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Date</th>
                <th className="text-right text-xs font-semibold text-text-muted uppercase tracking-wider px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-b border-border/50 hover:bg-bg-card/50 transition-colors">
                  <td className="px-4 py-3">
                    <span className="font-medium text-text">{doc.title}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-text-muted text-sm">{doc.department_id || '-'}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-text-muted text-sm">{doc.source || '-'}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-text-muted bg-bg-secondary px-2 py-1 rounded-md">{doc.content_type}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-text-muted text-sm">
                      {doc.created_at ? new Date(doc.created_at).toLocaleDateString('fr-FR') : '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-text-muted text-xs">-</span>
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
