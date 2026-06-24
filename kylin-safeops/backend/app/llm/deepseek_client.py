import json

import httpx


class DeepSeekClient:
    def __init__(self, settings):
        self.settings = settings

    def critique(self, knowledge_state: dict, hypotheses: list[dict], tool_trace: list[dict]) -> dict:
        prompt = (
            "你是 KylinSafeOps 运维 Agent 的认知审查器和修复建议生成器。"
            "只能基于已给出的工具证据进行解释，不能编造事实，不能输出可直接复制执行的 Shell 命令。"
            "未经工具验证的信息必须保持 assumed。"
            "修复建议必须是安全计划级建议，涉及 restart/修改配置时必须要求 Shadow Execution 和人工确认。"
            "请返回 JSON，字段包括 conclusion、evidence_gaps、safe_remediation_plan、risk_review。"
        )
        payload = {
            "model": self.settings.deepseek_model,
            "messages": [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": json.dumps({
                        "knowledge_state": knowledge_state,
                        "hypotheses": hypotheses,
                        "tool_trace": [
                            {"tool": item.get("tool"), "ok": item.get("ok"), "summary": item.get("summary")}
                            for item in tool_trace
                        ],
                    }, ensure_ascii=False),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        try:
            response = httpx.post(
                f"{self.settings.deepseek_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.deepseek_api_key}"},
                json=payload,
                timeout=httpx.Timeout(4.0, connect=2.0),
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = _safe_parse_json(content)
            return {
                "provider": "deepseek",
                "enabled": True,
                "conclusion": parsed.get("conclusion", content),
                "evidence_gaps": parsed.get("evidence_gaps", []),
                "safe_remediation_plan": parsed.get("safe_remediation_plan", []),
                "risk_review": parsed.get("risk_review", "DeepSeek 已完成认知审查。"),
                "raw": parsed,
            }
        except Exception as exc:
            return {
                "provider": "deepseek",
                "enabled": False,
                "conclusion": "DeepSeek 增强审查暂不可用，已切换规则兜底，诊断主链路不受影响。",
                "error": str(exc),
                "evidence_gaps": [],
                "safe_remediation_plan": [
                    "继续使用规则兜底诊断链路。",
                    "任何服务重启或配置变更仍需先经过 Shadow Execution 和人工确认。",
                ],
                "risk_review": "外部模型不可用不影响核心安全链路。",
            }


def _safe_parse_json(content: str) -> dict:
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}
