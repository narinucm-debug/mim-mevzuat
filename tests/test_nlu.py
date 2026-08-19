"""NLU testleri - Kullanıcı doğal dil ifadelerinden parametre ve niyet çıkarımı."""

from mim_mevzuat.nlu import extract_entities_from_text, parse_user_intent


def test_extract_parking_parameters():
    text = "Çankaya'da 40 dairelik konut projesi yapıyorum, 30 araçlık otopark ayırdım kurtarır mı?"
    intent = parse_user_intent(text)

    assert intent.intent == "PARKING_CALC"
    assert intent.entities.jurisdiction == "TR.Ankara.Cankaya"
    assert intent.entities.unit_count == 40
    assert intent.entities.existing_parking == 30
    assert "otopark" in intent.detected_topics


def test_extract_emsal_parameters():
    text = "1500 m2 arsam var emsal 1.50, taks 0.35, toplam inşaat alanım 2400 m2 oldu aşım var mı?"
    intent = parse_user_intent(text)

    assert intent.intent == "EMSAL_CALC"
    assert intent.entities.parcel_area == 1500.0
    assert intent.entities.kaks == 1.50
    assert intent.entities.taks == 0.35
    assert intent.entities.proposed_gross_area == 2400.0


def test_general_qa_intent():
    text = "Planlı Alanlar İmar Yönetmeliğinde emsale dahil edilmeyecek alanlar nelerdir?"
    intent = parse_user_intent(text)

    assert intent.intent == "QA"
    assert "emsal" in intent.detected_topics
