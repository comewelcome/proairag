import { Outlet } from '@tanstack/react-router';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { AppToaster } from '../common/Toast';

export function Layout() {
  return (
    <div className="flex h-screen bg-bg">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="ProAiRag Dashboard" />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
      <AppToaster />
    </div>
  );
}
