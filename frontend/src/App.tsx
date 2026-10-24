import { useEffect, useMemo, useState, type ReactNode } from "react";

import {
  createDatasource,
  deleteDatasource,
  getDashboard,
  listDashboards,
  listDatasources,
  syncDatasource,
  updateChart,
  type DashboardSummary,
  type Datasource,
} from "./api/client";
import EChart from "./charts/EChart";
import { CHART_TYPE_OPTIONS, convertOption } from "./charts/convertType";
import { resolveOption } from "./charts/fallbackOption";
import { exportPDF, exportPNG } from "./export/exportCharts";
import {
  useChatStore,
  type ChartItem,
  type InsightItem,
} from "./stores/chat";

const SUGGESTIONS = [
  "各区域成交额是多少",
  "每日成交额趋势",
  "各渠道订单量排名",
  "对比华东与其他区域的成交额",
];

function ChartCard({
  chart,
  onTypeChange,
}: {
  chart: ChartItem;
  onTypeChange: (
    chartId: string,
    chartType: string,
    option: Record<string, unknown>,
  ) => void;
}) {
  const [showSql, setShowSql] = useState(false);
  const [chartType, setChartType] = useState(chart.chart_type);

  useEffect(() => setChartType(chart.chart_type), [chart.chart_type]);

  const option = useMemo(
    () =>
      chartType === chart.chart_type
        ? resolveOption(chart)
        : convertOption(chart, chartType),
    [chart, chartType],
  );

  const typeOptions = CHART_TYPE_OPTIONS.some(
    (o) => o.value === chart.chart_type,
  )
    ? CHART_TYPE_OPTIONS
    : [{ value: chart.chart_type, label: chart.chart_type }, ...CHART_TYPE_OPTIONS];

  const handleType = (value: string) => {
    setChartType(value);
    if (value !== chart.chart_type) {
      onTypeChange(chart.chart_id, value, convertOption(chart, value));
    }
  };

  return (
    <div className="chart-card">
      <div className="chart-card-head">
        <div className="chart-card-title">
          <span className="chart-kind-dot" data-kind={chart.chart_type} />
          <strong>{chart.title}</strong>
        </div>
        <div className="chart-card-actions">
          <select
            className="type-select"
            value={chartType}
            onChange={(e) => handleType(e.target.value)}
            aria-label="图表类型"
          >
            {typeOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <button className="icon-btn" onClick={() => setShowSql((v) => !v)}>
            {showSql ? "SQL ▴" : "SQL"}
          </button>
          <button className="icon-btn" onClick={() => exportPNG([chart])}>
            PNG
          </button>
        </div>
      </div>
      {showSql && <pre className="sql-box">{chart.sql || "(无 SQL)"}</pre>}
      <EChart chartId={chart.chart_id} option={option} />
    </div>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="icon-btn" onClick={onClose}>
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

const EMPTY_FORM = {
  name: "",
  type: "postgresql",
  host: "127.0.0.1",
  port: "5432",
  database: "",
  username: "",
  password: "",
};

export default function App() {
  const [datasources, setDatasources] = useState<Datasource[]>([]);
  const [dashboards, setDashboards] = useState<DashboardSummary[]>([]);
  const [question, setQuestion] = useState("");
  const [notice, setNotice] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!notice) return;
    const id = window.setTimeout(() => setNotice(""), 2600);
    return () => window.clearTimeout(id);
  }, [notice]);

  const {
    conversations,
    activeConversationId,
    messages,
    charts,
    insights,
    narrative,
    datasourceId,
    setDatasource,
    loading,
    stage,
    error,
    loadConversations,
    createConversation,
    selectConversation,
    send,
    loadBoard,
  } = useChatStore();

  const refreshDatasources = () =>
    listDatasources()
      .then(setDatasources)
      .catch(() => setDatasources([]));

  const refreshDashboards = () =>
    listDashboards()
      .then(setDashboards)
      .catch(() => setDashboards([]));

  useEffect(() => {
    refreshDatasources();
    refreshDashboards();
    loadConversations();
  }, []);

  const canAsk = Boolean(datasourceId) && !loading;

  const submit = async () => {
    if (!question.trim() || loading) return;
    if (datasourceId == null) {
      setNotice("请先在左侧选择或添加数据源");
      return;
    }
    await send(question.trim());
    setQuestion("");
  };

  const handleSuggestion = async (q: string) => {
    if (datasourceId == null) {
      setNotice("请先在左侧选择或添加数据源");
      return;
    }
    await send(q);
  };

  const startNewConversation = async () => {
    if (datasourceId == null) {
      setNotice("请先选择数据源后再新建会话");
      return;
    }
    await createConversation();
    setSidebarOpen(false);
  };

  const addDatasource = async () => {
    setBusy(true);
    try {
      await createDatasource({
        name: form.name,
        type: form.type,
        host: form.host,
        port: Number(form.port),
        database: form.database,
        username: form.username,
        password: form.password,
      });
      setNotice("数据源已添加，请点击「同步知识库」建立索引");
      setShowAdd(false);
      setForm(EMPTY_FORM);
      refreshDatasources();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const syncSelected = async () => {
    if (datasourceId == null) return;
    setBusy(true);
    try {
      await syncDatasource(datasourceId);
      setNotice("知识库同步完成");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const removeSelected = async () => {
    if (datasourceId == null) return;
    try {
      await deleteDatasource(datasourceId);
      setDatasource(null);
      setNotice("数据源已删除");
      refreshDatasources();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : String(err));
    }
  };

  const loadDashboard = async (id: number) => {
    try {
      const board = await getDashboard(id);
      const layout = board.layout ?? {};
      loadBoard(
        (layout.charts as ChartItem[]) ?? [],
        (layout.insights as InsightItem[]) ?? [],
      );
      setNotice(`已载入看板「${board.title}」`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : String(err));
    }
  };

  const handleTypeChange = async (
    chartId: string,
    chartType: string,
    option: Record<string, unknown>,
  ) => {
    try {
      await updateChart(chartId, chartType, option);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : String(err));
    }
  };

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId,
  );
  const activeDatasource = datasources.find((d) => d.id === datasourceId);

  return (
    <div className="shell">
      <aside className={sidebarOpen ? "sidebar open" : "sidebar"}>
        <div className="brand" aria-label="DataMind logo">
          <div className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 64 64" role="img">
              <defs>
                <linearGradient id="brandGradient" x1="0%" x2="100%" y1="0%" y2="100%">
                  <stop offset="0%" stopColor="#60a5fa" />
                  <stop offset="100%" stopColor="#2563eb" />
                </linearGradient>
              </defs>
              <path d="M16 26l10-10 12 12 12-20 14 28H16z" fill="rgba(255,255,255,0.18)" />
              <path d="M14 38c6-16 11-24 18-24 9 0 11 8 17 19 3 7 7 13 15 17H14c0-4 0-8 0-12z" fill="url(#brandGradient)" opacity="0.22" />
              <path d="M12 16h18l-8 12H12V16zm19 0h21v11H31V16zm-8 14h27v12H23V30zm-11 14h38v8H12v-8z" fill="url(#brandGradient)" />
            </svg>
          </div>
          <div className="brand-wordmark">
            <span className="brand-name">DataMind</span>
            <span className="brand-tag">AI BI</span>
          </div>
        </div>

        <button className="primary" onClick={startNewConversation}>
          + 新建会话
        </button>

        <div className="side-section">
          <label className="side-label">数据源</label>
          <select
            value={datasourceId ?? ""}
            onChange={(e) => {
              setDatasource(e.target.value ? Number(e.target.value) : null);
              setSidebarOpen(false);
            }}
          >
            <option value="">选择数据源</option>
            {datasources.map((ds) => (
              <option key={ds.id} value={ds.id}>
                {ds.name} · {ds.type}
              </option>
            ))}
          </select>
          <div className="side-actions">
            <button className="ghost" onClick={syncSelected} disabled={busy}>
              同步知识库
            </button>
            <button className="ghost" onClick={() => setShowAdd(true)}>
              添加数据源
            </button>
            <button className="ghost danger" onClick={removeSelected}>
              删除当前数据源
            </button>
          </div>
        </div>

        <div className="side-section">
          <label className="side-label">会话</label>
          <div className="conv-list">
            {conversations.map((c) => (
              <button
                key={c.id}
                className={
                  c.id === activeConversationId
                    ? "conv-item active"
                    : "conv-item"
                }
                onClick={() => selectConversation(c.id)}
              >
                <span className="conv-name">{c.title}</span>
              </button>
            ))}
            {conversations.length === 0 && (
              <div className="empty-hint">还没有会话</div>
            )}
          </div>
        </div>

        {dashboards.length > 0 && (
          <div className="side-section">
            <label className="side-label">看板</label>
            <div className="conv-list">
              {dashboards.map((d) => (
                <button
                  key={d.id}
                  className="conv-item"
                  onClick={() => loadDashboard(d.id)}
                >
                  <span className="conv-name">{d.title}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </aside>

      <main className="main">
        <header className="topbar">
          <button
            className="icon-btn hamburger"
            onClick={() => setSidebarOpen((v) => !v)}
          >
            <svg width="16" height="12" viewBox="0 0 16 12" aria-hidden="true">
              <line x1="0" y1="1" x2="16" y2="1" stroke="currentColor" strokeWidth="2" />
              <line x1="0" y1="6" x2="16" y2="6" stroke="currentColor" strokeWidth="2" />
              <line x1="0" y1="11" x2="16" y2="11" stroke="currentColor" strokeWidth="2" />
            </svg>
          </button>
          <div className="topbar-title">
            {activeConversation ? activeConversation.title : "开始新的分析"}
          </div>
          <div className="topbar-right">
            {activeDatasource && (
              <span className="badge">{activeDatasource.name}</span>
            )}
            <span className="badge model">DeepSeek</span>
          </div>
        </header>

        <div className="sheet">
        <div className="content">
          {notice && <div className="notice">{notice}</div>}
          {error && <div className="error">出错了：{error}</div>}

          {(activeDatasource || activeConversationId != null || charts.length > 0) && (
            <div className="workspace-summary">
              <div className="summary-card">
                <span className="summary-label">当前数据源</span>
                <strong>{activeDatasource ? activeDatasource.name : "未选择"}</strong>
              </div>
              <div className="summary-card">
                <span className="summary-label">会话状态</span>
                <strong>{activeConversation ? activeConversation.title : "待开始"}</strong>
              </div>
              <div className="summary-card accent">
                <span className="summary-label">分析进度</span>
                <strong>{loading ? stage || "正在分析…" : charts.length > 0 ? "已生成结果" : "等待提问"}</strong>
              </div>
            </div>
          )}

          {activeConversationId == null && charts.length === 0 ? (
            <div className="welcome">
              <div className="welcome-intro">
                <h1>用一句话，得到图表和洞察</h1>
                <p>
                  选择数据源后，直接描述你想看的指标、维度和趋势。系统会检索数据库结构、
                  生成并执行 SQL，返回图表和 BI 解读。
                </p>
                <div className="welcome-steps">
                  <span>描述数据问题</span>
                  <span>自动生成 SQL</span>
                  <span>得到图表与洞察</span>
                </div>
                <div className="suggestions">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} onClick={() => handleSuggestion(s)}>
                      {s}
                    </button>
                  ))}
                </div>
                <div className="welcome-meta">已接入 1 个数据源 · 知识库 73 条</div>
              </div>
              <div className="welcome-example">
                <div className="example-q">各区域成交额是多少</div>
                <pre className="example-sql">
                  {"SELECT region, SUM(gmv) AS gmv\nFROM sales_orders\nGROUP BY region"}
                </pre>
                <div className="bar-list">
                  {[
                    ["华东", "100%", "20,000.50"],
                    ["华南", "56%", "11,200.00"],
                    ["华北", "15%", "3,000.00"],
                  ].map(([label, width, value]) => (
                    <div className="bar-row" key={label}>
                      <span>{label}</span>
                      <i style={{ width }} />
                      <b>{value}</b>
                    </div>
                  ))}
                </div>
                <p className="example-insight">
                  成交额合计 34,200.50，华东贡献 58.5%，集中度偏高。
                </p>
              </div>
            </div>
          ) : (
            <>
              {messages.length > 0 && (
                <div className="chat">
                  {messages.map((m) => (
                    <div
                      key={m.id}
                      className={
                        m.role === "user" ? "bubble user" : "bubble assistant"
                      }
                    >
                      {m.content}
                    </div>
                  ))}
                </div>
              )}

              {loading && (
                <div className="stage">
                  <span className="spinner" />
                  {stage || "正在分析…"}
                </div>
              )}

              {charts.length > 0 && (
                <div className="charts-block">
                  <div className="block-head">
                    <h2>图表</h2>
                    <div className="block-actions">
                      <button className="ghost" onClick={() => exportPNG(charts)}>
                        导出 PNG
                      </button>
                      <button className="ghost" onClick={() => exportPDF(charts)}>
                        导出 PDF
                      </button>
                    </div>
                  </div>
                  <div className="charts-grid">
                    {charts.map((chart) => (
                      <ChartCard
                        key={chart.chart_id}
                        chart={chart}
                        onTypeChange={handleTypeChange}
                      />
                    ))}
                  </div>
                </div>
              )}

              {narrative && (
                <section className="narrative">
                  <div className="narrative-head">
                    <h2>整体解读</h2>
                  </div>
                  <p className="narrative-summary">{narrative.summary}</p>
                  {narrative.highlights.length > 0 && (
                    <ul className="narrative-points">
                      {narrative.highlights.map((h, i) => (
                        <li key={i}>{h}</li>
                      ))}
                    </ul>
                  )}
                </section>
              )}

              {insights.length > 0 && (
                <section className="insights">
                  <h2>BI 洞察</h2>
                  <div className="insight-grid">
                    {insights.map((ins, i) => (
                      <div key={i} className="insight-card">
                        <div className="insight-head">
                          <span className="tag">{ins.kind}</span>
                          <strong>{ins.title}</strong>
                        </div>
                        <p>{ins.body}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>

        <div className="composer">
          <textarea
            value={question}
            placeholder={
              !datasourceId
                ? "先选择数据源，再输入你的问题…"
                : activeConversationId == null
                  ? "选择或新建会话后再提问…"
                  : "例如：各区域成交额是多少，并给出每日趋势"
            }
            rows={1}
            disabled={!canAsk}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
          />
          <button className="send-btn" onClick={submit} disabled={!canAsk || !question.trim()}>
            {loading ? "生成中" : "发送"}
          </button>
        </div>
        </div>
      </main>

      {showAdd && (
        <Modal title="添加数据源" onClose={() => setShowAdd(false)}>
          <div className="form-grid">
            <label>
              名称
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
            <label>
              类型
              <select
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}
              >
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL</option>
                <option value="clickhouse">ClickHouse</option>
              </select>
            </label>
            <label>
              主机
              <input
                value={form.host}
                onChange={(e) => setForm({ ...form, host: e.target.value })}
              />
            </label>
            <label>
              端口
              <input
                value={form.port}
                onChange={(e) => setForm({ ...form, port: e.target.value })}
              />
            </label>
            <label>
              数据库
              <input
                value={form.database}
                onChange={(e) => setForm({ ...form, database: e.target.value })}
              />
            </label>
            <label>
              用户名
              <input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />
            </label>
            <label>
              密码
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </label>
          </div>
          <div className="modal-foot">
            <button className="primary" onClick={addDatasource} disabled={busy}>
              保存
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

