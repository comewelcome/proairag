# frontend/

## Purpose

React dashboard SPA for ProAiRag. Provides a web interface for managing tenants (entreprises), departments (services), documents, chat conversations, and RAG settings. Built with Vite + React + TypeScript + TailwindCSS v4.

## Ownership

Owns the entire frontend application: pages, components, routing, state management, and API integration. Build output (dist/) is served by the FastAPI backend.

## Local Contracts

- React 19 + TypeScript with strict mode
- Vite as build tool with TailwindCSS v4 plugin
- TanStack Router for routing (no React Router)
- Axios for HTTP requests with JWT interceptor
- Sonner for toast notifications
- Lucide React for icons
- Dark theme with custom color palette (#0a0a0f background, #6366f1 accent)
- All API calls go through `/api/` prefix (proxied to backend in dev)

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Login | /login | JWT authentication (email + password) |
| Dashboard | / | Overview with stats and quick actions |
| Services | /services | CRUD for departments (create, edit, delete) |
| Documents | /documents | File upload (drag & drop), list with filters |
| Chat | /chat | ChatGPT-style interface with sessions and sources |
| Settings | /settings | RAG configuration (chunk size, LLM provider, etc.) |

## Architecture

```
frontend/
├── src/
│   ├── main.tsx                 # Entry point + AuthProvider
│   ├── router.tsx               # TanStack Router config (6 routes)
│   ├── index.css                # TailwindCSS + custom theme
│   ├── types/index.ts           # TypeScript interfaces (User, Tenant, Document, etc.)
│   ├── lib/api.ts               # Axios client with JWT interceptor
│   ├── hooks/useAuth.tsx        # Auth context (login/logout/tenant selection)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Layout.tsx       # Global layout (sidebar + header + content)
│   │   │   ├── Sidebar.tsx      # Navigation sidebar (5 sections + logout)
│   │   │   └── Header.tsx       # Header with title + user email
│   │   └── common/
│   │       ├── Modal.tsx        # Reusable modal dialog
│   │       ├── EmptyState.tsx   # Empty state placeholder
│   │       ├── ProtectedRoute.tsx # Auth guard for protected routes
│   │       ├── LazySuspense.tsx # Loading fallback
│   │       └── Toast.tsx        # Sonner toast notifications
│   └── pages/
│       ├── Login.tsx            # Login form
│       ├── Dashboard.tsx        # Stats overview + quick actions
│       ├── Services.tsx         # Department CRUD
│       ├── Documents.tsx        # File upload + document list
│       ├── Chat.tsx             # Chat interface with sessions
│       └── Settings.tsx         # RAG settings form
├── vite.config.ts               # Vite config with Tailwind + API proxy
├── tsconfig.json                # TypeScript config (strict mode)
└── dist/                        # Build output (served by FastAPI)
```

## Work Guidance

- Pages should be thin — delegate logic to hooks and API calls
- Use `useAuth()` hook for auth state (user, tenant, login, logout)
- Use `api` client from `src/lib/api.ts` for all HTTP requests
- Components should use TailwindCSS utility classes (no inline styles)
- New pages must be registered in `src/router.tsx`
- Modal dialogs use the shared `Modal` component
- Toast notifications use `sonner` toast

## Verification

- `npm run build` — TypeScript check + Vite build
- `npm run dev` — Development server with hot reload (port 5173)
- All pages must compile without TypeScript errors

## Child DOX Index

No child DOX files yet.
