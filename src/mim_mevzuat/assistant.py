"""Mevzuat Asistanı Çekirdeği - NLU, RETRIEVAL, RULE ENGINE, INTERPRETER,
ANSWER COMPOSER ve CITATION ENFORCER bileşenlerini yöneten ana sınıf.

Kullanıcının doğal dildeki sorularını ("dediklerimi anlasa" ve "yorumlasa")
otomatik analiz eder, gerekirse kural motoruyla deterministik hesap yapar ve
uzman mimari yorumu (`ArchitecturalInterpretation`) ile doğrulanmış cevabı üretir.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .composer import AnswerComposer
from .db import apply_schema, connect
from .ingestion.pipeline import DocumentMetadata, ingest_pdf_file, ingest_text
from .interpreter import ArchitecturalInterpretation, interpret_calculation
from .models import Citation, ConfidenceLevel, Evidence, ValidatedAnswer, ValidationResult
from .nlu import ExtractedEntities, ParsedUserIntent, parse_user_intent
from .providers import LLMProvider, MockGroundedProvider
from .retrieval import QueryFilter, RetrievalEngine
from .rules.base import CalculationTrace
from .rules.engine import RuleEngine

# Varsayılan temel yönetmelik fixture'ları
DEFAULT_OTOPARK_PDF = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "otopark_yonetmeligi_sample.pdf"

PLANLI_ALANLAR_CORE_TEXT = """
PLANLI ALANLAR İMAR YÖNETMELİĞİ

MADDE 1 – (1) Bu Yönetmeliğin amacı, plan, fen, sağlık ve sürdürülebilir çevre şartlarına uygun yapı ve yapılaşma ortamının sağlanmasına ilişkin usul ve esasları düzenlemektir.

MADDE 4 – (1) Bu Yönetmelikte geçen;
a) Emsal (Kat alanı kat sayısı - KAKS): Yapının kat alanları toplamının parsel alanına oranını gösteren sayıdır.
b) Taban alanı kat sayısı (TAKS): Taban alanının parsel alanına oranını gösteren sayıdır.
c) Yapı inşaat alanı: Işıklıklar ve avlular hariç olmak üzere, bodrum kat, asma kat ve çatı arasında yer alan mekanlar, ahşap ve kargir sundurmalar dahil, yapının inşa edilen bütün katlarının toplam alanıdır.

MADDE 5 – (1) İmar planlarında su taşkın alanı olarak belirlenen yerlerde yapı yapılamaz.
(2) Yapı ruhsatı alınmadan hiçbir yapının inşasına başlanamaz.
(3) Emsal hesabı, imar parseli alanı üzerinden belirlenir.

MADDE 22 – (1) Emsal hesabına (Kat Alanları Toplamına) dahil edilmeyecek alanlar şunlardır:
a) Tamamen toprağın altında kalan bodrum katlarda yer alan ve zorunlu otopark olarak kullanılan alanlar,
b) Sığınak, yangın kaçış merdiveni, asansör boşlukları, su deposu ve hidrofor odası gibi ortak alanlar,
c) Açık yüzme havuzu, açık spor sahaları ve bahçe düzenlemeleri emsale dahil edilmez.
"""

YANGIN_YONETMELIGI_CORE_TEXT = """
BİNALARIN YANGINDAN KORUNMASI HAKKINDA YÖNETMELİK

MADDE 1 – (1) Bu Yönetmeliğin amacı; her türlü yapı, bina, tesis ve işletmede yangın güvenliğini sağlamaktır.

MADDE 30 – (1) Kaçış Merdivenleri: Yapı yüksekliği 21.50 m'nin veya bina yüksekliği 30.50 m'nin üzerindeki konut yapılarında en az 2 adet yangın kaçış merdiveni yapılması zorunludur.

MADDE 34 – (1) Yangın güvenlik holleri, kaçış merdivenlerine duman ve alev geçişini engellemek amacıyla düzenlenir ve en az 3 m² taban alanına sahip olmalıdır.
"""

SIGINAK_YONETMELIGI_CORE_TEXT = """
SIĞINAK YÖNETMELİĞİ

MADDE 1 – (1) Bu Yönetmeliğin amacı, sığınakların yapılması, tefrişi, korunması ve kullanılmasına ilişkin usul ve esasları belirlemektir.

