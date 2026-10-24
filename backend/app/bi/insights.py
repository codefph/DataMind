from __future__ import annotations

import re
from typing import Any

from .anomaly import attribute_change, detect_anomalies


def compute_insights(result: dict[str, Any]) -> list[dict[str, Any]]:
    """基于查询结果做确定性洞察（不依赖 LLM）。"""
    columns: list[str] = result.get("columns", [])
    rows: list[dict[str, Any]] = result.get("rows", [])
    if not rows or not columns:
        return []

    numeric_cols = [
        c
        for c in columns
        if all(_is_number(r.get(c)) for r in rows)
    ]
    date_cols = [
        c
        for c in columns
        if all(_is_date(r.get(c)) for r in rows)
    ]
    dim_cols = [c for c in columns if c not in numeric_cols and c not in date_cols]

    insights: list[dict[str, Any]] = []

    if numeric_cols:
        for metric in numeric_cols:
            values = [float(r[metric]) for r in rows]
            insights.append(
                {
                    "kind": "summary",
                    "title": f"{metric} 汇总",
                    "body": (
                        f"{metric} 共 {len(values)} 个值，合计 {sum(values):,.2f}，"
                        f"平均 {sum(values) / len(values):,.2f}，"
                        f"最大 {max(values):,.2f}，最小 {min(values):,.2f}。"
                    ),
                    "metric_ref": metric,
                    "metrics": {
                        "count": len(values),
                        "sum": round(sum(values), 4),
                        "avg": round(sum(values) / len(values), 4),
                        "max": round(max(values), 4),
                        "min": round(min(values), 4),
                    },
                    "evidence": values,
                }
            )

    if dim_cols and numeric_cols:
        label = dim_cols[0]
        for metric in numeric_cols[:2]:
            ranked = sorted(
                rows, key=lambda r: float(r[metric]), reverse=True
            )[:3]
            top_text = "、".join(str(r[label]) for r in ranked)
            insights.append(
                {
                    "kind": "rank",
                    "title": f"{metric} TOP 3",
                    "body": f"按 {metric} 排名前三的 {label} 为：{top_text}。",
                    "metric_ref": metric,
                    "metrics": {
                        "label": label,
                        "top": [
                            {"name": str(r[label]), "value": float(r[metric])}
                            for r in ranked
                        ],
                    },
                    "evidence": [
                        {label: r[label], metric: r[metric]} for r in ranked
                    ],
                }
            )

        total = sum(float(r[metric]) for r in rows)
        if total:
            largest = max(rows, key=lambda r: float(r[metric]))
            share = float(largest[metric]) / total
            insights.append(
                {
                    "kind": "composition",
                    "title": "构成占比",
                    "body": (
                        f"{largest[label]} 贡献了 {metric} 的 {share:.1%}，"
                        f"在全部 {len(rows)} 个 {label} 中占比最高。"
                    ),
                    "metric_ref": metric,
                    "metrics": {
                        "label": label,
                        "top_name": str(largest[label]),
                        "share": round(share, 4),
                    },
                    "evidence": [
                        {"name": str(r[label]), "value": float(r[metric])}
                        for r in rows
                    ],
                }
            )

    if date_cols and numeric_cols:
        date_col = date_cols[0]
        metric = numeric_cols[0]
        ordered = sorted(rows, key=lambda r: str(r[date_col]))
        if len(ordered) >= 2:
            last = float(ordered[-1][metric])
            prev = float(ordered[-2][metric])
            change = last - prev
            pct = (change / prev * 100) if prev else 0.0
            direction = "上升" if change >= 0 else "下降"
            insights.append(
                {
                    "kind": "trend",
                    "title": f"{metric} 环比",
                    "body": (
                        f"最新一期（{ordered[-1][date_col]}）{metric} 为 {last:,.2f}，"
                        f"较上一期（{ordered[-2][date_col]}）{direction} {abs(change):,.2f}"
                        f"（{pct:+.1f}%）。"
                    ),
                    "metric_ref": metric,
                    "metrics": {
                        "date_col": date_col,
                        "last": round(last, 4),
                        "previous": round(prev, 4),
                        "change": round(change, 4),
                        "pct": round(pct, 4),
                    },
                    "evidence": [
                        {date_col: r[date_col], metric: r[metric]}
                        for r in ordered[-2:]
                    ],
                }
            )

    insights.extend(detect_anomalies(result))
    insights.extend(attribute_change(result))

    return insights


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_date(value: Any) -> bool:
    return isinstance(value, str) and bool(
        re.match(r"^\d{4}-\d{2}(-\d{2})?([ T]\d{2}:\d{2})?", value)
    )

