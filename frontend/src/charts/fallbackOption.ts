import type { ChartItem } from "../stores/chat";

export function resolveOption(chart: ChartItem): Record<string, unknown> {
  const option = chart.echarts_option ?? {};
  if (
    option.series != null ||
    option.xAxis != null ||
    option.yAxis != null ||
    Object.keys(option).length > 0
  ) {
    return option;
  }

  const columns = chart.data?.columns ?? [];
  const rows = chart.data?.rows ?? [];
  if (!columns.length || !rows.length) return {};

  const numeric = columns.find((c) => typeof rows[0]?.[c] === "number");
  const dim = columns.find((c) => c !== numeric);
  if (numeric == null || dim == null) return {};

  const categories = rows.map((r) => String(r[dim]));
  const values = rows.map((r) => Number(r[numeric]));
  return {
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: categories },
    yAxis: { type: "value" },
    series: [
      {
        type: chart.chart_type === "line" ? "line" : "bar",
        data: values,
        name: numeric,
      },
    ],
  };
}

