import { Toaster } from 'sonner';

export function AppToaster() {
  return <Toaster position="top-right" theme="dark" toastOptions={{
    style: { background: '#1a1a2e', border: '1px solid #2a2a3e', color: '#e2e8f0' },
  }} />;
}
