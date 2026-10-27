import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  App as AntdApp,
  Button,
  Card,
  Dropdown,
  Empty,
  Input,
  InputNumber,
  Modal,
  Select,
  Spin,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  BarChartOutlined,
  BulbOutlined,
  CodeOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  EditOutlined,
  EllipsisOutlined,
  MenuFoldOutlined,
  PlusOutlined,
  RobotOutlined,
  SendOutlined,
  SyncOutlined,
} from "@ant-design/icons";

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
    <Card className="chart-card" bordered={false}>
      <div className="chart-card-head">
        <div className="chart-card-title">
          <span className="chart-kind-dot" data-kind={chart.chart_type} />
          <strong>{chart.title}</strong>
        </div>
        <div className="chart-card-actions">
          <Select
            size="small"
            value={chartType}
            onChange={handleType}
            aria-label="图表类型"
            options={typeOptions.map((option) => ({
              value: option.value,
              label: option.label,
            }))}
          />
          <Button
            size="small"
            type={showSql ? "primary" : "default"}
            ghost={showSql}
            icon={<CodeOutlined />}
            onClick={() => setShowSql((value) => !value)}
          >
            SQL
          </Button>
          <Button size="small" onClick={() => exportPNG([chart])}>
            导出 PNG
          </Button>
        </div>
      </div>
      {showSql && <pre className="sql-box">{chart.sql || "(无 SQL)"}</pre>}
      <EChart chartId={chart.chart_id} option={option} />
    </Card>
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
  const { message, modal } = AntdApp.useApp();
  const [datasources, setDatasources] = useState<Datasource[]>([]);
  const [dashboards, setDashboards] = useState<DashboardSummary[]>([]);
  const [question, setQuestion] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<{
    id: number;
    title: string;
  } | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [busy, setBusy] = useState(false);

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
    renameConversation,
    deleteConversation,
    selectConversation,
    send,
    loadBoard,
  } = useChatStore();

  const refreshDatasources = async () => {
    try {
      setDatasources(await listDatasources());
    } catch (err) {
      message.error(err instanceof Error ? err.message : String(err));
    }
  };

  const refreshDashboards = async () => {
    try {
      setDashboards(await listDashboards());
    } catch (err) {
      message.error(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    refreshDatasources();
    refreshDashboards();
    loadConversations();
  }, []);

  const canAsk = Boolean(datasourceId) && !loading;

  const submit = async () => {
    if (!question.trim() || loading) return;
    if (datasourceId == null) {
      message.warning("请先在左侧选择或添加数据源");
      return;
    }
    await send(question.trim());
    setQuestion("");
  };

  const handleSuggestion = async (q: string) => {
    if (datasourceId == null) {
      message.warning("请先在左侧选择或添加数据源");
      return;
    }
    await send(q);
  };

  const startNewConversation = async () => {
    if (datasourceId == null) {
      message.warning("请先选择数据源后再新建会话");
      return;
    }
    await createConversation();
    setSidebarOpen(false);
  };

  const renameSelectedConversation = (id: number, title: string) => {
    setRenameTarget({ id, title });
    setRenameTitle(title);
  };

  const removeConversation = async (id: number, title: string) => {
    modal.confirm({
      title: "删除会话",
      content: `确定删除「${title}」及其消息和图表吗？此操作无法撤销。`,
      okText: "删除",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: () => deleteConversation(id),
    });
  };

  const addDatasource = async () => {
    if (
      !form.name.trim() ||
      !form.host.trim() ||
      !form.database.trim() ||
      !form.username.trim() ||
      !form.password ||
      !Number(form.port)
    ) {
      message.warning("请完整填写数据源连接信息");
      return;
    }
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
      message.success("数据源已添加，请同步知识库建立索引");
      setShowAdd(false);
      setForm(EMPTY_FORM);
      await refreshDatasources();
    } catch (err) {
      message.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const syncSelected = async () => {
    if (datasourceId == null) return;
    setBusy(true);
    try {
      await syncDatasource(datasourceId);
      message.success("知识库同步完成");
    } catch (err) {
      message.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const removeSelected = async () => {
    if (datasourceId == null) return;
    modal.confirm({
      title: "删除数据源",
      content: `确定删除数据源「${activeDatasource?.name}」吗？此操作无法撤销。`,
      okText: "删除",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteDatasource(datasourceId);
          setDatasource(null);
          await refreshDatasources();
          message.success("数据源已删除");
        } catch (err) {
          message.error(err instanceof Error ? err.message : String(err));
          throw err;
        }
      },
    });
  };

  const loadDashboard = async (id: number) => {
    try {
      const board = await getDashboard(id);
      const layout = board.layout ?? {};
      loadBoard(
        (layout.charts as ChartItem[]) ?? [],
        (layout.insights as InsightItem[]) ?? [],
      );
      message.success(`已载入看板「${board.title}」`);
    } catch (err) {
      message.error(err instanceof Error ? err.message : String(err));
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
      message.error(err instanceof Error ? err.message : String(err));
    }
  };

  const confirmRename = async () => {
    if (!renameTarget) return;
    const title = renameTitle.trim();
    if (!title) {
      message.warning("会话名称不能为空");
      return;
    }
    if (title !== renameTarget.title) {
      await renameConversation(renameTarget.id, title);
    }
    setRenameTarget(null);
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

        <Button
          type="primary"
          size="large"
          block
          icon={<PlusOutlined />}
          onClick={startNewConversation}
        >
          新建分析
        </Button>

        <div className="side-section">
          <label className="side-label">
            <DatabaseOutlined /> 数据源
          </label>
          <Select
            value={datasourceId ?? undefined}
            placeholder="选择数据源"
            size="large"
            options={datasources.map((datasource) => ({
              value: datasource.id,
              label: `${datasource.name} · ${datasource.type}`,
            }))}
            onChange={(value) => {
              setDatasource(value ?? null);
              setSidebarOpen(false);
            }}
          />
          <div className="side-actions">
            <Button
              block
              icon={<SyncOutlined spin={busy} />}
              onClick={syncSelected}
              disabled={busy || datasourceId == null}
            >
              同步知识库
            </Button>
            <Button
              block
              icon={<PlusOutlined />}
              onClick={() => setShowAdd(true)}
            >
              添加数据源
            </Button>
            <Button
              block
              danger
              icon={<DeleteOutlined />}
              onClick={removeSelected}
              disabled={datasourceId == null}
            >
              删除当前数据源
            </Button>
          </div>
        </div>

        <div className="side-section">
          <label className="side-label">
            <RobotOutlined /> 分析会话
          </label>
          <div className="conv-list">
            {conversations.map((c) => (
              <div className="conversation-row" key={c.id}>
                <Button
                  type="text"
                  className={
                    c.id === activeConversationId
                      ? "conv-item active"
                      : "conv-item"
                  }
                  onClick={() => selectConversation(c.id)}
                  title={c.title}
                >
                  <span className="conv-name">{c.title}</span>
                </Button>
                <Dropdown
                  trigger={["click"]}
                  menu={{
                    items: [
                      {
                        key: "rename",
                        icon: <EditOutlined />,
                        label: "重命名",
                      },
                      {
                        key: "delete",
                        icon: <DeleteOutlined />,
                        label: "删除会话",
                        danger: true,
                        disabled: loading && c.id === activeConversationId,
                      },
                    ],
                    onClick: ({ key }) => {
                      if (key === "rename") {
                        renameSelectedConversation(c.id, c.title);
                      } else if (key === "delete") {
                        removeConversation(c.id, c.title);
                      }
                    },
                  }}
                >
                  <Button
                    className="conversation-menu"
                    type="text"
                    icon={<EllipsisOutlined />}
                    aria-label={`会话操作：${c.title}`}
                  />
                </Dropdown>
              </div>
            ))}
            {conversations.length === 0 && (
              <Empty
                className="sidebar-empty"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="暂无会话"
              />
            )}
          </div>
        </div>

        {dashboards.length > 0 && (
          <div className="side-section">
            <label className="side-label">
              <BarChartOutlined /> 已保存看板
            </label>
            <div className="conv-list">
              {dashboards.map((d) => (
                <Button
                  key={d.id}
                  type="text"
                  className="conv-item"
                  onClick={() => loadDashboard(d.id)}
                >
                  <span className="conv-name">{d.title}</span>
                </Button>
              ))}
            </div>
          </div>
        )}
      </aside>

      {sidebarOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="关闭导航菜单"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <main className="main">
        <header className="topbar">
          <Button
            className="icon-btn hamburger"
            type="text"
            icon={<MenuFoldOutlined />}
            onClick={() => setSidebarOpen((v) => !v)}
          />
          <div className="topbar-title">
            {activeConversation ? activeConversation.title : "开始新的分析"}
          </div>
          <div className="topbar-right">
            {activeDatasource && (
              <Tag icon={<DatabaseOutlined />} color="blue">
                {activeDatasource.name}
              </Tag>
            )}
            <Tag icon={<RobotOutlined />} color="green">
              DeepSeek
            </Tag>
          </div>
        </header>

        <div className="sheet">
        <div className="content">
          {error && (
            <Alert
              className="page-alert"
              type="error"
              showIcon
              closable
              message="操作未完成"
              description={error}
            />
          )}

          {(activeDatasource || activeConversationId != null || charts.length > 0) && (
            <div className="workspace-summary">
              <Card className="summary-card" size="small">
                <span className="summary-label">当前数据源</span>
                <strong>{activeDatasource ? activeDatasource.name : "未选择"}</strong>
              </Card>
              <Card className="summary-card" size="small">
                <span className="summary-label">会话状态</span>
                <strong>{activeConversation ? activeConversation.title : "待开始"}</strong>
              </Card>
              <Card className="summary-card accent" size="small">
                <span className="summary-label">分析进度</span>
                <strong>
                  {loading
                    ? stage || "正在分析…"
                    : charts.length > 0
                      ? "已生成结果"
                      : "等待提问"}
                </strong>
              </Card>
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
                    <Button
                      key={s}
                      shape="round"
                      onClick={() => handleSuggestion(s)}
                    >
                      {s}
                    </Button>
                  ))}
                </div>
                <div className="welcome-meta">
                  已配置 {datasources.length} 个数据源 · 支持自然语言分析
                </div>
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

              {messages.length === 0 &&
                charts.length === 0 &&
                !loading && (
                  <Empty
                    className="conversation-empty"
                    description="提出一个数据问题，开始本次分析"
                  />
                )}

              {loading && (
                <Alert
                  className="stage"
                  type="info"
                  showIcon
                  icon={<Spin size="small" />}
                  message={stage || "正在分析…"}
                />
              )}

              {charts.length > 0 && (
                <div className="charts-block">
                  <div className="block-head">
                    <Typography.Title level={4}>
                      <BarChartOutlined /> 分析图表
                    </Typography.Title>
                    <div className="block-actions">
                      <Button onClick={() => exportPNG(charts)}>
                        导出 PNG
                      </Button>
                      <Button type="primary" onClick={() => exportPDF(charts)}>
                        导出 PDF
                      </Button>
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
                    <Typography.Title level={4}>
                      <BulbOutlined /> 整体解读
                    </Typography.Title>
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
                  <Typography.Title level={4}>
                    <BulbOutlined /> BI 洞察
                  </Typography.Title>
                  <div className="insight-grid">
                    {insights.map((ins, i) => (
                      <Card key={i} className="insight-card" size="small">
                        <div className="insight-head">
                          <Tag color="blue">{ins.kind}</Tag>
                          <strong>{ins.title}</strong>
                        </div>
                        <p>{ins.body}</p>
                      </Card>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>

        <div className="composer">
          <Input.TextArea
            value={question}
            placeholder={
              !datasourceId
                ? "先选择数据源，再输入你的问题…"
                : activeConversationId == null
                  ? "选择或新建会话后再提问…"
                  : "例如：各区域成交额是多少，并给出每日趋势"
            }
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={!canAsk}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
          />
          <Tooltip title={loading ? stage || "正在生成" : "发送问题（Enter）"}>
            <Button
              type="primary"
              className="send-btn"
              icon={<SendOutlined />}
              onClick={submit}
              disabled={!canAsk || !question.trim()}
              loading={loading}
            >
              发送
            </Button>
          </Tooltip>
        </div>
        </div>
      </main>

      <Modal
        title="添加数据源"
        open={showAdd}
        onCancel={() => setShowAdd(false)}
        onOk={addDatasource}
        okText="保存数据源"
        cancelText="取消"
        confirmLoading={busy}
        destroyOnHidden
      >
        <div className="form-grid">
          <label>
            名称
            <Input
              placeholder="例如：生产数据仓库"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label>
            类型
            <Select
              value={form.type}
              onChange={(value) => setForm({ ...form, type: value })}
              options={[
                { value: "postgresql", label: "PostgreSQL" },
                { value: "mysql", label: "MySQL" },
                { value: "clickhouse", label: "ClickHouse" },
              ]}
            />
          </label>
          <label>
            主机
            <Input
              placeholder="数据库主机地址"
              value={form.host}
              onChange={(e) => setForm({ ...form, host: e.target.value })}
            />
          </label>
          <label>
            端口
            <InputNumber
              min={1}
              max={65535}
              style={{ width: "100%" }}
              value={Number(form.port) || null}
              onChange={(value) =>
                setForm({ ...form, port: value == null ? "" : String(value) })
              }
            />
          </label>
          <label>
            数据库
            <Input
              placeholder="数据库名称"
              value={form.database}
              onChange={(e) => setForm({ ...form, database: e.target.value })}
            />
          </label>
          <label>
            用户名
            <Input
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
            />
          </label>
          <label className="form-wide">
            密码
            <Input.Password
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </label>
        </div>
      </Modal>

      <Modal
        title="重命名会话"
        open={renameTarget !== null}
        onCancel={() => setRenameTarget(null)}
        onOk={confirmRename}
        okText="保存"
        cancelText="取消"
        okButtonProps={{ disabled: !renameTitle.trim() }}
      >
        <Input
          autoFocus
          maxLength={255}
          showCount
          value={renameTitle}
          placeholder="请输入会话名称"
          onChange={(e) => setRenameTitle(e.target.value)}
          onPressEnter={confirmRename}
        />
      </Modal>
    </div>
  );
}