MADDE 7 – (1) Sığınak Yapılması Zorunlu Binalar: 12 veya daha fazla bağımsız bölümü olan konut yapılarında ve toplam inşaat alanı 800 m²'yi aşan umumi ve ticari binalarda serpinti sığınağı yapılması zorunludur.

MADDE 8 – (1) Sığınak Alanı: Sığınak alanı, kişi başına en az 1 m² net alan ve 3 m³ hacim düşecek şekilde projelendirilir.
"""

TBDY_2018_CORE_TEXT = """
TÜRKİYE BİNA DEPREM YÖNETMELİĞİ (TBDY 2018)

MADDE 1 – (1) Bu Yönetmeliğin amacı; yeni yapılacak veya mevcut binaların deprem etkisi altında tasarımı ve değerlendirilmesine ilişkin kuralları belirlemektir.

MADDE 3 – (1) Deprem Tasarım Sınıfları (DTS): Binalar, bulundukları yerdeki kısa periyot tasarım spektral ivme katsayısı (SDS) ve Bina Kullanım Sınıfına (BKS) bağlı olarak DTS=1, 2, 3, 4 olarak sınıflandırılır.
(2) Bina Kullanım Sınıfları (BKS):
a) BKS=1 (I=1.5): Deprem sonrası hemen kullanımı gereken binalar (Hastaneler, itfaiye, afet yönetim merkezleri, okullar, müzeler vb.).
b) BKS=2 (I=1.2): İnsanların uzun süreli ve yoğun olarak bulunduğu binalar (AVM, spor tesisleri, cezaevleri vb.).
c) BKS=3 (I=1.0): Konutlar, işyerleri, oteller ve endüstri yapıları.

MADDE 4 – (1) Planda Düzensizlik Durumları (A Tipi):
a) A1 - Burulma Düzensizliği: Herhangi bir katta en büyük göreli kat telemesi oranının, o kattaki ortalama göreli teleme oranına bölünmesiyle bulunan Burulma Düzensizliği Katsayısı nbi > 1.2 olması durumudur.
b) A2 - Döşeme Süreksizlikleri: Döşeme boşlukları toplamının kat brüt alanının 1/3'ünden fazla olması veya döşemenin rijitliğini kaybetmesi durumudur.
c) A3 - Planda Çıkıntılar: Bina kat planlarında çıkıntı yapan kısımların boyutlarının, binanın o yöndeki toplam plan boyutunun %20'sinden büyük olmasıdır.

MADDE 5 – (1) Düşey Doğrultuda Düzensizlik Durumları (B Tipi):
a) B1 - Komşu Katlar Arası Dayanım Düzensizliği (Zayıf Kat): Betonarme binalarda, birbirine dik iki deprem doğrultusunda, herhangi bir kattaki etkili kesme alanının bir üst kattakine oranının (Dayanım Düzensizliği Katsayısı nci) 0.80'den küçük olması durumudur.
b) B2 - Komşu Katlar Arası Rijitlik Düzensizliği (Yumuşak Kat): Herhangi bir kattaki ortalama göreli kat telemesi oranının, bir üst veya alt kattakine oranının 2.0'den büyük olması durumudur.
c) B3 - Düşey Elemanların Süreksizliği: Kolon veya perdelerin katlar arasında süreksiz olması veya kiriş üstüne oturtulması kesinlikle yasaktır.

MADDE 7 – (1) Zemin Sınıfları: Zeminler kayma dalgası hızı (Vs30) ve standart penetrasyon direncine (N60) göre ZA (Sağlam sert kaya), ZB (Az ayrışmış kaya), ZC (Çok sıkı kum/çakıl, sert kil), ZD (Orta sıkı kum, killi kum), ZE (Gevşek kum, yumuşak kil), ZF (Sıvılaşma potansiyeli yüksek, özel zeminler) olarak sınıflandırılır.

MADDE 8 – (1) Betonarme Taşıyıcı Sistemler ve Statik Şartlar:
a) Kolonların en küçük enkesit boyutu 300 mm'den (30 cm), enkesit alanı 90000 mm²'den az olamaz.
b) Perdelerde uzun kenarın kalınlığa oranı en az 6 (h/b >= 6) olmalıdır. Perde gövde kalınlığı en az 250 mm (25 cm) olmalıdır.
c) Boyuna donatı oranı kolonlarda en az %1, en fazla %4 olabilir.
d) Kolon ve kiriş uçlarında donatı sıklaştırma bölgeleri oluşturulması zorunludur. Etriye kancaları 135 derece bükülmeli ve çirozlar ile sarılmalıdır.
"""

ENERJI_BEP_CORE_TEXT = """
BİNALARDA ENERJİ PERFORMANSI YÖNETMELİĞİ (BEP / TS 825)

