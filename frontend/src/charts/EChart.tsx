import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import { chartRegistry } from "./registry";
import { useResize } from "../hooks/useResize";

export default function EChart({
  chartId,
  option,
  height = 320,
}: {
  chartId: string;
  option: Record<string, unknown>;
  height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  useResize(ref, (rect) => {
    chartRef.current?.resize();
  });
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, {
      color: ["#1b6c80", "#2f70bb", "#a86f0c", "#8a9099"],
      textStyle: {
        fontFamily: "IBM Plex Sans, Inter, system-ui, sans-serif",
        color: "#131416",
      },
    });
    chartRef.current = chart;
    chartRegistry.set(chartId, chart);
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      chartRegistry.delete(chartId);
      chart.dispose();
    };
  }, [chartId]);

  useEffect(() => {
    chartRef.current?.setOption(option, true);
  }, [option]);

  return <div ref={ref} style={{ width: "100%", height: '100%', flex: 1}}/>;
}

