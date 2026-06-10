import { ReactNode } from 'react';

export function EmptyState({ icon, title, description, action }: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      {icon && <div className="mb-4 text-text-muted/50">{icon}</div>}
      <h3 className="text-lg font-medium text-text mb-1">{title}</h3>
      {description && <p className="text-text-muted text-sm mb-4">{description}</p>}
      {action && <div>{action}</div>}
    </div>
  );
}
