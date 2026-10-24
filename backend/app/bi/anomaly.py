from __future__ import annotations

import re
import statistics
from typing import Any


def detect_anomalies(result: dict[str, Any]) -> list[dict[str, Any]]:
    """对查询结果做异常检测（Z-score / 环比突变 / 集中度）。"""
    columns: list[str] = result.get("columns", [])
    rows: list[dict[str, Any]] = result.get("rows", [])
    if not columns or not rows:
        return []

    numeric = [c for c in columns if all(_is_number(r.get(c)) for r in rows)]
    date_cols = [c for c in columns if all(_is_date(r.get(c)) for r in rows)]
    dim_cols = [c for c in columns if c not in numeric and c not in date_cols]

    anomalies: list[dict[str, Any]] = []

    if date_cols and numeric:
        date = date_cols[0]
        ordered = sorted(rows, key=lambda r: str(r[date]))
        for metric in numeric[:2]:
            values = [float(r[metric]) for r in ordered]
            if len(values) >= 4:
                mean = statistics.mean(values)
                std = statistics.stdev(values)
                if std > 0:
                    for r, value in zip(ordered, values):
                        z = (value - mean) / std
                        if abs(z) >= 1.2:
                            anomalies.append(
                                _make(
                                    "anomaly",
                                    f"{metric} 异常点",
                                    (
                                        f"{r[date]} 的 {metric} 为 {value:,.2f}，"
                                        f"偏离均值 {z:+.1f} 个标准差。"
                                    ),
                                    metric,
                                    {
                                        "method": "zscore",
                                        "threshold": 1.2,
                                        "date": r[date],
                                        "value": round(value, 4),
                                        "z": round(z, 4),
                                    },
                                    [r],
                                )
                            )

            for i in range(1, len(ordered)):
                prev = float(ordered[i - 1][metric])
                current = float(ordered[i][metric])
                if prev == 0:
                    continue
                pct = (current - prev) / prev * 100
                if abs(pct) >= 100:
                    anomalies.append(
                        _make(
                            "anomaly",
                            f"{metric} 环比突变",
                            f"{ordered[i][date]} 的 {metric} 较上一期 {pct:+.1f}%。",
                            metric,
                            {
                                "method": "pct_change",
                                "threshold": 100,
                                "date": ordered[i][date],
                                "pct": round(pct, 4),
                            },
                            [ordered[i - 1], ordered[i]],
                        )
                    )

    elif dim_cols and numeric:
        label = dim_cols[0]
        for metric in numeric[:2]:
            values = [float(r[metric]) for r in rows]
            total = sum(values)
            if total:
                for r, value in zip(rows, values):
                    share = value / total
                    if share >= 0.7:
                        anomalies.append(
                            _make(
                                "anomaly",
                                "集中度异常",
                                (
                                    f"{r[label]} 贡献了 {metric} 的 {share:.1%}，"
                                    "集中度过高。"
                                ),
                                metric,
                                {
                                    "method": "share",
                                    "threshold": 0.7,
                                    "name": str(r[label]),
                                    "share": round(share, 4),
                                },
                                [r],
                            )
                        )

    return anomalies


def attribute_change(result: dict[str, Any]) -> list[dict[str, Any]]:
    """把指标的整体变化归因到维度成员的贡献。"""
    columns: list[str] = result.get("columns", [])
    rows: list[dict[str, Any]] = result.get("rows", [])
    if not columns or not rows:
        return []

    numeric = [c for c in columns if all(_is_number(r.get(c)) for r in rows)]
    date_cols = [c for c in columns if all(_is_date(r.get(c)) for r in rows)]
    dim_cols = [c for c in columns if c not in numeric and c not in date_cols]
    if not (date_cols and dim_cols and numeric):
        return []

    date = date_cols[0]
    dim = dim_cols[0]
    metric = numeric[0]

    unique_dates = sorted({str(r[date]) for r in rows})
    if len(unique_dates) < 2:
        return []
    half = max(1, len(unique_dates) // 2)
    baseline_dates = set(unique_dates[:half])
    current_dates = set(unique_dates[half:])

    baseline_total = sum(
        float(r[metric]) for r in rows if str(r[date]) in baseline_dates
    )
    current_total = sum(
        float(r[metric]) for r in rows if str(r[date]) in current_dates
    )
    delta = current_total - baseline_total
    if delta == 0:
        return []

    members = sorted({str(r[dim]) for r in rows})
    contributions: list[tuple[str, float, float, float]] = []
    for member in members:
        before = sum(
            float(r[metric])
            for r in rows
            if str(r[dim]) == member and str(r[date]) in baseline_dates
        )
        after = sum(
            float(r[metric])
            for r in rows
            if str(r[dim]) == member and str(r[date]) in current_dates
        )
        contributions.append((member, after - before, before, after))
    contributions.sort(key=lambda item: -abs(item[1]))

    body = (
        f"{metric} 由 {baseline_total:,.2f} 变为 {current_total:,.2f}"
        f"（{delta:+,.2f}）。"
    )
    detail = []
    for member, member_delta, before, after in contributions[:3]:
        share = member_delta / delta
        body += (
            f" 其中 {member} 贡献 {member_delta:+,.2f}"
            f"（占变化的 {abs(share):.1%}）。"
        )
        detail.append(
            {
                "name": member,
                "before": round(before, 4),
                "after": round(after, 4),
                "delta": round(member_delta, 4),
                "share": round(share, 4),
            }
        )

    return [
        _make(
            "attribution",
            f"{metric} 变化归因",
            body,
            metric,
            {
                "dim": dim,
                "baseline_total": round(baseline_total, 4),
                "current_total": round(current_total, 4),
                "delta": round(delta, 4),
                "contributors": detail,
            },
            rows,
        )
    ]


def _make(
    kind: str,
    title: str,
    body: str,
    metric_ref: str,
    metrics: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "kind": kind,
        "title": title,
        "body": body,
        "metric_ref": metric_ref,
        "metrics": metrics,
        "evidence": evidence,
    }


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_date(value: Any) -> bool:
    return isinstance(value, str) and bool(
        re.match(r"^\d{4}-\d{2}(-\d{2})?([ T]\d{2}:\d{2})?", value)
    )

