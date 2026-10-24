import { jsPDF } from "jspdf";

import { chartRegistry } from "../charts/registry";
import type { ChartItem } from "../stores/chat";

function download(url: string, filename: string) {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
}

function safeName(text: string) {
  return text.replace(/[\\/:*?"<>|]/g, "_").slice(0, 60) || "chart";
}

export function exportPNG(charts: ChartItem[]) {
  for (const chart of charts) {
    const instance = chartRegistry.get(chart.chart_id);
    if (!instance) continue;
    const url = instance.getDataURL({
      type: "png",
      pixelRatio: 2,
      backgroundColor: "#ffffff",
    });
    download(url, `${safeName(chart.title)}.png`);
  }
}

export function exportPDF(charts: ChartItem[], title = "DataMind 看板") {
  const doc = new jsPDF({ unit: "px", format: "a4" });
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 32;
  const maxWidth = pageWidth - margin * 2;

  for (let i = 0; i < charts.length; i++) {
    const chart = charts[i];
    const instance = chartRegistry.get(chart.chart_id);
    if (!instance) continue;

    const url = instance.getDataURL({
      type: "png",
      pixelRatio: 2,
      backgroundColor: "#ffffff",
    });
    const width = instance.getWidth();
    const height = instance.getHeight();
    const scale = Math.min(1, maxWidth / width);

    if (i > 0) doc.addPage();
    doc.setFontSize(14);
    doc.text(chart.title, margin, margin - 8);
    doc.addImage(url, "PNG", margin, margin, width * scale, height * scale);
  }

  doc.save(`${safeName(title)}.pdf`);
}

