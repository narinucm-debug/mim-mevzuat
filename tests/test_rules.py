"""Rule Engine ve Interpreter testleri - Deterministik hesap ve mimari yorumları doğrular."""

from mim_mevzuat.interpreter import interpret_calculation
from mim_mevzuat.rules.engine import RuleEngine
from mim_mevzuat.rules.otopark import RULE_OTOPARK_KONUT
from mim_mevzuat.rules.emsal import RULE_EMSAL_TAKS


def test_rule_otopark_execution():
    engine = RuleEngine()
    # 40 daire, 30 otopark -> 10 eksik
    res = engine.execute("rule:otopark:konut:v2022", {"unit_count": 40, "existing_parking": 30})
    assert res.success is True
    assert res.trace is not None
    assert res.trace.result["required_parking"] == 40
    assert res.trace.result["difference"] == -10
    assert res.trace.result["status"] == "YETERSİZ"
    assert res.trace.result["accessible_parking_required"] == 2
    assert res.trace.result["ev_charging_parking_required"] == 2

    # Mimari yorum kontrolü
    interp = interpret_calculation(res.trace, project_name="Çankaya Konut")
    assert "YETERSİZ" in interp.verdict
    assert len(interp.design_recommendations) >= 3
    assert any("Bodrum" in r for r in interp.design_recommendations)


def test_rule_emsal_execution():
    engine = RuleEngine()
    # 1000 m2 parsel, KAKS 1.5 -> Max 1500 m2 emsal. Önerilen 1800 m2 -> 300 m2 aşım
    res = engine.execute(
        "rule:imar:emsal_taks:v2026",
        {"parcel_area": 1000, "kaks": 1.5, "taks": 0.35, "actual_emsal_area": 1800},
    )
    assert res.success is True
    assert res.trace.result["max_allowed_emsal_area"] == 1500.0
    assert res.trace.result["excess_area"] == 300.0
    assert res.trace.result["status"] == "EMSAL_ASIMI"

    interp = interpret_calculation(res.trace)
    assert "EMSAL AŞIMI" in interp.verdict
    assert any("Madde 22" in r for r in interp.design_recommendations)


def test_rule_missing_required_input_fails_without_guess():
    engine = RuleEngine()
    # Gerekli parcel_area eksik
    res = engine.execute("rule:imar:emsal_taks:v2026", {"kaks": 1.5})
    assert res.success is False
    assert len(res.missing_inputs) > 0
    assert any(m.name == "parcel_area" for m in res.missing_inputs)
