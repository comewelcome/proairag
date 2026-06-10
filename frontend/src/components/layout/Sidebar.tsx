import { useNavigate, useLocation } from '@tanstack/react-router';
import { LayoutDashboard, FolderOpen, FileText, MessageSquare, Settings, LogOut, Building2 } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/services', label: 'Services', icon: FolderOpen },
  { path: '/documents', label: 'Documents', icon: FileText },
  { path: '/chat', label: 'Chat', icon: MessageSquare },
  { path: '/settings', label: 'Parametres', icon: Settings },
];

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { tenant, logout } = useAuth();

  return (
    <aside className="w-64 min-h-screen bg-bg-secondary border-r border-border flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Building2 className="text-accent" size={24} />
          <span className="font-bold text-lg text-text">ProAiRag</span>
        </div>
        {tenant && (
          <div className="mt-2 px-2 py-1 bg-bg-card rounded-md text-sm text-text-muted truncate">
            {tenant.name}
          </div>
        )}
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ path, label, icon: Icon }) => {
          const isActive = location.pathname === path || (path !== '/' && location.pathname.startsWith(path));
          return (
            <button
              key={path}
              onClick={() => navigate({ to: path })}
              className={`w-full sidebar-link ${isActive ? 'sidebar-link-active' : ''}`}
            >
              <Icon size={18} />
              <span className="text-sm">{label}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-3 border-t border-border">
        <button onClick={logout} className="w-full sidebar-link text-error hover:bg-error/10">
          <LogOut size={18} />
          <span className="text-sm">Deconnexion</span>
        </button>
      </div>
    </aside>
  );
}