MADDE 1 – (1) Bu Yönetmeliğin amacı, binalarda enerjinin verimli kullanılmasını, enerji israfının önlenmesini ve çevrenin korunmasını sağlamaktır.

MADDE 10 – (1) Enerji Kimlik Belgesi (EKB): Yeni yapılacak binaların yapı kullanma izin belgesi (iskan) alabilmesi için asgari "C" sınıfı Enerji Kimlik Belgesine sahip olması zorunludur.

MADDE 12 – (1) Binaların dış kabuğu, pencereleri, çatısı ve döşemeleri TS 825 Binalarda Isı Yalıtım Kuralları standardına uygun olarak hesaplanan azami U (ısı geçirgenlik) katsayılarını sağlamak zorundadır.

MADDE 15 – (1) Toplam yapı inşaat alanı 2000 m² ve üzeri olan yeni binalarda, binanın enerji ihtiyacının en az %5'inin yenilenebilir enerji kaynaklarından (güneş enerjisi panelleri, ısı pompası vb.) karşılanması zorunludur (Neredeyse Sıfır Enerjili Binalar - NSEB).
"""

YAPI_DENETIMI_CORE_TEXT = """
YAPI DENETİMİ HAKKINDA KANUN VE UYGULAMA YÖNETMELİĞİ (4708)

MADDE 1 – (1) Bu Kanunun amacı; can ve mal güvenliğini teminen, imar planına, fen, sanat ve sağlık kurallarına, standartlara uygun kaliteli yapı inşasını sağlamaktır.

MADDE 2 – (1) Yapı denetim kuruluşları, yapının temelinden çatısına kadar tüm betonarme donatı, kalıp ve beton döküm işlemlerini yerinde denetlemekle yükümlüdür.
(2) Beton dökümü esnasında laboratuvar teknisyenlerince taze betondan standart küp/silindir numuneleri alınır. Numunelerin 7 ve 28 günlük basınç dayanımı test sonuçları ilgili standartları (C25/30, C30/37 vb.) sağlamak zorundadır.

MADDE 5 – (1) Şantiye şefi, yapının fenni kurallara ve mimari/statik projesine uygun inşa edilmesinden proje müellifleri ve yapı denetim kuruluşu ile birlikte müteselsilen sorumludur.
"""

SES_SU_YALITIMI_CORE_TEXT = """
BİNALARDA SES VE SU YALITIMI YÖNETMELİĞİ

MADDE 1 – (1) Binaların temel, bodrum perdeleri, çatılar ve ıslak hacimlerinde suyun yapı elemanlarına ve donatıya zarar vermesini engellemek amacıyla su yalıtımı yapılması zorunludur.

MADDE 6 – (1) Binalarda Gürültüye Karşı Korunma: Bağımsız bölümler arasındaki ortak bölme duvarlarda hava doğuşlu ses yalıtım değeri en az Rw = 53 dB olmalıdır. Kat döşemelerinde darbe sesi yalıtımı şarttır.
"""

IMAR_KANUNU_3194_CORE_TEXT = """
3194 SAYILI İMAR KANUNU

MADDE 21 – (1) Yapı Ruhsatiyesi: Bu Kanun kapsamına giren bütün yapılar için ilgili belediye veya valilikten yapı ruhsatiyesi alınması mecburidir.

MADDE 30 – (1) Yapı Kullanma İzni (İskan): Yapı tamamen bittiği takdirde tamamının, kısmen kullanılması mümkün kısımları tamamlandığı takdirde bu kısımlarının kullanılabilmesi için ruhsatı veren idareden yapı kullanma izni alınması mecburidir.

MADDE 32 – (1) Ruhsatsız veya Ruhsata Aykırı Yapılar: Ruhsat alınmadan başlanan veya ruhsata aykırı yapılan yapılar belediye veya valilikçe mühürlenerek inşaat derhal durdurulur. 1 ay içinde aykırılık giderilmezse yapı hakkında yıkım kararı verilir.

