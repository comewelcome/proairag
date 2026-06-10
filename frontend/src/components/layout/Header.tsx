import { UserCircle } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export function Header({ title }: { title: string }) {
  const { user } = useAuth();

  return (
    <header className="h-14 border-b border-border bg-bg-secondary/50 backdrop-blur flex items-center justify-between px-6">
      <h1 className="text-base font-semibold text-text">{title}</h1>
      <div className="flex items-center gap-3">
        <span className="text-sm text-text-muted">{user?.email}</span>
        <UserCircle className="text-text-muted" size={28} />
      </div>
    </header>
  );
}
