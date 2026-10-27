const BASE = "/api";

export interface Datasource {
  id: number;
  name: string;
  type: string;
  host: string;
  port: number;
  database: string;
}

export interface DashboardSummary {
  id: number;
  title: string;
  created_at: string;
  layout?: Record<string, unknown>;
}

export interface Conversation {
  id: number;
  title: string;
  datasource_id: number | null;
  created_at: string;
}

export interface MessageItem {
  id: number;
  role: string;
  content: string;
  meta?: Record<string, unknown> | null;
  created_at: string;
}

export interface ChartPayload {
  chart_id: string;
  title: string;
  chart_type: string;
  sql: string;
  echarts_option: Record<string, unknown>;
  insight?: { items: Record<string, unknown>[] };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

async function streamSSE(
  path: string,
  init: RequestInit,
  onEvent: (event: string, data: unknown) => void,
): Promise<void> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok || !res.body) {
    throw new Error(`HTTP ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);

      let event = "message";
      let data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) onEvent(event, JSON.parse(data));
    }
  }
}

export const listDatasources = () => request<Datasource[]>("/datasources");

export const createDatasource = (body: {
  name: string;
  type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
}) =>
  request<Datasource>("/datasources", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const deleteDatasource = (id: number) =>
  request<void>(`/datasources/${id}`, { method: "DELETE" });

export const syncDatasource = (id: number) =>
  request<void>(`/datasources/${id}/sync`, { method: "POST" });

export const saveDashboard = (
  title: string,
  layout: Record<string, unknown>,
) =>
  request<DashboardSummary>("/dashboards", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, layout }),
  });

export const listDashboards = () => request<DashboardSummary[]>("/dashboards");

export const getDashboard = (id: number) =>
  request<DashboardSummary>(`/dashboards/${id}`);

export const createConversation = (datasourceId: number | null) =>
  request<Conversation>("/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ datasource_id: datasourceId }),
  });

export const listConversations = () => request<Conversation[]>("/conversations");

export const updateConversation = (id: number, title: string) =>
  request<Conversation>(`/conversations/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });

export const deleteConversation = (id: number) =>
  request<void>(`/conversations/${id}`, { method: "DELETE" });

export const listMessages = (id: number) =>
  request<MessageItem[]>(`/conversations/${id}/messages`);

export const listCharts = (id: number) =>
  request<ChartPayload[]>(`/conversations/${id}/charts`);

export const updateChart = (
  chartId: string,
  chartType: string,
  echartsOption: Record<string, unknown>,
) =>
  request<Record<string, unknown>>(`/charts/${chartId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chart_type: chartType, echarts_option: echartsOption }),
  });

export function queryConversation(
  id: number,
  question: string,
  onEvent: (event: string, data: unknown) => void,
) {
  return streamSSE(
    `/conversations/${id}/query`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    },
    onEvent,
  );
}
