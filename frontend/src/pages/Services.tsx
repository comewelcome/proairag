import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, FolderOpen } from 'lucide-react';
import { api } from '../lib/api';
import { Modal } from '../components/common/Modal';
import { EmptyState } from '../components/common/EmptyState';
import { toast } from 'sonner';
import type { Department } from '../types';

export function Services() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Department | null>(null);
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');

  const load = async () => {
    try {
      const { data } = await api.get<Department[]>('/departments/');
      setDepartments(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les services');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditing(null);
    setFormName('');
    setFormDesc('');
    setModalOpen(true);
  };

  const openEdit = (dept: Department) => {
    setEditing(dept);
    setFormName(dept.name);
    setFormDesc(dept.description || '');
    setModalOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editing) {
        await api.put(`/departments/${editing.id}`, { name: formName, description: formDesc });
        toast.success('Service modifie');
      } else {
        await api.post('/departments/', { name: formName, description: formDesc });
        toast.success('Service cree');
      }
      setModalOpen(false);
      load();
    } catch {
      toast.error('Erreur lors de la sauvegarde');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Supprimer ce service ?')) return;
    try {
      await api.delete(`/departments/${id}`);
      toast.success('Service supprime');
      load();
    } catch {
      toast.error('Erreur lors de la suppression');
    }
  };

  if (loading) return <div className="p-6 text-text-muted">Chargement...</div>;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-text">Services</h2>
          <p className="text-text-muted text-sm mt-1">Gerez les departements de votre entreprise</p>
        </div>
        <button onClick={openCreate} className="btn-primary flex items-center gap-2">
          <Plus size={18} />
          Nouveau service
        </button>
      </div>

      {departments.length === 0 ? (
        <EmptyState
          icon={<FolderOpen size={48} />}
          title="Aucun service"
          description="Creez votre premier service pour organiser vos documents"
          action={<button onClick={openCreate} className="btn-primary">+ Nouveau service</button>}
        />
      ) : (
        <div className="space-y-2">
          {departments.map((dept) => (
            <div key={dept.id} className="card flex items-center justify-between">
              <div>
                <p className="font-medium text-text">{dept.name}</p>
                {dept.description && <p className="text-text-muted text-sm mt-0.5">{dept.description}</p>}
              </div>
              <div className="flex gap-2">
                <button onClick={() => openEdit(dept)} className="btn-secondary text-sm px-3 py-1.5">
                  <Edit size={16} />
                </button>
                <button onClick={() => handleDelete(dept.id)} className="btn-danger text-sm px-3 py-1.5">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Modifier le service' : 'Nouveau service'}>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Nom *</label>
            <input className="input-base" value={formName} onChange={(e) => setFormName(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Description</label>
            <textarea className="input-base" rows={3} value={formDesc} onChange={(e) => setFormDesc(e.target.value)} />
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
