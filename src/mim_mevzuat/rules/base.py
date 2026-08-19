"""Rule Engine Base - RULE_ENGINE.txt ve DATA_MODEL.txt ilkelerine uygun
kural ve hesaplama modelleri.

İLKELER:
1. LLM formül ÜRETMEZ. Formüller onaylanmış Python fonksiyonlarıdır.
2. Tahmin YOK: Gerekli girdi eksikse hesaplama yapılmaz, missing_inputs listesi döner.
3. Her hesaplama zorunlu bir CalculationTrace üretir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional
import uuid

from ..models import ConfidenceLevel


@dataclass(frozen=True)
class RuleInput:
    name: str
    type: str  # "float", "int", "str", "bool"
    required: bool = True
    description: str = ""
    default: Optional[Any] = None


@dataclass
class CalculationTrace:
    trace_id: str
    rule_id: str
    rule_name: str
    inputs: dict[str, Any]
    method: str
    result: dict[str, Any]
    source_document: str
    source_article: str
    confidence: ConfidenceLevel
    generated_at: str


@dataclass
class RuleExecutionResult:
    success: bool
    trace: Optional[CalculationTrace] = None
    missing_inputs: list[RuleInput] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class RulePack:
    rule_id: str
    name: str
    jurisdiction: str
    version: str
    source_document: str
    source_article: str
    inputs: list[RuleInput]
    formula_fn: Callable[[dict[str, Any]], tuple[dict[str, Any], str]]
    conditions: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None

    def execute(self, inputs: dict[str, Any]) -> RuleExecutionResult:
        """Girdileri denetler; eksik varsa reddeder, tamsa formülü çalıştırıp
        CalculationTrace üretir."""

        missing: list[RuleInput] = []
        clean_inputs: dict[str, Any] = {}

        for inp in self.inputs:
            val = inputs.get(inp.name)
            if val is None and inp.default is not None:
                val = inp.default

            if val is None or val == "":
                if inp.required:
                    missing.append(inp)
            else:
                try:
                    if inp.type == "float":
                        clean_inputs[inp.name] = float(val)
                    elif inp.type == "int":
                        clean_inputs[inp.name] = int(val)
                    elif inp.type == "bool":
                        clean_inputs[inp.name] = bool(val)
                    else:
                        clean_inputs[inp.name] = str(val)
                except (ValueError, TypeError):
                    return RuleExecutionResult(
                        success=False,
                        error_message=f"'{inp.name}' alanı geçerli bir {inp.type} değeri olmalıdır (Gelen: {val}).",
                    )

        if missing:
            return RuleExecutionResult(
                success=False,
                missing_inputs=missing,
                error_message=f"Hesaplama için eksik zorunlu alanlar var: {', '.join(m.name for m in missing)}",
            )

        try:
            result_data, method_desc = self.formula_fn(clean_inputs)
        except Exception as e:
            return RuleExecutionResult(
                success=False,
                error_message=f"Formül çalıştırma hatası: {e}",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        trace = CalculationTrace(
            trace_id=str(uuid.uuid4()),
            rule_id=self.rule_id,
            rule_name=self.name,
            inputs=clean_inputs,
            method=method_desc,
            result=result_data,
            source_document=self.source_document,
            source_article=self.source_article,
            confidence=ConfidenceLevel.HIGH,
            generated_at=now_iso,
        )

        return RuleExecutionResult(success=True, trace=trace)
