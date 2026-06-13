import { createRouter, createRootRoute, createRoute, Outlet } from '@tanstack/react-router';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { Layout } from './components/layout/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Services } from './pages/Services';
import { Documents } from './pages/Documents';
import { Chat } from './pages/Chat';
import { Settings } from './pages/Settings';
import { AdminTenants } from './pages/AdminTenants';
import { AdminUsers } from './pages/AdminUsers';
import { AdminDocuments } from './pages/AdminDocuments';

const rootRoute = createRootRoute({
  component: () => <Outlet />,
});

// Public routes
const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: Login,
});

// Protected layout
const layoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'layout',
  component: () => (
    <ProtectedRoute>
      <Layout />
    </ProtectedRoute>
  ),
});

// Dashboard pages
const indexRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/',
  component: Dashboard,
});

const servicesRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/services',
  component: Services,
});

const documentsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/documents',
  component: Documents,
});

const chatRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/chat',
  component: Chat,
});

const settingsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/settings',
  component: Settings,
});

// Admin routes
const adminTenantsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/admin/tenants',
  component: AdminTenants,
});

const adminUsersRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/admin/users',
  component: AdminUsers,
});

const adminDocumentsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/admin/documents',
  component: AdminDocuments,
});

const routeTree = rootRoute.addChildren([
  loginRoute,
  layoutRoute.addChildren([
    indexRoute, servicesRoute, documentsRoute, chatRoute, settingsRoute,
    adminTenantsRoute, adminUsersRoute, adminDocumentsRoute,
  ]),
]);

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

export const router = createRouter({ routeTree, defaultPreload: false });
