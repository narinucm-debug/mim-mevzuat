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


def test_extract_various_nationwide_districts():
    # Konya Selçuklu
    intent1 = parse_user_intent("Selçuklu'da 50 dairelik site yapıyoruz")
    assert intent1.entities.jurisdiction == "TR.Konya.Selcuklu"
    assert intent1.entities.unit_count == 50

    # Muğla Bodrum
    intent2 = parse_user_intent("Bodrum Yalıkavak'ta 8 villalık otopark hesabı")
    assert intent2.entities.jurisdiction == "TR.Mugla.Bodrum"

    # Trabzon Akçaabat
    intent3 = parse_user_intent("Akçaabat sahilinde 2000 m2 arsa emsal 1.20")
    assert intent3.entities.jurisdiction == "TR.Trabzon.Akcaabat"
    assert intent3.entities.parcel_area == 2000.0
    assert intent3.entities.kaks == 1.20

    # Bursa Nilüfer
    intent4 = parse_user_intent("Nilüfer Özlüce 30 daire")
    assert intent4.entities.jurisdiction == "TR.Bursa.Nilufer"
    assert intent4.entities.unit_count == 30

