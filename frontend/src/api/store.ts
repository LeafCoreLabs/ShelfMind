import { request, getToken } from "./client";

export interface UrgentAction {
  type: string;
  label: string;
  href: string;
}

export interface StoreWeather {
  location: string;
  lat: number;
  lon: number;
  source: string;
  fetched_at: string;
  current: {
    temp_c: number;
    condition: string;
    precipitation_mm?: number;
    humidity_pct?: number;
    wind_kmh?: number;
  };
  daily: {
    date: string;
    temp_max_c: number;
    temp_min_c: number;
    precip_mm: number;
    condition: string;
  }[];
  retail_signals: { category: string; impact: string; description: string }[];
}

export interface StoreOverview {
  store_id: number;
  store_name: string;
  store_location: string;
  product_count: number;
  low_stock_count: number;
  customer_count: number;
  total_revenue: number;
  weekly_revenue: number;
  top_seller: string | null;
  unpaid_invoices: number;
  unacked_alerts: number;
  forecasts_available: number;
  anomaly_count: number;
  signals_active: number;
  ai_queries: number;
  top_local_signal: { title: string; description: string; category: string } | null;
  urgent_actions: UrgentAction[];
  weather: StoreWeather | null;
}

export interface ProductRow {
  id: number;
  sku: string;
  name: string;
  category: string;
  list_price: number;
  cost_price: number;
  stock_on_hand: number;
  reorder_level: number;
  low_stock: boolean;
}

export interface CustomerRow {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  segment: string;
  total_spent: number;
  last_purchase_at: string | null;
}

export interface InvoiceRow {
  id: number;
  invoice_number: string;
  status: string;
  customer_id: number | null;
  subtotal: number;
  tax_amount: number;
  cgst_amount?: number;
  sgst_amount?: number;
  igst_amount?: number;
  place_of_supply?: string | null;
  total: number;
  issued_at: string;
  gstin?: string | null;
}

export interface InvoiceDetail extends InvoiceRow {
  store_name: string;
  store_location: string;
  customer_name: string;
  lines: { description: string; hsn_code: string | null; quantity: number; unit_price: number; line_total: number }[];
}

export interface VendorRow {
  id: number;
  name: string;
  phone: string | null;
  gstin: string | null;
  email: string | null;
}

export interface PurchaseRow {
  id: number;
  vendor_id: number;
  vendor_name: string;
  status: string;
  subtotal: number;
  tax: number;
  total: number;
  ordered_at: string;
  received_at: string | null;
  lines: { product_id: number; qty: number; unit_cost: number; line_total: number }[];
}

export interface PnlReport {
  from: string;
  to: string;
  revenue: number;
  cogs: number;
  gross_margin: number;
  margin_pct: number;
  tax_collected: number;
}

export interface DayBookEntry {
  time: string;
  type: string;
  description: string;
  debit: number;
  credit: number;
}

export interface SaleRow {
  id: number;
  sku: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  total: number;
  customer_id: number | null;
  sold_at: string;
}

export interface AdminAnomaly {
  id: string;
  severity: string;
  title: string;
  delta_pct?: number;
  signal_cause?: string;
  recommended_action?: string;
}

export interface Recommendation {
  sku: string;
  product_name: string;
  action: string;
  delta_pct: number;
  rationale: string;
  confidence: number;
}

export interface StoreChatSuggestion {
  label: string;
  value?: string;
  command?: string;
}

export interface StoreChatAction {
  label: string;
  command?: string;
  href?: string;
}

export interface StoreChatResponse {
  reply: string;
  intent: string;
  session_id: string;
  status: "complete" | "needs_input" | "confirm";
  missing?: string[] | null;
  suggestions?: StoreChatSuggestion[] | null;
  result?: Record<string, unknown> | null;
  data?: Record<string, unknown> | null;
  actions?: StoreChatAction[] | null;
}

