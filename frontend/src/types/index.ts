export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_tenant_admin: boolean;
  is_super_admin: boolean;
  tenant_id?: string;
}

export interface Tenant {
  id: string;
  name: string;
  api_key?: string;
  is_active: boolean;
  created_at?: string;
}

export interface Department {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  created_at?: string;
}

export interface DocumentItem {
  id: string;
  tenant_id: string;
  department_id?: string;
  title: string;
  source?: string;
  content_type: string;
  created_at?: string;
}

export interface Conversation {
  id: string;
  tenant_id: string;
  department_id?: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<{ doc_id: string; doc_title: string; score: number }>;
  graph_context?: Array<{ entity: string; type: string; relationships: string[] }>;
  created_at: string;
}

export interface RagSettings {
  chunk_size: number;
  chunk_overlap: number;
  top_k: number;
  embedding_model: string;
  llm_provider: 'openai' | 'ollama' | 'fallback';
  llm_model?: string;
  openai_api_key?: string;
  openai_api_base?: string;
  ollama_base_url?: string;
  llm_max_tokens?: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SystemStats {
  document_count: number;
  chunk_count: number;
  entity_count: number;
  postgres_connected: boolean;
  neo4j_connected: boolean;
}
