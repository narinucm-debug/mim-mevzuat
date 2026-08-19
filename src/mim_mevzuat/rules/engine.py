"""Rule Engine - Rule Pack kayıtlarını yöneten ve çalıştıran ana motor."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional

from .base import CalculationTrace, RuleExecutionResult, RulePack
from .emsal import RULE_EMSAL_TAKS
from .otopark import RULE_OTOPARK_KONUT


class RuleEngine:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn
        self._rules: dict[str, RulePack] = {}
        self.register_default_rules()

    def register(self, rule: RulePack) -> None:
        self._rules[rule.rule_id] = rule
        if self.conn:
            self._sync_rule_pack_to_db(rule)

    def _sync_rule_pack_to_db(self, rule: RulePack) -> None:
        try:
            inputs_json = json.dumps(
                [
                    {
                        "name": inp.name,
                        "type": inp.type,
                        "required": inp.required,
                        "description": inp.description,
                    }
                    for inp in rule.inputs
                ],
                ensure_ascii=False,
            )
            self.conn.execute(
                """
                INSERT INTO rule_pack (
                    rule_id, jurisdiction, version, source_document, source_article,
                    inputs_json, formula_ref, conditions, exceptions, effective_from, effective_to
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(rule_id) DO UPDATE SET
                    jurisdiction=excluded.jurisdiction,
                    version=excluded.version,
                    source_document=excluded.source_document,
                    source_article=excluded.source_article,
                    inputs_json=excluded.inputs_json,
                    formula_ref=excluded.formula_ref
                """,
                (
                    rule.rule_id,
                    rule.jurisdiction,
                    rule.version,
                    rule.source_document,
                    rule.source_article,
                    inputs_json,
                    rule.rule_id,
                    json.dumps(rule.conditions, ensure_ascii=False),
                    json.dumps(rule.exceptions, ensure_ascii=False),
                    rule.effective_from,
                    rule.effective_to,
                ),
            )
            self.conn.commit()
        except Exception:
            pass

    def register_default_rules(self) -> None:
        self.register(RULE_OTOPARK_KONUT)
        self.register(RULE_EMSAL_TAKS)

    def get_rule(self, rule_id: str) -> Optional[RulePack]:
        return self._rules.get(rule_id)

    def list_rules(self) -> list[dict[str, Any]]:
        return [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "jurisdiction": r.jurisdiction,
                "version": r.version,
                "source_document": r.source_document,
                "source_article": r.source_article,
                "inputs": [
                    {
                        "name": inp.name,
                        "type": inp.type,
                        "required": inp.required,
                        "description": inp.description,
                        "default": inp.default,
                    }
                    for inp in r.inputs
                ],
            }
            for r in self._rules.values()
        ]

    def execute(self, rule_id: str, inputs: dict[str, Any]) -> RuleExecutionResult:
        rule = self.get_rule(rule_id)
        if not rule:
            return RuleExecutionResult(
                success=False,
                error_message=f"'{rule_id}' kimlikli kural paketi bulunamadı.",
            )

        res = rule.execute(inputs)
        if res.success and res.trace and self.conn:
            self._save_trace(res.trace)

        return res

    def _save_trace(self, trace: CalculationTrace) -> None:
        """Trace kaydını calculation_trace tablosuna yazar."""
        try:
            self.conn.execute(
                """
                INSERT INTO calculation_trace (
                    trace_id, rule_id, inputs_json, method, result_json,
                    source_document, source_article, confidence, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace.trace_id,
                    trace.rule_id,
                    json.dumps(trace.inputs, ensure_ascii=False),
                    trace.method,
                    json.dumps(trace.result, ensure_ascii=False),
                    trace.source_document,
                    trace.source_article,
                    trace.confidence.value,
                    trace.generated_at,
                ),
            )
            self.conn.commit()
        except Exception:
            pass
