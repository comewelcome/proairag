import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Database, Brain, Save } from 'lucide-react';
import { api } from '../lib/api';
import { toast } from 'sonner';
import type { RagSettings, SystemStats } from '../types';

export function Settings() {
  const [settings, setSettings] = useState<RagSettings>({
    chunk_size: 512,
    chunk_overlap: 64,
    top_k: 5,
    embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
    llm_provider: 'openai',
    llm_model: 'gpt-4o-mini',
    openai_api_key: '',
    ollama_base_url: 'http://localhost:11434',
  });
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const { data: s } = await api.get<RagSettings>('/settings/');
      setSettings({ ...settings, ...s });
    } catch {
      // Settings endpoint may not exist yet - use defaults
    }
    try {
      const { data: st } = await api.get<SystemStats>('/settings/stats');
      setStats(st);
    } catch {
      // Stats endpoint may not exist yet
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/settings/', settings);
      toast.success('Parametres sauvegardes');
    } catch {
      toast.error('Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-6 text-text-muted">Chargement...</div>;

  return (
    <div className="p-6 max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <SettingsIcon className="text-accent" size={24} />
        <div>
          <h2 className="text-xl font-bold text-text">Parametres</h2>
          <p className="text-text-muted text-sm">Configurez les parametres RAG de votre projet</p>
        </div>
      </div>

      {/* RAG Settings */}
      <div className="card mb-6">
        <h3 className="font-semibold text-text mb-4 flex items-center gap-2">
          <Brain size={18} className="text-accent" />
          Parametres RAG
        </h3>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Taille des chunks (mots)</label>
              <input
                type="number"
                className="input-base"
                value={settings.chunk_size}
                onChange={(e) => setSettings({ ...settings, chunk_size: parseInt(e.target.value) || 512 })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Chevauchement (mots)</label>
              <input
                type="number"
                className="input-base"
                value={settings.chunk_overlap}
                onChange={(e) => setSettings({ ...settings, chunk_overlap: parseInt(e.target.value) || 64 })}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Top K (resultats vectoriels)</label>
            <input
              type="number"
              className="input-base"
              value={settings.top_k}
              onChange={(e) => setSettings({ ...settings, top_k: parseInt(e.target.value) || 5 })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Modele d'embedding</label>
            <select
              className="input-base"
              value={settings.embedding_model}
              onChange={(e) => setSettings({ ...settings, embedding_model: e.target.value })}
            >
              <option value="sentence-transformers/all-MiniLM-L6-v2">all-MiniLM-L6-v2 (384d)</option>
              <option value="sentence-transformers/all-mpnet-base-v2">all-mpnet-base-v2 (768d)</option>
              <option value="openai/text-embedding-3-small">text-embedding-3-small</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Provider LLM</label>
            <select
              className="input-base"
              value={settings.llm_provider}
              onChange={(e) => setSettings({ ...settings, llm_provider: e.target.value as any })}
            >
              <option value="openai">OpenAI</option>
              <option value="ollama">Ollama</option>
              <option value="fallback">Fallback (contexte seul)</option>
            </select>
          </div>
          {settings.llm_provider === 'openai' && (
            <>
              <div>
                <label className="block text-sm font-medium text-text-muted mb-1">Cles API OpenAI</label>
                <input
                  type="password"
                  className="input-base"
                  value={settings.openai_api_key || ''}
                  onChange={(e) => setSettings({ ...settings, openai_api_key: e.target.value })}
                  placeholder="sk-..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-muted mb-1">Modele OpenAI</label>
                <input
                  className="input-base"
                  value={settings.llm_model || 'gpt-4o-mini'}
                  onChange={(e) => setSettings({ ...settings, llm_model: e.target.value })}
                />
              </div>
            </>
          )}
          {settings.llm_provider === 'ollama' && (
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">URL Ollama</label>
              <input
                className="input-base"
                value={settings.ollama_base_url || ''}
                onChange={(e) => setSettings({ ...settings, ollama_base_url: e.target.value })}
              />
            </div>
          )}
        </div>

        <div className="flex justify-end mt-6">
          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
            <Save size={16} />
            {saving ? 'Sauvegarde...' : 'Enregistrer'}
          </button>
        </div>
      </div>

      {/* System Stats */}
      <div className="card">
        <h3 className="font-semibold text-text mb-4 flex items-center gap-2">
          <Database size={18} className="text-accent" />
          Informations du systeme
        </h3>
        {stats ? (
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-bg-secondary rounded-lg p-3">
              <p className="text-text-muted text-xs">Documents indexes</p>
              <p className="text-xl font-bold text-text mt-1">{stats.document_count}</p>
            </div>
            <div className="bg-bg-secondary rounded-lg p-3">
              <p className="text-text-muted text-xs">Chunks en base</p>
              <p className="text-xl font-bold text-text mt-1">{stats.chunk_count}</p>
            </div>
            <div className="bg-bg-secondary rounded-lg p-3">
              <p className="text-text-muted text-xs">Entites dans le graphe</p>
              <p className="text-xl font-bold text-text mt-1">{stats.entity_count}</p>
            </div>
            <div className="bg-bg-secondary rounded-lg p-3">
              <p className="text-text-muted text-xs">Connectivite</p>
              <p className="text-sm mt-1">
                <span className={stats.postgres_connected ? 'text-success' : 'text-error'}>PostgreSQL</span>
                {' / '}
                <span className={stats.neo4j_connected ? 'text-success' : 'text-error'}>Neo4j</span>
              </p>
            </div>
          </div>
        ) : (
          <p className="text-text-muted text-sm">Statistiques non disponibles</p>
        )}
      </div>
    </div>
  );
}
