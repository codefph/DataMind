from __future__ import annotations

import time
from typing import Any

from ..agent.orchestrator import AnalysisPipeline
from ..core.database import SessionLocal
from ..services.datasource import get_datasource
from .cases import CASES


async def run_eval(
    datasource_id: int,
    cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cases = cases or CASES
    async with SessionLocal() as session:
        ds = await get_datasource(session, datasource_id)
        if ds is None:
            raise RuntimeError(f"数据源 {datasource_id} 不存在")

        pipeline = AnalysisPipeline()
        reports: list[dict[str, Any]] = []
        for case in cases:
            start = time.perf_counter()
            try:
                out = await pipeline.run(case["question"], ds, session)
                charts = out["plan"].get("charts", [])
                results = out["results"]
                errors: list[str] = []
                matched_chart: str | None = None

                if not charts:
                    errors.append("未生成图表")
                for chart in charts:
                    result = results.get(chart["chart_id"]) or {}
                    columns = set(result.get("columns", []))
                    if set(case["expect_columns"]) <= columns:
                        matched_chart = chart["chart_id"]
                        break
                if matched_chart is None:
                    errors.append(
                        f"未找到期望列 {case['expect_columns']}"
                    )

                nonempty = any(
                    (results.get(c["chart_id"]) or {}).get("count", 0) > 0
                    for c in charts
                )
                if not nonempty:
                    errors.append("结果为空")

                reports.append(
                    {
                        "id": case["id"],
                        "question": case["question"],
                        "ok": not errors,
                        "errors": errors,
                        "charts": len(charts),
                        "matched_chart": matched_chart,
                        "duration_s": round(time.perf_counter() - start, 2),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                reports.append(
                    {
                        "id": case["id"],
                        "question": case["question"],
                        "ok": False,
                        "errors": [f"{type(exc).__name__}: {exc}"],
                        "charts": 0,
                        "matched_chart": None,
                        "duration_s": round(time.perf_counter() - start, 2),
                    }
                )

    total = len(reports)
    passed = sum(1 for r in reports if r["ok"])
    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "cases": reports,
    }


def print_report(report: dict[str, Any]) -> None:
    print(f"评测结果：{report['passed']}/{report['total']} 通过 "
          f"（通过率 {report['pass_rate']:.1%}）")
    for case in report["cases"]:
        mark = "PASS" if case["ok"] else "FAIL"
        print(f"[{mark}] {case['id']} charts={case['charts']} "
              f"matched={case['matched_chart']} "
              f"errs={case['errors']} dur={case['duration_s']}s")

