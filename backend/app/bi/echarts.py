from __future__ import annotations

import re
from typing import Any


def apply_data_to_option(
    option: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """把执行结果回填到模型生成的 ECharts option（替换 {{column}} 占位符）。"""
    columns: list[str] = result.get("columns", [])
    rows: list[dict[str, Any]] = result.get("rows", [])
    if not columns or not rows:
        return option

    numeric = [
        c
        for c in columns
        if all(_is_number(r.get(c)) for r in rows)
    ]
    dim = next((c for c in columns if c not in numeric), columns[0])
    metrics = numeric or [c for c in columns if c != dim]

    out = dict(option)

    # dataset.source 始终用真实数据
    out["dataset"] = {
        "source": [{c: r.get(c) for c in columns} for r in rows]
    }

    xaxis = out.get("xAxis")
    if isinstance(xaxis, dict) and dim:
        xaxis["type"] = "category"
        xaxis["data"] = [str(r.get(dim)) for r in rows]

    series = out.get("series")
    if not isinstance(series, list) or not series:
        metric = metrics[0] if metrics else None
        if metric and dim:
            out["series"] = [
                {
                    "type": "bar",
                    "name": metric,
                    "data": [float(r.get(metric)) for r in rows],
                }
            ]
        return out

    for item in series:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "pie":
            metric = metrics[0] if metrics else None
            if metric and dim:
                item["data"] = [
                    {"name": str(r.get(dim)), "value": float(r.get(metric))}
                    for r in rows
                ]
            continue

        metric = _extract_metric(item.get("data"), metrics)
        if metric:
            item["data"] = [float(r.get(metric)) for r in rows]

    return out


def _extract_metric(data: Any, metrics: list[str]) -> str | None:
    if isinstance(data, list):
        for value in data:
            if isinstance(value, str):
                match = re.fullmatch(r"\{\{\s*(\w+)\s*\}\}", value)
                if match and match.group(1) in metrics:
                    return match.group(1)
    return metrics[0] if metrics else None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)

