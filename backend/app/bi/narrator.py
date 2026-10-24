from typing import Any

SYSTEM_NARRATOR = (
    "你是资深数据分析师。请根据给定的确定性数据洞察，写一段整体业务解读。\n"
    "要求：1) 必须引用给定内容中的具体数字，禁止编造；"
    "2) 提炼 3~5 条要点；3) 语言简洁、面向业务人员；"
    "4) summary 是一整段连贯的话。"
)


def build_narrative_messages(
    question: str,
    chart_insights: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lines = [f"用户问题：{question}", ""]
    for item in chart_insights:
        lines.append(f"图表《{item['title']}》（{item['chart_type']}）：")
        for insight in item.get("insights", []):
            lines.append(
                f"- [{insight['kind']}] {insight['title']}：{insight['body']}"
            )
        lines.append("")
    return [
        {"role": "system", "content": SYSTEM_NARRATOR},
        {"role": "user", "content": "\n".join(lines)},
    ]

