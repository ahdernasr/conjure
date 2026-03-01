export interface App {
  id: string;
  name: string;
  description: string;
  theme_color: string;
  created_at: string;
  updated_at: string;
  status: string;
  version: number;
}

export interface AppListResponse {
  apps: App[];
  count: number;
}

// Phase 2+: populated by generated apps
export interface AppSchema {
  app_id: string;
  name: string;
  capabilities: string[];
  data_shape: Record<string, string>;
  actions: Record<string, string>;
}

// Phase 2+: data synced from localStorage
export interface AppData {
  [key: string]: unknown;
}
