import { Suspense, ReactNode } from 'react';

export function LazySuspense({ children, fallback }: { children: ReactNode; fallback?: ReactNode }) {
  return (
    <Suspense fallback={fallback || <div className="p-8 text-text-muted">Chargement...</div>}>
      {children}
    </Suspense>
  );
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <span className="text-text-muted text-sm">Chargement...</span>
      </div>
    </div>
  );
}