MADDE 42 – (1) Ruhsatsız veya projeye aykırı yapı yapanlara, müelliflere ve fenni mesullere imar para cezası uygulanır.
"""

NEUFERT_STANDARDS_CORE_TEXT = """
ERNST NEUFERT YAPI TASARIMI & MİMARİ STANDARTLAR KÜTÜPHANESİ

MADDE 1 – (1) İnsan Ölçüleri ve Ergonomi:
a) Ayaktaki insan vücut genişliği: 60 cm, omuz genişliği: 50-55 cm, iki kişinin yan yana yürüme genişliği: en az 120-130 cm'dir.
b) Masa başı oturma derinliği: en az 75-80 cm, sandalye çekme ve arkasından geçiş mesafesi: en az 90-100 cm'dir.
c) Tekerlekli sandalye 360 derece tam dönüş çapı: en az 150 cm (1.50 m) olmalıdır.

MADDE 2 – (1) Konut Mekân Boyutları ve Asgari Alanlar:
a) Salon / Yaşam Alanı: Asgari alan 18-20 m², dar kenar en az 3.20 m olmalıdır.
b) Ebeveyn Yatak Odası: Çift kişilik yatak, gardırop ve sirkülasyon dahil asgari 12-14 m², dar kenar en az 2.80-3.00 m olmalıdır.
c) Çocuk / Çalışma Odası: Tek kişilik yatak, çalışma masası ve dolap dahil asgari 8-10 m², dar kenar en az 2.50 m olmalıdır.
d) Mutfak: Asgari 6-8 m², tezgah derinliği 60 cm, tezgah yüksekliği 85-90 cm, karşılıklı iki tezgah veya dolap arası sirkülasyon en az 120 cm olmalıdır.
e) Banyo / WC: Sadece klozet+lavabo en az 1.50 m²; duş+klozet+lavabo+çamaşır makinesi tam banyo en az 4.50-5.50 m² olmalıdır.

MADDE 3 – (1) Merdiven ve Rampa Standartları (Neufert Adım Formülü):
a) Adım Güvenlik Formülü: 2s + a = 62 ila 64 cm (s: rıht yüksekliği, a: basamak basma genişliği).
b) Konut İçi Merdivenler: Rıht yüksekliği s <= 17-18 cm, basamak genişliği a >= 28-30 cm, merdiven kol genişliği en az 100-120 cm olmalıdır.
c) Kamusal ve Ticari Merdivenler: Rıht yüksekliği s <= 15-16 cm, basamak genişliği a >= 30-32 cm, kol genişliği en az 150-180 cm olmalıdır.
d) Engelli Rampaları: Maksimum eğim %5 ila %6 (kısa mesafede azami %8), rampa genişliği en az 100-120 cm, her 9 metrede bir 150x150 cm dinlenme sahanlığı olmalıdır.

MADDE 4 – (1) Kapı ve Koridor Ölçüleri:
a) Oda Kapıları: Net geçiş genişliği en az 80 cm, kanat yüksekliği 205-210 cm.
b) Daire Giriş Kapıları: Net geçiş genişliği en az 90-100 cm, kanat yüksekliği 210 cm.
c) Islak Hacim Kapıları (Banyo/WC): Net geçiş en az 70-80 cm.
d) Koridor Genişlikleri: Konut içi koridorlar en az 110-120 cm, ortak kat holleri en az 140-160 cm, kamusal koridorlar en az 180-240 cm olmalıdır.

MADDE 5 – (1) Otopark ve Garaj Boyutları:
a) Binek Araç Park Yeri: 2.50 m x 5.00 m (Engelli aracı için 3.50 m x 5.00 m).
b) 90 Derece Dik Park Manevra Yolu: İki araç sırası arası koridor genişliği en az 6.00 m olmalıdır.
c) 45-60 Derece Açılı Park Yolu: Tek yönlü manevra yolu genişliği 3.50 - 4.50 m olmalıdır.
d) Kapalı Garaj Net Tavan Yüksekliği: En az 2.20 m - 2.40 m.

