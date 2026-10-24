import type { ChartItem } from "../stores/chat";

export const CHART_TYPE_OPTIONS = [
  { value: "bar", label: "柱状图" },
  { value: "line", label: "折线图" },
  { value: "area", label: "面积图" },
  { value: "pie", label: "饼图" },
  { value: "scatter", label: "散点图" },
];

export function convertOption(
  chart: ChartItem,
  targetType: string,
): Record<string, unknown> {
  const dataset = (chart.echarts_option as Record<string, unknown>).dataset as
    | { source?: Record<string, unknown>[] }
    | undefined;
  const rows = dataset?.source;
  if (Array.isArray(rows) && rows.length > 0) {
    return buildFromRows(rows, targetType, chart.title);
  }

  const option = JSON.parse(
    JSON.stringify(chart.echarts_option ?? {}),
  ) as Record<string, any>;
  const series = Array.isArray(option.series) ? option.series : [];
  for (const item of series) {
    if (targetType === "pie") {
      item.type = "pie";
      if (!Array.isArray(item.data) || typeof item.data[0] !== "object") {
        const categories = Array.isArray(option.xAxis?.data)
          ? option.xAxis.data
          : [];
        item.data = categories.map((name: string, i: number) => ({
          name,
          value: Number(item.data?.[i] ?? 0),
        }));
      }
    } else {
      item.type = targetType === "area" ? "line" : targetType;
      if (targetType === "area") item.areaStyle = {};
      else delete item.areaStyle;
    }
  }
  return option;
}

function buildFromRows(
  rows: Record<string, unknown>[],
  targetType: string,
  title?: string,
): Record<string, unknown> {
  const columns = Object.keys(rows[0]);
  const numeric = columns.filter((c) => typeof rows[0][c] === "number");
  const dim = columns.find((c) => typeof rows[0][c] !== "number") ?? columns[0];
  const metrics = numeric.length ? numeric : columns.filter((c) => c !== dim);

  const base: Record<string, unknown> = {
    title: { text: title ?? "", left: "center" },
    legend: {},
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
  };

  if (targetType === "pie") {
    const metric = metrics[0] ?? columns[0];
    return {
      ...base,
      tooltip: { trigger: "item" },
      legend: { orient: "vertical", left: "left" },
      series: [
        {
          type: "pie",
          radius: "60%",
          data: rows.map((r) => ({
            name: String(r[dim]),
            value: Number(r[metric]),
          })),
        },
      ],
    };
  }

  const seriesType = targetType === "area" ? "line" : targetType;
  return {
    ...base,
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: rows.map((r) => String(r[dim])) },
    yAxis: { type: "value" },
    series: metrics.map((m) => {
      const item: Record<string, unknown> = {
        name: m,
        type: seriesType,
        data: rows.map((r) => Number(r[m])),
      };
      if (targetType === "area") item.areaStyle = {};
      if (targetType === "scatter") item.symbolSize = 10;
      return item;
    }),
  };
}

