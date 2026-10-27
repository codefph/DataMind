import { create } from "zustand";

import {
  createConversation,
  deleteConversation as deleteConversationRequest,
  listCharts,
  listConversations,
  listMessages,
  queryConversation,
  type Conversation,
  type MessageItem,
  updateConversation as updateConversationRequest,
} from "../api/client";

export interface ChartItem {
  chart_id: string;
  title: string;
  chart_type: string;
  echarts_option: Record<string, unknown>;
  data?: { columns: string[]; rows: Record<string, unknown>[] };
  sql?: string;
}

export interface InsightItem {
  chart_id: string;
  kind: string;
  title: string;
  body: string;
}

export interface NarrativeItem {
  summary: string;
  highlights: string[];
}

interface ChatState {
  conversations: Conversation[];
  activeConversationId: number | null;
  messages: MessageItem[];
  charts: ChartItem[];
  insights: InsightItem[];
  narrative: NarrativeItem | null;
  sqlMap: Record<string, string>;
  datasourceId: number | null;
  loading: boolean;
  stage: string;
  error: string | null;
  loadConversations: () => Promise<void>;
  createConversation: () => Promise<number | null>;
  renameConversation: (id: number, title: string) => Promise<void>;
  deleteConversation: (id: number) => Promise<void>;
  selectConversation: (id: number) => Promise<void>;
  setDatasource: (id: number | null) => void;
  send: (question: string) => Promise<void>;
  loadBoard: (charts: ChartItem[], insights: InsightItem[]) => void;
}

export const useChatStore = create<ChatState>()((set, get) => {
  async function loadConversationData(id: number) {
    const [messages, charts] = await Promise.all([
      listMessages(id),
      listCharts(id),
    ]);
    const chartItems: ChartItem[] = charts.map((c) => ({
      chart_id: c.chart_id,
      title: c.title,
      chart_type: c.chart_type,
      echarts_option: c.echarts_option,
      sql: c.sql,
    }));
    const insights: InsightItem[] = [];
    for (const c of charts) {
      for (const item of c.insight?.items ?? []) {
        insights.push(item as unknown as InsightItem);
      }
    }
    let narrative: NarrativeItem | null = null;
    for (const msg of messages) {
      if (msg.role === "assistant" && msg.meta?.narrative) {
        narrative = msg.meta.narrative as unknown as NarrativeItem;
      }
    }
    set({ messages, charts: chartItems, insights, sqlMap: {}, narrative });
  }

  return {
    conversations: [],
    activeConversationId: null,
    messages: [],
    charts: [],
    insights: [],
    narrative: null,
    sqlMap: {},
    datasourceId: null,
    loading: false,
    stage: "",
    error: null,

    loadConversations: async () => {
      try {
        set({ conversations: await listConversations() });
      } catch (err) {
        set({ error: err instanceof Error ? err.message : String(err) });
      }
    },

    createConversation: async () => {
      const { datasourceId } = get();
      try {
        const conv = await createConversation(datasourceId);
        await get().loadConversations();
        set({ activeConversationId: conv.id });
        await loadConversationData(conv.id);
        return conv.id;
      } catch (err) {
        set({ error: err instanceof Error ? err.message : String(err) });
        return null;
      }
    },

    renameConversation: async (id, title) => {
      try {
        const updated = await updateConversationRequest(id, title);
        set((state) => ({
          conversations: state.conversations.map((conversation) =>
            conversation.id === id ? updated : conversation,
          ),
        }));
      } catch (err) {
        set({ error: err instanceof Error ? err.message : String(err) });
      }
    },

    deleteConversation: async (id) => {
      try {
        await deleteConversationRequest(id);
        const conversations = get().conversations.filter(
          (conversation) => conversation.id !== id,
        );
        const isActive = get().activeConversationId === id;
        set({ conversations, error: null });

        if (isActive) {
          const nextConversation = conversations[0];
          set({
            activeConversationId: nextConversation?.id ?? null,
            messages: [],
            charts: [],
            insights: [],
            narrative: null,
            sqlMap: {},
          });
          if (nextConversation) {
            await loadConversationData(nextConversation.id);
          }
        }
      } catch (err) {
        set({ error: err instanceof Error ? err.message : String(err) });
      }
    },

    selectConversation: async (id) => {
      set({ activeConversationId: id, error: null });
      await loadConversationData(id);
    },

    setDatasource: (id) => set({ datasourceId: id }),

    send: async (question) => {
      let { activeConversationId, datasourceId } = get();
      if (activeConversationId == null) {
        const created = await get().createConversation();
        if (created == null) return;
        activeConversationId = created;
      }
      const currentDatasourceId = datasourceId ?? get().datasourceId;
      if (currentDatasourceId == null) {
        set({ error: "请先选择一个数据源再提问" });
        return;
      }
      set({
        loading: true,
        stage: "",
        error: null,
        charts: [],
        insights: [],
        narrative: null,
        sqlMap: {},
      });
      try {
        await queryConversation(activeConversationId, question, (event, data) => {
          const payload = data as Record<string, unknown>;
          if (event === "sql") {
            set((s) => ({
              sqlMap: {
                ...s.sqlMap,
                [payload.chart_id as string]: payload.sql as string,
              },
            }));
          } else if (event === "chart") {
            set({ stage: "正在渲染图表…" });
            set((s) => {
              const chart = payload as unknown as ChartItem;
              chart.sql = s.sqlMap[chart.chart_id];
              return {
                charts: [
                  ...s.charts.filter((c) => c.chart_id !== chart.chart_id),
                  chart,
                ],
              };
            });
          } else if (event === "insight") {
            set((s) => ({
              insights: [...s.insights, payload as unknown as InsightItem],
            }));
          } else if (event === "narrative") {
            set({ narrative: payload as unknown as NarrativeItem, stage: "正在生成整体解读…" });
          } else if (event === "error") {
            set({ error: String(payload.message ?? "未知错误"), stage: "" });
          }
          if (event === "sql") set({ stage: "正在生成查询 SQL…" });
          if (event === "executing") set({ stage: "正在查询数据库…" });
          if (event === "retrieved") set({ stage: "已定位相关表和字段…" });
          if (event === "done") set({ stage: "" });
        });
        await loadConversationData(activeConversationId);
      } catch (err) {
        set({ error: err instanceof Error ? err.message : String(err) });
      } finally {
        set({ loading: false, stage: "" });
      }
    },

    loadBoard: (charts, insights) =>
      set({ charts, insights, sqlMap: {}, narrative: null }),
  };
});