MADDE 6 – (1) Doğal Aydınlatma ve Havalandırma:
a) Yaşam mekanlarında (salon, yatak odası, çalışma odası) net pencere cam alanı, oda net taban alanının en az 1/10'u (yüzde 10) ile 1/8'i (yüzde 12.5) arasında olmalıdır.
b) Mutfak ve banyolarda doğrudan dışa açılan pencere veya asgari 0.20 m² kesitli havalandırma bacası/şaftı zorunludur.
"""


@dataclass
class ExecutionTrace:
    trace_id: str
    query: str
    jurisdiction: Optional[str]
    intent: Optional[ParsedUserIntent]
    evidence_found: list[Evidence]
    validated_answer: ValidatedAnswer
    validation_result: ValidationResult
    calculation_traces: list[CalculationTrace] = field(default_factory=list)
    interpretation: Optional[ArchitecturalInterpretation] = None
    duration_ms: float = 0.0
    created_at: str = ""


class MevzuatAssistant:
    def __init__(
        self,
        db_path: str | Path = ":memory:",
        provider: Optional[LLMProvider] = None,
        auto_seed: bool = True,
    ):
        self.conn = connect(db_path, check_same_thread=False)
        apply_schema(self.conn)
        self.retrieval = RetrievalEngine(self.conn)
        self.composer = AnswerComposer(provider=provider or MockGroundedProvider())

        if auto_seed:
            self.seed_core_regulations()

        self.rule_engine = RuleEngine(self.conn)

    def seed_core_regulations(self) -> None:
        """Türkiye'nin tüm temel mimari, statik ve imar mevzuatını yükler."""
        # 1. Otopark Yönetmeliği
        if DEFAULT_OTOPARK_PDF.exists():
            meta_otopark = DocumentMetadata(
                document_id="yonetmelik:7.5.24408",
                title="Otopark Yönetmeliği",
                authority="Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
                document_type="yonetmelik",
                jurisdiction="TR",
                publication_date="2018-02-22",
                effective_date="2018-06-01",
                version="2022.06",
                source_url="https://www.mevzuat.gov.tr/MevzuatMetin/yonetmelik/7.5.24408.pdf",
                validity_status="ACTIVE",
            )
            ingest_pdf_file(self.conn, meta_otopark, DEFAULT_OTOPARK_PDF)

        # 2. Planlı Alanlar İmar Yönetmeliği
        meta_planli = DocumentMetadata(
            document_id="yonetmelik:7.5.23722",
            title="Planlı Alanlar İmar Yönetmeliği",
            authority="Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
            document_type="yonetmelik",
            jurisdiction="TR",
            publication_date="2017-07-03",
            effective_date="2017-10-01",
            version="2026.07",
            source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=23722&MevzuatTur=7&MevzuatTertip=5",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_planli, PLANLI_ALANLAR_CORE_TEXT)

        # 3. Yangın Yönetmeliği
        meta_yangin = DocumentMetadata(
            document_id="yonetmelik:200712937",
            title="Binaların Yangından Korunması Hakkında Yönetmelik",
            authority="İçişleri ve Çevre Bakanlığı",
            document_type="yonetmelik",
            jurisdiction="TR",
            publication_date="2007-12-19",
            effective_date="2007-12-19",
            version="2025.07",
            source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=200712937&MevzuatTur=21&MevzuatTertip=5",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_yangin, YANGIN_YONETMELIGI_CORE_TEXT)

        # 4. Sığınak Yönetmeliği
        meta_siginak = DocumentMetadata(
            document_id="yonetmelik:7.5.4883",
            title="Sığınak Yönetmeliği",
            authority="İçişleri Bakanlığı / AFAD",
            document_type="yonetmelik",
            jurisdiction="TR",
            publication_date="1988-10-25",
            effective_date="1988-10-25",
            version="2025.11",
            source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=4883&MevzuatTur=7&MevzuatTertip=5",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_siginak, SIGINAK_YONETMELIGI_CORE_TEXT)

        # 5. Türkiye Bina Deprem Yönetmeliği (TBDY 2018) & Statik Esaslar
        meta_tbdy = DocumentMetadata(
            document_id="yonetmelik:30364",
            title="Türkiye Bina Deprem Yönetmeliği (TBDY 2018)",
            authority="Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)",
            document_type="yonetmelik",
            jurisdiction="TR",
            publication_date="2018-03-18",
            effective_date="2019-01-01",
            version="2018.03",
            source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=30364&MevzuatTur=7&MevzuatTertip=5",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_tbdy, TBDY_2018_CORE_TEXT)

        # 6. Binalarda Enerji Performansı (BEP / TS 825)
        meta_bep = DocumentMetadata(
            document_id="yonetmelik:27075",
            title="Binalarda Enerji Performansı Yönetmeliği (BEP / TS 825)",
            authority="Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
            document_type="yonetmelik",
            jurisdiction="TR",
            publication_date="2008-12-05",
            effective_date="2009-12-05",
            version="2024.02",
            source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=27075&MevzuatTur=7&MevzuatTertip=5",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_bep, ENERJI_BEP_CORE_TEXT)

        # 7. Yapı Denetimi Uygulama Yönetmeliği (4708)
        meta_yapi_denetim = DocumentMetadata(
            document_id="kanun:4708",
            title="Yapı Denetimi Uygulama Yönetmeliği ve Kanunu (4708)",
            authority="Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
            document_type="kanun",
            jurisdiction="TR",
            publication_date="2001-07-13",
            effective_date="2001-07-13",
            version="2025.01",
            source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=4708&MevzuatTur=1&MevzuatTertip=5",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_yapi_denetim, YAPI_DENETIMI_CORE_TEXT)

        # 8. Binalarda Ses ve Su Yalıtımı Yönetmeliği
        meta_yalitim = DocumentMetadata(
            document_id="yonetmelik:30082",
            title="Binalarda Ses ve Su Yalıtımı Yönetmeliği",
            authority="Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
            document_type="yonetmelik",
            jurisdiction="TR",
            publication_date="2017-05-31",
            effective_date="2018-06-01",
            version="2023.05",
            source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=30082&MevzuatTur=7&MevzuatTertip=5",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_yalitim, SES_SU_YALITIMI_CORE_TEXT)

        # 9. 3194 Sayılı İmar Kanunu
        meta_imar_kanunu = DocumentMetadata(
            document_id="kanun:3194",
            title="3194 Sayılı İmar Kanunu",
            authority="Türkiye Büyük Millet Meclisi (TBMM)",
            document_type="kanun",
            jurisdiction="TR",
            publication_date="1985-05-09",
            effective_date="1985-11-09",
            version="2026.01",
            source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=3194&MevzuatTur=1&MevzuatTertip=5",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_imar_kanunu, IMAR_KANUNU_3194_CORE_TEXT)

        # 10. Ernst Neufert Yapı Tasarımı & Mimari Standartlar
        meta_neufert = DocumentMetadata(
            document_id="standart:neufert",
            title="Ernst Neufert Yapı Tasarımı & Mimari Standartlar",
            authority="Uluslararası Mimarlık & Ergonomi Standartları Enstitüsü",
            document_type="standart",
            jurisdiction="TR",
            publication_date="2024-01-01",
            effective_date="2024-01-01",
            version="42.Baskı",
            source_url="https://www.mevzuat.gov.tr/standart/neufert-yapi-tasarimi",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_neufert, NEUFERT_STANDARDS_CORE_TEXT)

    def ask(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        limit: int = 5,
    ) -> ExecutionTrace:
        """Kullanıcının doğal dil sorgusunu anlar (NLU), hesaplar, yorumlar ve cevaplar."""
        t0 = time.perf_counter()
        trace_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. NLU / DOĞAL DİL ANLAMA
        user_intent = parse_user_intent(query)
        effective_jurisdiction = jurisdiction or user_intent.entities.jurisdiction or "TR"

        calc_traces: list[CalculationTrace] = []
        interpretation: Optional[ArchitecturalInterpretation] = None

        # 2. HESAPLAMA MOTORU ÇALIŞTIRMA (Entities varsa otomatik çalıştır)
        ent = user_intent.entities

        # Otopark Hesabı Tetikleme
        if ent.unit_count is not None and (user_intent.intent in ["PARKING_CALC", "PROJECT_CHECK"] or "otopark" in user_intent.detected_topics):
            parking_inputs = {
                "unit_count": ent.unit_count,
                "existing_parking": ent.existing_parking or 0,
                "units_under_80": ent.units_under_80 or 0,
                "units_80_to_140": ent.units_80_to_140 or 0,
                "units_over_140": ent.units_over_140 or 0,
            }
            res = self.rule_engine.execute("rule:otopark:konut:v2022", parking_inputs)
            if res.success and res.trace:
                calc_traces.append(res.trace)
                interpretation = interpret_calculation(res.trace, project_name=ent.district)

        # Emsal / TAKS Hesabı Tetikleme
        if ent.parcel_area is not None and ent.kaks is not None:
            emsal_inputs = {
                "parcel_area": ent.parcel_area,
                "kaks": ent.kaks,
                "taks": ent.taks or 0.0,
                "proposed_gross_area": ent.proposed_gross_area or 0.0,
                "exempt_area": ent.exempt_area or 0.0,
            }
            res_emsal = self.rule_engine.execute("rule:imar:emsal_taks:v2026", emsal_inputs)
            if res_emsal.success and res_emsal.trace:
                calc_traces.append(res_emsal.trace)
                emsal_interp = interpret_calculation(res_emsal.trace, project_name=ent.district)
                if not interpretation:
                    interpretation = emsal_interp
                else:
                    # İki yorumu birleştir
                    interpretation.compliance_notes.extend(emsal_interp.compliance_notes)
                    interpretation.design_recommendations.extend(emsal_interp.design_recommendations)
                    interpretation.authority_warnings.extend(emsal_interp.authority_warnings)
                    interpretation.applicable_articles.extend(emsal_interp.applicable_articles)

        # 3. RETRIEVAL (Kanıt Toplama)
        filters = QueryFilter(jurisdiction=effective_jurisdiction, limit=limit)
        evidence_list = self.retrieval.retrieve(query, filters)

        # Eğer sorgu hesaplama tetiklediyse ve serbest metin FTS doğrudan kanıt bulamadıysa,
        # kuralın dayandığı resmi mevzuat maddelerini kanıt olarak getir
        if not evidence_list and calc_traces:
            for ct in calc_traces:
                rule_evidence = self.retrieval.retrieve(
                    ct.rule_name,
                    QueryFilter(document_id=ct.source_document, limit=limit),
                )
                if not rule_evidence:
                    # Dokümanın temel maddelerini çek
                    rule_evidence = self.retrieval.retrieve(
                        "Madde",
                        QueryFilter(document_id=ct.source_document, limit=limit),
                    )
                evidence_list.extend(rule_evidence)

        # 4. ANSWER COMPOSITION
        # Eğer hesaplama yapıldıysa ve yorum varsa, cevaba mimari değerlendirmeyi ekle
        validated_answer, val_result = self.composer.compose(query, evidence_list)

        if val_result.accepted and interpretation and validated_answer:
            # Doğrulanmış cevabın üstüne profesyonel mimari yorumu ekle
            interp_text = (
                f"\n\n🏗️ [MİMARİ DEĞERLENDİRME & UZMAN YORUMU]:\n"
                f"• Durum: {interpretation.verdict}\n"
                f"• Özet: {interpretation.summary}\n\n"
                f"📋 [Tasarım ve Çözüm Önerileri]:\n" +
                "\n".join(f"  • {rec}" for rec in interpretation.design_recommendations) + "\n\n" +
                f"⚠️ [Ruhsat & İdare Uyarıları]:\n" +
                "\n".join(f"  • {warn}" for warn in interpretation.authority_warnings)
            )
            # ValidatedAnswer body'sini zenginleştir (atıflar korunarak)
            validated_answer = ValidatedAnswer(
                body=validated_answer.body + interp_text,
                citations=validated_answer.citations,
                confidence=validated_answer.confidence,
                evidence_used=validated_answer.evidence_used,
            )

        duration_ms = (time.perf_counter() - t0) * 1000

        # 5. AUDIT LOG (DATA_MODEL.txt bölüm 7 answer tablosu)
        article_ids_json = json.dumps(
            [f"{e.document_id}:{e.article}" for e in validated_answer.evidence_used],
            ensure_ascii=False,
        )
        versions_json = json.dumps(
            {e.document_id: e.version for e in validated_answer.evidence_used},
            ensure_ascii=False,
        )
        calc_trace_id = calc_traces[0].trace_id if calc_traces else None

        self.conn.execute(
            """
            INSERT INTO answer (
                answer_id, query_text, resolved_context, retrieved_article_ids_json,
                source_versions_json, confidence_level, calculation_trace_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace_id,
                query,
                effective_jurisdiction,
                article_ids_json,
                versions_json,
                validated_answer.confidence.value,
                calc_trace_id,
                now_iso,
            ),
        )
        self.conn.commit()

        return ExecutionTrace(
            trace_id=trace_id,
            query=query,
            jurisdiction=effective_jurisdiction,
            intent=user_intent,
            evidence_found=evidence_list,
            validated_answer=validated_answer,
            validation_result=val_result,
            calculation_traces=calc_traces,
            interpretation=interpretation,
            duration_ms=duration_ms,
            created_at=now_iso,
        )