export const storeApi = {
  getOverview: () => request<StoreOverview>("/store/overview"),
  getWeather: (refresh = false) => request<StoreWeather>(`/store/weather${refresh ? "?refresh=true" : ""}`),
  getSummary: () => request<Record<string, unknown>>("/store/insights/summary"),
  getForecasts: () => request<{ forecasts: Record<string, unknown>[] }>("/store/insights/forecasts"),
  getHeatmap: () => request<{ heatmap: Record<string, unknown>[]; store_location?: string }>("/store/insights/heatmap"),
  getSignals: () =>
    request<{ signals: Record<string, unknown>[]; store_location?: string; weather?: StoreWeather | null }>(
      "/store/insights/signals"
    ),
  getBenchmarks: () => request<{ benchmarks: Record<string, unknown>[] }>("/store/insights/benchmarks"),
  getAccuracy: () => request<Record<string, unknown>>("/store/insights/accuracy"),
  getAnomalies: () => request<{ anomalies: AdminAnomaly[]; count: number }>("/store/insights/anomalies"),
  aiQuery: (query: string) =>
    request<{ recommendations: Recommendation[] }>("/store/ai/query", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  chat: (message: string, sessionId?: string | null, fresh = false) =>
    request<StoreChatResponse>("/store/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId ?? undefined, fresh }),
    }),
  explain: (data: { title: string; detail: string; insight_type?: string }) =>
    request<{ explanation: string; recommended_action: string }>("/store/ai/explain", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getAlerts: () => request<{ alerts: { id: number; severity: string; title: string; message: string; acknowledged: boolean }[] }>("/store/alerts"),
  acknowledgeAlert: (id: number) =>
    request<{ acknowledged: boolean }>(`/store/alerts/${id}/acknowledge`, { method: "POST", body: "{}" }),
  getProducts: () => request<{ products: ProductRow[] }>("/store/inventory/products"),
  getLowStock: () => request<{ products: ProductRow[] }>("/store/inventory/low-stock"),
  updateProduct: (id: number, data: Partial<ProductRow>) =>
    request<{ updated: boolean }>(`/store/inventory/products/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  adjustStock: (id: number, delta: number) =>
    request<{ stock_on_hand: number }>(`/store/inventory/products/${id}/adjust-stock`, {
      method: "POST",
      body: JSON.stringify({ delta }),
    }),
  getCustomers: () => request<{ customers: CustomerRow[] }>("/store/customers"),
  createCustomer: (data: { name: string; email?: string; phone?: string; segment?: string }) =>
    request<{ id: number }>("/store/customers", { method: "POST", body: JSON.stringify(data) }),
  updateCustomer: (id: number, data: { name?: string; email?: string; phone?: string; segment?: string }) =>
    request<{ updated: boolean }>(`/store/customers/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteCustomer: (id: number) => request<{ deleted: boolean }>(`/store/customers/${id}`, { method: "DELETE" }),
  getSales: () => request<{ sales: SaleRow[] }>("/store/sales"),
  createSale: (data: { product_id: number; quantity: number; unit_price?: number; customer_id?: number }) =>
    request<{ id: number; total: number }>("/store/sales", { method: "POST", body: JSON.stringify(data) }),
  createBatchSale: (data: { lines: { product_id: number; quantity: number; unit_price?: number }[]; customer_id?: number }) =>
    request<{ transaction_ids: number[]; total: number }>("/store/sales/batch", { method: "POST", body: JSON.stringify(data) }),
  getInvoices: () => request<{ invoices: InvoiceRow[]; store_gstin?: string | null }>("/store/billing/invoices"),
  getInvoice: (id: number) => request<InvoiceDetail>(`/store/billing/invoices/${id}`),
  createInvoiceFromSale: (transactionId: number) =>
    request<{ invoice_id: number; invoice_number: string; total: number }>(
      `/store/billing/invoices/from-sale/${transactionId}`,
      { method: "POST", body: "{}" }
    ),
  createInvoiceFromSales: (transactionIds: number[]) =>
    request<{ invoice_id: number; invoice_number: string; total: number }>("/store/billing/invoices/from-sales", {
      method: "POST",
      body: JSON.stringify({ transaction_ids: transactionIds }),
    }),
  payInvoice: (id: number, amount: number, method: string) =>
    request<{ status: string }>(`/store/billing/invoices/${id}/pay`, {
      method: "POST",
      body: JSON.stringify({ amount, method }),
    }),
  getSettings: () => request<Record<string, unknown>>("/store/settings"),
  updateSettings: (data: Record<string, unknown>) =>
    request<{ updated: boolean }>("/store/settings", { method: "PATCH", body: JSON.stringify(data) }),
  getVendors: () => request<{ vendors: VendorRow[] }>("/store/vendors"),
  createVendor: (data: { name: string; phone?: string; gstin?: string; email?: string }) =>
    request<{ id: number; name: string }>("/store/vendors", { method: "POST", body: JSON.stringify(data) }),
  getPurchases: () => request<{ purchases: PurchaseRow[] }>("/store/purchases"),
  createPurchase: (data: { vendor_id: number; lines: { product_id: number; qty: number; unit_cost?: number }[] }) =>
    request<{ id: number; total: number; status: string }>("/store/purchases", { method: "POST", body: JSON.stringify(data) }),
  receivePurchase: (id: number) =>
    request<{ id: number; status: string }>(`/store/purchases/${id}/receive`, { method: "POST", body: "{}" }),
  getPnl: (from?: string, to?: string) => {
    const params = new URLSearchParams();
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    const q = params.toString();
    return request<PnlReport>(`/store/reports/pnl${q ? `?${q}` : ""}`);
  },
  getDayBook: (date?: string) =>
    request<{ date: string; entries: DayBookEntry[] }>(`/store/reports/daybook${date ? `?date=${date}` : ""}`),
  exportReport: () => request<{ download_url: string }>("/store/reports/export", { method: "POST", body: "{}" }),
  importCsv: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const token = getToken();
    const res = await fetch("/api/store/reports/import-csv", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) throw new Error("Import failed");
    return res.json() as Promise<{ imported: number }>;
  },
};
