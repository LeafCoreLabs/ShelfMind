import { request, User } from "./client";

export interface PlatformStats {
  total_stores: number;
  active_users: number;
  total_transactions: number;
  forecasts_generated: number;
  signals_live: number;
  platform_revenue: number;
  onboarding_drafts_pending: number;
}

export interface StoreRow {
  id: number;
  name: string;
  location: string;
  lat: number;
  lon: number;
  phone: string | null;
  business_type: string | null;
  is_active: boolean;
  owner_count: number;
  transaction_count: number;
  revenue: number;
}

export interface StoreUpdate {
  name?: string;
  location?: string;
  lat?: number;
  lon?: number;
  phone?: string | null;
  business_type?: string | null;
  is_active?: boolean;
}

export const adminApi = {
  getStats: () => request<PlatformStats>("/admin/stats"),
  getUsers: (params?: { role?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.role) q.set("role", params.role);
    if (params?.search) q.set("search", params.search);
    const qs = q.toString();
    return request<{ users: User[] }>(`/admin/users${qs ? `?${qs}` : ""}`);
  },
  deactivateUser: (id: number) => request<{ deactivated: boolean }>(`/admin/users/${id}`, { method: "DELETE" }),
  getStores: () => request<{ stores: StoreRow[] }>("/admin/stores"),
  deactivateStore: (id: number) =>
    request<{ deactivated: boolean }>(`/admin/stores/${id}`, { method: "DELETE" }),
  updateStore: (id: number, data: StoreUpdate) =>
    request<{ updated: boolean; store_id: number }>(`/admin/stores/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  startOnboarding: () => request<{ draft_id: number; step: number }>("/admin/onboarding/start", { method: "POST", body: "{}" }),
  saveOnboardingStep: (draftId: number, step: number, data: Record<string, unknown>) =>
    request<{ draft_id: number; step: number; saved: number }>(
      `/admin/onboarding/${draftId}/step/${step}`,
      { method: "PUT", body: JSON.stringify({ data }) }
    ),
  completeOnboarding: (draftId: number) =>
    request<{ store_id: number; user_id: number; email: string }>(
      `/admin/onboarding/${draftId}/complete`,
      { method: "POST", body: "{}" }
    ),
  triggerJob: (job: "forecasts" | "signals" | "benchmarks" | "export") =>
    request<{ task_id: string; status: string }>(`/admin/jobs/${job}`, { method: "POST", body: "{}" }),
  getSystemHealth: () =>
    request<{ overall: string; checked_at: string; checks: { name: string; status: string; latency_ms: number; detail: Record<string, unknown> }[] }>(
      "/admin/system-health"
    ),
};
