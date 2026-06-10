import { useAuth } from '../hooks/useAuth';
import { FolderOpen, FileText, MessageSquare } from 'lucide-react';
import { useNavigate } from '@tanstack/react-router';

export function Dashboard() {
  const { tenant } = useAuth();
  const navigate = useNavigate();

  const quickActions = [
    { label: 'Services', icon: FolderOpen, path: '/services', desc: 'Gerer les departements' },
    { label: 'Documents', icon: FileText, path: '/documents', desc: 'Importer des fichiers' },
    { label: 'Chat', icon: MessageSquare, path: '/chat', desc: 'Poser des questions' },
  ];

  return (
    <div className="p-6 max-w-5xl">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-text">
          Bienvenue{tenant ? `, ${tenant.name}` : ''}
        </h2>
        <p className="text-text-muted mt-1">Tableau de bord ProAiRag</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {[
          { label: 'Services', value: '-', icon: FolderOpen },
          { label: 'Documents', value: '-', icon: FileText },
          { label: 'Conversations', value: '-', icon: MessageSquare },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-muted text-sm">{label}</p>
                <p className="text-2xl font-bold text-text mt-1">{value}</p>
              </div>
              <Icon className="text-accent/60" size={28} />
            </div>
          </div>
        ))}
      </div>

      <h3 className="text-lg font-semibold text-text mb-4">Actions rapides</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {quickActions.map(({ label, icon: Icon, path, desc }) => (
          <button
            key={label}
            onClick={() => navigate({ to: path })}
            className="card hover:border-accent/50 transition-all group text-left"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-text group-hover:text-accent transition-colors">
                  {label}
                </p>
                <p className="text-text-muted text-sm mt-1">{desc}</p>
              </div>
              <Icon className="text-text-muted group-hover:text-accent transition-colors" size={24} />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
