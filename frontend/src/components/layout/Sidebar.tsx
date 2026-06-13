import { useNavigate, useLocation } from '@tanstack/react-router';
import { LayoutDashboard, FolderOpen, FileText, MessageSquare, Settings, LogOut, Building2, Shield, Users } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/services', label: 'Services', icon: FolderOpen },
  { path: '/documents', label: 'Documents', icon: FileText },
  { path: '/chat', label: 'Chat', icon: MessageSquare },
  { path: '/settings', label: 'Parametres', icon: Settings },
];

const adminNavItems = [
  { path: '/admin/tenants', label: 'Tenants', icon: Shield },
  { path: '/admin/users', label: 'Utilisateurs', icon: Users },
  { path: '/admin/documents', label: 'Documents', icon: FileText },
];

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { tenant, logout, user } = useAuth();

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

      {user?.is_super_admin && (
        <div className="px-3 py-2 border-t border-border">
          <p className="text-xs font-semibold text-text-muted/60 uppercase tracking-wider px-2 mb-2">Admin</p>
          <nav className="space-y-1">
            {adminNavItems.map(({ path, label, icon: Icon }) => {
              const isActive = location.pathname === path || location.pathname.startsWith(path + '/');
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
        </div>
      )}

      <div className="p-3 border-t border-border">
        <button onClick={logout} className="w-full sidebar-link text-error hover:bg-error/10">
          <LogOut size={18} />
          <span className="text-sm">Deconnexion</span>
        </button>
      </div>
    </aside>
  );
}
