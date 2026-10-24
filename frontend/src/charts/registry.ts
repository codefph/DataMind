import type * as echarts from "echarts";

const registry = new Map<string, echarts.ECharts>();

export const chartRegistry = {
  set: (id: string, chart: echarts.ECharts) => registry.set(id, chart),
  get: (id: string) => registry.get(id),
  delete: (id: string) => registry.delete(id),
};

