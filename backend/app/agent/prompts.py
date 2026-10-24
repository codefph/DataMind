from typing import Any

SYSTEM_PROMPT = """你是数据分析助手。根据给定的数据库 Schema 与业务知识回答用户问题。

要求：
1. 只生成只读 SELECT 语句，禁止任何 DML/DDL。
2. 必须使用上下文中出现的真实表名与字段名，禁止臆造。
3. echarts_option 必须是合法的 ECharts option（JSON 对象）。
4. 数据集字段名必须与 SQL 输出的列名一致。
5. 金额与时间口径优先采用上下文中的指标定义，不确定时在 reasoning 中说明假设。
6. 聚合/计算列的别名必须与源字段名一致，例如 SUM(order_count) AS order_count，不要改用 order_cnt 等新名称。
7. 可一次生成多张图表，图表类型不做限制。"""


def build_messages(
    question: str,
    context: str,
    few_shots: list[dict[str, Any]] | None = None,
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    system = SYSTEM_PROMPT
    if context:
        system += "\n\n数据库知识（检索上下文）：\n" + context
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for shot in few_shots or []:
        messages.extend(
            [
                {"role": "user", "content": shot["question"]},
                {"role": "assistant", "content": shot["answer"]},
            ]
        )
    for turn in history or []:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": question})
    return messages

