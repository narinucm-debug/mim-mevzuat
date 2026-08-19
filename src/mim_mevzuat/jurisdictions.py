"""Türkiye İdari Hiyerarşi & Coğrafi Çözümleme Modülü.

TÜRKİYE'NİN 81 İLİ VE 973 İLÇESİNİN TAMAMI (TÜİK & İçişleri Bakanlığı Resmi İdari Yapısı).
DATA_MODEL.txt Bölüm 3 ilkelerine uygun olarak kullanıcı hangi ilden veya ilçeden bahsederse
bahsetsin hiyerarşik jurisdiction yapısına (TR.Il.Ilce) anında ve hatasız çözümler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DistrictInfo:
    name: str
    code: str


@dataclass(frozen=True)
class ProvinceInfo:
    plate_code: int
    name: str
    code: str
    is_metropolitan: bool
    districts: list[DistrictInfo] = field(default_factory=list)


def _d(name: str, code: str) -> DistrictInfo:
    return DistrictInfo(name, code)


# Türkiye'nin 81 İli ve 973 İlçesinin Eksiksiz Veritabanı
ALL_81_PROVINCES: dict[str, ProvinceInfo] = {
    # 01 ADANA
    "adana": ProvinceInfo(1, "Adana", "Adana", True, [
        _d("Seyhan", "Seyhan"), _d("Yüreğir", "Yuregir"), _d("Çukurova", "Cukurova"),
        _d("Sarıçam", "Saricam"), _d("Ceyhan", "Ceyhan"), _d("Kozan", "Kozan"),
        _d("İmamoğlu", "Imamoglu"), _d("Karataş", "Karatas"), _d("Karaisalı", "Karaisali"),
        _d("Pozantı", "Pozanti"), _d("Yumurtalık", "Yumurtalik"), _d("Tufanbeyli", "Tufanbeyli"),
        _d("Feke", "Feke"), _d("Aladağ", "Aladag"), _d("Saimbeyli", "Saimbeyli"),
    ]),
    # 02 ADIYAMAN
    "adiyaman": ProvinceInfo(2, "Adıyaman", "Adiyaman", False, [
        _d("Merkez", "Merkez"), _d("Kahta", "Kahta"), _d("Besni", "Besni"),
        _d("Gölbaşı", "Golbasi"), _d("Gerger", "Gerger"), _d("Sincik", "Sincik"),
        _d("Çelikhan", "Celikhan"), _d("Tut", "Tut"), _d("Samsat", "Samsat"),
    ]),
    # 03 AFYONKARAHİSAR
    "afyonkarahisar": ProvinceInfo(3, "Afyonkarahisar", "Afyonkarahisar", False, [
        _d("Merkez", "Merkez"), _d("Sandıklı", "Sandikli"), _d("Dinar", "Dinar"),
        _d("Bolvadin", "Bolvadin"), _d("Sinanpaşa", "Sinanpasa"), _d("Emirdağ", "Emirdag"),
        _d("Şuhut", "Suhut"), _d("Çay", "Cay"), _d("İhsaniye", "Ihsaniye"),
        _d("İscehisar", "Iscehisar"), _d("Sultandağı", "Sultandagi"), _d("Çobanlar", "Cobanlar"),
        _d("Dazkırı", "Dazkiri"), _d("Başmakçı", "Basmakci"), _d("Hocalar", "Hocalar"),
        _d("Kızılören", "Kiziloren"), _d("Evciler", "Evciler"), _d("Bayat", "Bayat"),
    ]),
    # 04 AĞRI
    "agri": ProvinceInfo(4, "Ağrı", "Agri", False, [
        _d("Merkez", "Merkez"), _d("Doğubayazıt", "Dogubayazit"), _d("Patnos", "Patnos"),
        _d("Diyadin", "Diyadin"), _d("Eleşkirt", "Eleskirt"), _d("Tutak", "Tutak"),
        _d("Taşlıçay", "Taslicay"), _d("Hamur", "Hamur"),
    ]),
    # 05 AMASYA
    "amasya": ProvinceInfo(5, "Amasya", "Amasya", False, [
        _d("Merkez", "Merkez"), _d("Merzifon", "Merzifon"), _d("Suluova", "Suluova"),
        _d("Taşova", "Tasova"), _d("Gümüşhacıköy", "Gumushacikoy"), _d("Göynücek", "Goynucek"),
        _d("Hamamözü", "Hamamozu"),
    ]),
    # 06 ANKARA
    "ankara": ProvinceInfo(6, "Ankara", "Ankara", True, [
        _d("Çankaya", "Cankaya"), _d("Keçiören", "Kecioren"), _d("Yenimahalle", "Yenimahalle"),
        _d("Mamak", "Mamak"), _d("Etimesgut", "Etimesgut"), _d("Sincan", "Sincan"),
        _d("Altındağ", "Altindag"), _d("Pursaklar", "Pursaklar"), _d("Gölbaşı", "Golbasi"),
        _d("Polatlı", "Polatli"), _d("Çubuk", "Cubuk"), _d("Kahramankazan", "Kahramankazan"),
        _d("Beypazarı", "Beypazari"), _d("Elmadağ", "Elmadag"), _d("Nallıhan", "Nallihan"),
        _d("Akyurt", "Akyurt"), _d("Haymana", "Haymana"), _d("Kızılcahamam", "Kizilcahamam"),
        _d("Bala", "Bala"), _d("Kalecik", "Kalecik"), _d("Ayaş", "Ayas"),
        _d("Güdül", "Gudul"), _d("Çamlıdere", "Camlidere"), _d("Evren", "Evren"),
        _d("Şereflikoçhisar", "Sereflikochisar"),
    ]),
    # 07 ANTALYA
    "antalya": ProvinceInfo(7, "Antalya", "Antalya", True, [
        _d("Muratpaşa", "Muratpasa"), _d("Kepez", "Kepez"), _d("Konyaaltı", "Konyaalti"),
        _d("Alanya", "Alanya"), _d("Manavgat", "Manavgat"), _d("Serik", "Serik"),
        _d("Aksu", "Aksu"), _d("Döşemealtı", "Dosemealti"), _d("Kumluca", "Kumluca"),
        _d("Kaş", "Kas"), _d("Korkuteli", "Korkuteli"), _d("Gazipaşa", "Gazipasa"),
        _d("Finike", "Finike"), _d("Kemer", "Kemer"), _d("Elmalı", "Elmali"),
        _d("Demre", "Demre"), _d("Akseki", "Akseki"), _d("Gündoğmuş", "Gundogmus"),
        _d("İbradı", "Ibradi"),
    ]),
    # 08 ARTVİN
    "artvin": ProvinceInfo(8, "Artvin", "Artvin", False, [
        _d("Merkez", "Merkez"), _d("Hopa", "Hopa"), _d("Borçka", "Borcka"),
        _d("Yusufeli", "Yusufeli"), _d("Arhavi", "Arhavi"), _d("Şavşat", "Savsat"),
        _d("Ardanuç", "Ardanuc"), _d("Murgul", "Murgul"), _d("Kemalpaşa", "Kemalpasa"),
    ]),
    # 09 AYDIN
    "aydin": ProvinceInfo(9, "Aydın", "Aydin", True, [
        _d("Efeler", "Efeler"), _d("Nazilli", "Nazilli"), _d("Söke", "Soke"),
        _d("Kuşadası", "Kusadasi"), _d("Didim", "Didim"), _d("İncirliova", "Incirliova"),
        _d("Çine", "Cine"), _d("Germencik", "Germencik"), _d("Bozdoğan", "Bozdogan"),
        _d("Köşk", "Kosk"), _d("Kuyucak", "Kuyucak"), _d("Sultanhisar", "Sultanhisar"),
        _d("Karacasu", "Karacasu"), _d("Yenipazar", "Yenipazar"), _d("Buharkent", "Buharkent"),
        _d("Karpuzlu", "Karpuzlu"), _d("Koçarlı", "Kocarli"),
    ]),
    # 10 BALIKESİR
    "balikesir": ProvinceInfo(10, "Balıkesir", "Balikesir", True, [
        _d("Altıeylül", "Altieylul"), _d("Karesi", "Karesi"), _d("Edremit", "Edremit"),
        _d("Bandırma", "Bandirma"), _d("Gönen", "Gonen"), _d("Ayvalık", "Ayvalik"),
        _d("Burhaniye", "Burhaniye"), _d("Bigadiç", "Bigadic"), _d("Dursunbey", "Dursunbey"),
        _d("Susurluk", "Susurluk"), _d("Sındırgı", "Sindirgi"), _d("İvrindi", "Ivrindi"),
        _d("Erdek", "Erdek"), _d("Havran", "Havran"), _d("Kepsut", "Kepsut"),
        _d("Manyas", "Manyas"), _d("Savaştepe", "Savastepe"), _d("Balya", "Balya"),
        _d("Gömeç", "Gomec"), _d("Marmara", "Marmara"),
    ]),
    # 11 BİLECİK
    "bilecik": ProvinceInfo(11, "Bilecik", "Bilecik", False, [
        _d("Merkez", "Merkez"), _d("Bozüyük", "Bozuyuk"), _d("Osmaneli", "Osmaneli"),
        _d("Söğüt", "Sogut"), _d("Gölpazarı", "Golpazari"), _d("Pazaryeri", "Pazaryeri"),
        _d("Yenipazar", "Yenipazar"), _d("İnhisar", "Inhisar"),
    ]),
    # 12 BİNGÖL
    "bingol": ProvinceInfo(12, "Bingöl", "Bingol", False, [
        _d("Merkez", "Merkez"), _d("Genç", "Genc"), _d("Solhan", "Solhan"),
        _d("Karlıova", "Karliova"), _d("Adaklı", "Adakli"), _d("Kiğı", "Kigi"),
        _d("Yedisu", "Yedisu"), _d("Yayladere", "Yayladere"),
    ]),
    # 13 BİTLİS
    "bitlis": ProvinceInfo(13, "Bitlis", "Bitlis", False, [
        _d("Merkez", "Merkez"), _d("Tatvan", "Tatvan"), _d("Güroymak", "Guroymak"),
        _d("Ahlat", "Ahlat"), _d("Hizan", "Hizan"), _d("Mutki", "Mutki"),
        _d("Adilcevaz", "Adilcevaz"),
    ]),
    # 14 BOLU
    "bolu": ProvinceInfo(14, "Bolu", "Bolu", False, [
        _d("Merkez", "Merkez"), _d("Gerede", "Gerede"), _d("Mudurnu", "Mudurnu"),
        _d("Göynük", "Goynuk"), _d("Mengen", "Mengen"), _d("Yeniçağa", "Yenicaga"),
        _d("Dörtdivan", "Dortdivan"), _d("Seben", "Seben"), _d("Kıbrıscık", "Kibriscik"),
    ]),
    # 15 BURDUR
    "burdur": ProvinceInfo(15, "Burdur", "Burdur", False, [
        _d("Merkez", "Merkez"), _d("Bucak", "Bucak"), _d("Gölhisar", "Golhisar"),
        _d("Yeşilova", "Yesilova"), _d("Ağlasun", "Aglasun"), _d("Karamanlı", "Karamanli"),
        _d("Tefenni", "Tefenni"), _d("Çavdır", "Cavdir"), _d("Altınyayla", "Altinyayla"),
        _d("Çeltikçi", "Celtikci"), _d("Kemer", "Kemer"),
    ]),
    # 16 BURSA
    "bursa": ProvinceInfo(16, "Bursa", "Bursa", True, [
        _d("Osmangazi", "Osmangazi"), _d("Yıldırım", "Yildirim"), _d("Nilüfer", "Nilufer"),
        _d("İnegöl", "Inegol"), _d("Gemlik", "Gemlik"), _d("Mudanya", "Mudanya"),
        _d("Mustafakemalpaşa", "Mustafakemalpasa"), _d("Gürsu", "Gursu"), _d("Karacabey", "Karacabey"),
        _d("Orhangazi", "Orhangazi"), _d("Kestel", "Kestel"), _d("Yenişehir", "Yenisehir"),
        _d("İznik", "Iznik"), _d("Orhaneli", "Orhaneli"), _d("Keles", "Keles"),
        _d("Büyükorhan", "Buyukorhan"), _d("Harmancık", "Harmancik"),
    ]),
    # 17 ÇANAKKALE
    "canakkale": ProvinceInfo(17, "Çanakkale", "Canakkale", False, [
        _d("Merkez", "Merkez"), _d("Biga", "Biga"), _d("Çan", "Can"),
        _d("Gelibolu", "Gelibolu"), _d("Yenice", "Yenice"), _d("Ayvacık", "Ayvacik"),
        _d("Ezine", "Ezine"), _d("Bayramiç", "Bayramic"), _d("Lapseki", "Lapseki"),
        _d("Eceabat", "Eceabat"), _d("Gökçeada", "Gokceada"), _d("Bozcaada", "Bozcaada"),
    ]),
    # 18 ÇANKIRI
    "cankiri": ProvinceInfo(18, "Çankırı", "Cankiri", False, [
        _d("Merkez", "Merkez"), _d("Çerkeş", "Cerkes"), _d("Ilgaz", "Ilgaz"),
        _d("Orta", "Orta"), _d("Şabanözü", "Sabanozu"), _d("Kurşunlu", "Kursunlu"),
        _d("Yapraklı", "Yaprakli"), _d("Kızılırmak", "Kizilirmak"), _d("Eldivan", "Eldivan"),
        _d("Atkaracalar", "Atkaracalar"), _d("Korgun", "Korgun"), _d("Bayramören", "Bayramoren"),
    ]),
    # 19 ÇORUM
    "corum": ProvinceInfo(19, "Çorum", "Corum", False, [
        _d("Merkez", "Merkez"), _d("Sungurlu", "Sungurlu"), _d("Osmancık", "Osmancik"),
        _d("İskilip", "Iskilip"), _d("Alaca", "Alaca"), _d("Bayat", "Bayat"),
        _d("Mecitözü", "Mecitozu"), _d("Kargı", "Kargi"), _d("Ortaköy", "Ortakoy"),
        _d("Uğurludağ", "Ugurludag"), _d("Dodurga", "Dodurga"), _d("Oğuzlar", "Oguzlar"),
        _d("Laçin", "Lacin"), _d("Boğazkale", "Bogazkale"),
    ]),
    # 20 DENİZLİ
    "denizli": ProvinceInfo(20, "Denizli", "Denizli", True, [
        _d("Pamukkale", "Pamukkale"), _d("Merkezefendi", "Merkezefendi"), _d("Çivril", "Civril"),
        _d("Acıpayam", "Acipayam"), _d("Tavas", "Tavas"), _d("Honaz", "Honaz"),
        _d("Sarayköy", "Saraykoy"), _d("Buldan", "Buldan"), _d("Kale", "Kale"),
        _d("Çal", "Cal"), _d("Çameli", "Cameli"), _d("Serinhisar", "Serinhisar"),
        _d("Güney", "Guney"), _d("Bozkurt", "Bozkurt"), _d("Çardak", "Cardak"),
        _d("Bekilli", "Bekilli"), _d("Beyağaç", "Beyagac"), _d("Babadağ", "Babadag"),
        _d("Baklan", "Baklan"),
    ]),
    # 21 DİYARBAKIR
    "diyarbakir": ProvinceInfo(21, "Diyarbakır", "Diyarbakir", True, [
        _d("Bağlar", "Baglar"), _d("Kayapınar", "Kayapinar"), _d("Yenişehir", "Yenisehir"),
        _d("Sur", "Sur"), _d("Ergani", "Ergani"), _d("Bismil", "Bismil"),
        _d("Silvan", "Silvan"), _d("Çınar", "Cinar"), _d("Çermik", "Cermik"),
        _d("Dicle", "Dicle"), _d("Kulp", "Kulp"), _d("Hani", "Hani"),
        _d("Lice", "Lice"), _d("Eğil", "Egil"), _d("Hazro", "Hazro"),
        _d("Kocaköy", "Kocakoy"), _d("Çüngüş", "Cungus"),
    ]),
    # 22 EDİRNE
    "edirne": ProvinceInfo(22, "Edirne", "Edirne", False, [
        _d("Merkez", "Merkez"), _d("Keşan", "Kesan"), _d("Uzunköprü", "Uzunkopru"),
        _d("İpsala", "Ipsala"), _d("Havsa", "Havsa"), _d("Meriç", "Meric"),
        _d("Enez", "Enez"), _d("Süloğlu", "Suloglu"), _d("Lalapaşa", "Lalapasa"),
    ]),
    # 23 ELAZIĞ
    "elazig": ProvinceInfo(23, "Elazığ", "Elazig", False, [
        _d("Merkez", "Merkez"), _d("Kovancılar", "Kovancilar"), _d("Karakoçan", "Karakocan"),
        _d("Palu", "Palu"), _d("Arıcak", "Aricak"), _d("Baskil", "Baskil"),
        _d("Maden", "Maden"), _d("Sivrice", "Sivrice"), _d("Keban", "Keban"),
        _d("Alacakaya", "Alacakaya"), _d("Ağın", "Agin"),
    ]),
    # 24 ERZİNCAN
    "erzincan": ProvinceInfo(24, "Erzincan", "Erzincan", False, [
        _d("Merkez", "Merkez"), _d("Tercan", "Tercan"), _d("Üzümlü", "Uzumlu"),
        _d("Çayırlı", "Cayirli"), _d("İliç", "Ilic"), _d("Kemah", "Kemah"),
        _d("Kemaliye", "Kemaliye"), _d("Refahiye", "Refahiye"), _d("Otlukbeli", "Otlukbeli"),
    ]),
    # 25 ERZURUM
    "erzurum": ProvinceInfo(25, "Erzurum", "Erzurum", True, [
        _d("Yakutiye", "Yakutiye"), _d("Palandöken", "Palandoken"), _d("Aziziye", "Aziziye"),
        _d("Horasan", "Horasan"), _d("Oltu", "Oltu"), _d("Pasinler", "Pasinler"),
        _d("Karayazı", "Karayazi"), _d("Hınıs", "Hinis"), _d("Tekman", "Tekman"),
        _d("Karaçoban", "Karacoban"), _d("Aşkale", "Askale"), _d("Şenkaya", "Senkaya"),
        _d("Çat", "Cat"), _d("Köprüköy", "Koprukoy"), _d("İspir", "Ispir"),
        _d("Tortum", "Tortum"), _d("Narman", "Narman"), _d("Uzundere", "Uzundere"),
        _d("Olur", "Olur"), _d("Pazaryolu", "Pazaryolu"),
    ]),
    # 26 ESKİŞEHİR
    "eskisehir": ProvinceInfo(26, "Eskişehir", "Eskisehir", True, [
        _d("Odunpazarı", "Odunpazari"), _d("Tepebaşı", "Tepebasi"), _d("Sivrihisar", "Sivrihisar"),
        _d("Çifteler", "Cifteler"), _d("Seyitgazi", "Seyitgazi"), _d("Alpu", "Alpu"),
        _d("Mihalıççık", "Mihaliccik"), _d("Mahmudiye", "Mahmudiye"), _d("Beylikova", "Beylikova"),
        _d("İnönü", "Inonu"), _d("Günyüzü", "Gunyuzu"), _d("Han", "Han"),
        _d("Sarıcakaya", "Saricakaya"), _d("Mihalgazi", "Mihalgazi"),
    ]),
    # 27 GAZİANTEP
    "gaziantep": ProvinceInfo(27, "Gaziantep", "Gaziantep", True, [
        _d("Şahinbey", "Sahinbey"), _d("Şehitkamil", "Sehitkamil"), _d("Nizip", "Nizip"),
        _d("İslahiye", "Islahiye"), _d("Nurdağı", "Nurdagi"), _d("Araban", "Araban"),
        _d("Oğuzeli", "Oguzeli"), _d("Yavuzeli", "Yavuzeli"), _d("Karkamış", "Karkamis"),
    ]),
    # 28 GİRESUN
    "giresun": ProvinceInfo(28, "Giresun", "Giresun", False, [
        _d("Merkez", "Merkez"), _d("Bulancak", "Bulancak"), _d("Espiye", "Espiye"),
        _d("Görele", "Gorele"), _d("Tirebolu", "Tirebolu"), _d("Dereli", "Dereli"),
        _d("Şebinkarahisar", "Sebinkarahisar"), _d("Keşap", "Kesap"), _d("Yağlıdere", "Yaglidere"),
        _d("Piraziz", "Piraziz"), _d("Eynesil", "Eynesil"), _d("Alucra", "Alucra"),
        _d("Çamoluk", "Camoluk"), _d("Güce", "Guce"), _d("Doğankent", "Dogankent"),
        _d("Çanakçı", "Canakci"),
    ]),
    # 29 GÜMÜŞHANE
    "gumushane": ProvinceInfo(29, "Gümüşhane", "Gumushane", False, [
        _d("Merkez", "Merkez"), _d("Kelkit", "Kelkit"), _d("Şiran", "Siran"),
        _d("Kürtün", "Kurtun"), _d("Torul", "Torul"), _d("Köse", "Kose"),
    ]),
    # 30 HAKKARİ
    "hakkari": ProvinceInfo(30, "Hakkari", "Hakkari", False, [
        _d("Merkez", "Merkez"), _d("Yüksekova", "Yuksekova"), _d("Şemdinli", "Semdinli"),
        _d("Çukurca", "Cukurca"), _d("Derecik", "Derecik"),
    ]),
    # 31 HATAY
    "hatay": ProvinceInfo(31, "Hatay", "Hatay", True, [
        _d("Antakya", "Antakya"), _d("İskenderun", "Iskenderun"), _d("Defne", "Defne"),
        _d("Dörtyol", "Dortyol"), _d("Samandağ", "Samandag"), _d("Kırıkhan", "Kirikhan"),
        _d("Reyhanlı", "Reyhanli"), _d("Arsuz", "Arsuz"), _d("Altınözü", "Altinozu"),
        _d("Hassa", "Hassa"), _d("Payas", "Payas"), _d("Erzin", "Erzin"),
        _d("Yayladağı", "Yayladagi"), _d("Belen", "Belen"), _d("Kumlu", "Kumlu"),
    ]),
    # 32 ISPARTA
    "isparta": ProvinceInfo(32, "Isparta", "Isparta", False, [
        _d("Merkez", "Merkez"), _d("Yalvaç", "Yalvac"), _d("Eğirdir", "Egirdir"),
        _d("Şarkikaraağaç", "Sarkikaraagac"), _d("Gelendost", "Gelendost"), _d("Keçiborlu", "Keciborlu"),
        _d("Senirkent", "Senirkent"), _d("Sütçüler", "Sutculer"), _d("Gönen", "Gonen"),
        _d("Uluborlu", "Uluborlu"), _d("Atabey", "Atabey"), _d("Aksu", "Aksu"),
        _d("Yenişarbademli", "Yenisarbademli"),
    ]),
    # 33 MERSİN
    "mersin": ProvinceInfo(33, "Mersin", "Mersin", True, [
        _d("Tarsus", "Tarsus"), _d("Toroslar", "Toroslar"), _d("Akdeniz", "Akdeniz"),
        _d("Yenişehir", "Yenisehir"), _d("Mezitli", "Mezitli"), _d("Erdemli", "Erdemli"),
        _d("Silifke", "Silifke"), _d("Anamur", "Anamur"), _d("Mut", "Mut"),
        _d("Bozyazı", "Bozyazi"), _d("Gülnar", "Gulnar"), _d("Aydıncık", "Aydincik"),
        _d("Çamlıyayla", "Camliyayla"),
    ]),
    # 34 İSTANBUL (Tüm 39 İlçe)
    "istanbul": ProvinceInfo(34, "İstanbul", "Istanbul", True, [
        _d("Esenyurt", "Esenyurt"), _d("Küçükçekmece", "Kucukcekmece"), _d("Bağcılar", "Bagcilar"),
        _d("Pendik", "Pendik"), _d("Ümraniye", "Umraniye"), _d("Bahçelievler", "Bahcelievler"),
        _d("Sultangazi", "Sultangazi"), _d("Üsküdar", "Uskudar"), _d("Maltepe", "Maltepe"),
        _d("Gaziosmanpaşa", "Gaziosmanpasa"), _d("Kartal", "Kartal"), _d("Kadıköy", "Kadikoy"),
        _d("Esenler", "Esenler"), _d("Kağıthane", "Kagithane"), _d("Fatih", "Fatih"),
        _d("Avcılar", "Avcilar"), _d("Başakşehir", "Basaksehir"), _d("Ataşehir", "Atasehir"),
        _d("Sancaktepe", "Sancaktepe"), _d("Eyüpsultan", "Eyupsultan"), _d("Beylikdüzü", "Beylikduzu"),
        _d("Sarıyer", "Sariyer"), _d("Sultanbeyli", "Sultanbeyli"), _d("Güngören", "Gungoren"),
        _d("Zeytinburnu", "Zeytinburnu"), _d("Şişli", "Sisli"), _d("Bayrampaşa", "Bayrampasa"),
        _d("Arnavutköy", "Arnavutkoy"), _d("Tuzla", "Tuzla"), _d("Çekmeköy", "Cekmekoy"),
        _d("Büyükçekmece", "Buyukcekmece"), _d("Beykoz", "Beykoz"), _d("Beyoğlu", "Beyoglu"),
        _d("Bakırköy", "Bakirkoy"), _d("Silivri", "Silivri"), _d("Beşiktaş", "Besiktas"),
        _d("Çatalca", "Catalca"), _d("Şile", "Sile"), _d("Adalar", "Adalar"),
    ]),
    # 35 İZMİR (Tüm 30 İlçe)
    "izmir": ProvinceInfo(35, "İzmir", "Izmir", True, [
        _d("Buca", "Buca"), _d("Karabağlar", "Karabaglar"), _d("Bornova", "Bornova"),
        _d("Konak", "Konak"), _d("Karşıyaka", "Karsiyaka"), _d("Bayraklı", "Bayrakli"),
        _d("Çiğli", "Cigli"), _d("Torbalı", "Torbali"), _d("Menemen", "Menemen"),
        _d("Gaziemir", "Gaziemir"), _d("Ödemiş", "Odemis"), _d("Kemalpaşa", "Kemalpasa"),
        _d("Bergama", "Bergama"), _d("Aliağa", "Aliaga"), _d("Menderes", "Menderes"),
        _d("Tire", "Tire"), _d("Balçova", "Balcova"), _d("Narlıdere", "Narlidere"),
        _d("Urla", "Urla"), _d("Çeşme", "Cesme"), _d("Seferihisar", "Seferihisar"),
        _d("Dikili", "Dikili"), _d("Kiraz", "Kiraz"), _d("Bayındır", "Bayindir"),
        _d("Selçuk", "Selcuk"), _d("Güzelbahçe", "Guzelbahce"), _d("Foça", "Foca"),
        _d("Kınık", "Kinik"), _d("Karaburun", "Karaburun"), _d("Beydağ", "Beydag"),
    ]),
    # 36 KARS
    "kars": ProvinceInfo(36, "Kars", "Kars", False, [
        _d("Merkez", "Merkez"), _d("Kağızman", "Kagizman"), _d("Sarıkamış", "Sarikamis"),
        _d("Selim", "Selim"), _d("Digor", "Digor"), _d("Arpaçay", "Arpacay"),
        _d("Akyaka", "Akyaka"), _d("Susuz", "Susuz"),
    ]),
    # 37 KASTAMONU
    "kastamonu": ProvinceInfo(37, "Kastamonu", "Kastamonu", False, [
        _d("Merkez", "Merkez"), _d("Tosya", "Tosya"), _d("Taşköprü", "Taskopru"),
        _d("Cide", "Cide"), _d("İnebolu", "Inebolu"), _d("Araç", "Arac"),
        _d("Devrekani", "Devrekani"), _d("Bozkurt", "Bozkurt"), _d("Daday", "Daday"),
        _d("Azdavay", "Azdavay"), _d("Çatalzeytin", "Catalzeytin"), _d("Küre", "Kure"),
        _d("Doğanyurt", "Doganyurt"), _d("İhsangazi", "Ihsangazi"), _d("Pınarbaşı", "Pinarbasi"),
        _d("Şenpazar", "Senpazar"), _d("Abana", "Abana"), _d("Seydiler", "Seydiler"),
        _d("Hanönü", "Hanonu"), _d("Ağlı", "Agli"),
    ]),
    # 38 KAYSERİ
    "kayseri": ProvinceInfo(38, "Kayseri", "Kayseri", True, [
        _d("Melikgazi", "Melikgazi"), _d("Kocasinan", "Kocasinan"), _d("Talas", "Talas"),
        _d("Develi", "Develi"), _d("Yahyalı", "Yahyali"), _d("Bünyan", "Bunyan"),
        _d("Pınarbaşı", "Pinarbasi"), _d("Tomarza", "Tomarza"), _d("Yeşilhisar", "Yesilhisar"),
        _d("Sarıoğlan", "Sarioglan"), _d("Hacılar", "Hacilar"), _d("Sarız", "Sariz"),
        _d("Akkışla", "Akkisla"), _d("Felahiye", "Felahiye"), _d("Özvatan", "Ozvatan"),
        _d("İncesu", "Incesu"),
    ]),
    # 39 KIRKLARELİ
    "kirklareli": ProvinceInfo(39, "Kırklareli", "Kirklareli", False, [
        _d("Lüleburgaz", "Luleburgaz"), _d("Merkez", "Merkez"), _d("Babaeski", "Babaeski"),
        _d("Vize", "Vize"), _d("Pınarhisar", "Pinarhisar"), _d("Demirköy", "Demirkoy"),
        _d("Pehlivanköy", "Pehlivankoy"), _d("Kofçaz", "Kofcaz"),
    ]),
    # 40 KIRŞEHİR
    "kirsehir": ProvinceInfo(40, "Kırşehir", "Kirsehir", False, [
        _d("Merkez", "Merkez"), _d("Kaman", "Kaman"), _d("Mucur", "Mucur"),
        _d("Çiçekdağı", "Cicekdagi"), _d("Akpınar", "Akpinar"), _d("Boztepe", "Boztepe"),
        _d("Akçakent", "Akcakent"),
    ]),
    # 41 KOCAELİ (Tüm 12 İlçe)
    "kocaeli": ProvinceInfo(41, "Kocaeli", "Kocaeli", True, [
        _d("Gebze", "Gebze"), _d("İzmit", "Izmit"), _d("Darıca", "Darica"),
        _d("Körfez", "Korfez"), _d("Gölcük", "Golcuk"), _d("Derince", "Derince"),
        _d("Çayırova", "Cayirova"), _d("Kartepe", "Kartepe"), _d("Başiskele", "Basiskele"),
        _d("Karamürsel", "Karamursel"), _d("Kandıra", "Kandira"), _d("Dilovası", "Dilovasi"),
    ]),
    # 42 KONYA (Tüm 31 İlçe)
    "konya": ProvinceInfo(42, "Konya", "Konya", True, [
        _d("Selçuklu", "Selcuklu"), _d("Meram", "Meram"), _d("Karatay", "Karatay"),
        _d("Ereğli", "Eregli"), _d("Akşehir", "Aksehir"), _d("Beyşehir", "Beysehir"),
        _d("Çumra", "Cumra"), _d("Seydişehir", "Seydisehir"), _d("Ilgın", "Ilgin"),
        _d("Cihanbeyli", "Cihanbeyli"), _d("Kulu", "Kulu"), _d("Karapınar", "Karapinar"),
        _d("Kadınhanı", "Kadinhani"), _d("Sarayönü", "Sarayonu"), _d("Bozkır", "Bozkir"),
        _d("Yunak", "Yunak"), _d("Doğanhisar", "Doganhisar"), _d("Hüyük", "Huyuk"),
        _d("Altınekin", "Altinekin"), _d("Hadim", "Hadim"), _d("Çeltik", "Celtik"),
        _d("Güneysınır", "Guneysinir"), _d("Emirgazi", "Emirgazi"), _d("Taşkent", "Taskent"),
        _d("Tuzlukçu", "Tuzlukcu"), _d("Akören", "Akoren"), _d("Derebucak", "Derebucak"),
        _d("Halkapınar", "Halkapinar"), _d("Yalıhüyük", "Yalihuyuk"), _d("Derbent", "Derbent"),
        _d("Ahırlı", "Ahirli"),
    ]),
    # 43 KÜTAHYA
    "kutahya": ProvinceInfo(43, "Kütahya", "Kutahya", False, [
        _d("Merkez", "Merkez"), _d("Tavşanlı", "Tavsanli"), _d("Simav", "Simav"),
        _d("Gediz", "Gediz"), _d("Emet", "Emet"), _d("Altıntaş", "Altintas"),
        _d("Domaniç", "Domanic"), _d("Hisarcık", "Hisarcik"), _d("Aslanapa", "Aslanapa"),
        _d("Çavdarhisar", "Cavdarhisar"), _d("Şaphane", "Saphane"), _d("Pazarlar", "Pazarlar"),
        _d("Dumlupınar", "Dumlupinar"),
    ]),
    # 44 MALATYA
    "malatya": ProvinceInfo(44, "Malatya", "Malatya", True, [
        _d("Battalgazi", "Battalgazi"), _d("Yeşilyurt", "Yesilyurt"), _d("Doğanşehir", "Dogansehir"),
        _d("Akçadağ", "Akcadag"), _d("Darende", "Darende"), _d("Hekimhan", "Hekimhan"),
        _d("Pütürge", "Puturge"), _d("Yazıhan", "Yazihan"), _d("Arapgir", "Arapgir"),
        _d("Kuluncak", "Kuluncak"), _d("Arguvan", "Arguvan"), _d("Kale", "Kale"),
        _d("Doğanyol", "Doganyol"),
    ]),
    # 45 MANİSA
    "manisa": ProvinceInfo(45, "Manisa", "Manisa", True, [
        _d("Yunusemre", "Yunusemre"), _d("Şehzadeler", "Sehzadeler"), _d("Akhisar", "Akhisar"),
        _d("Turgutlu", "Turgutlu"), _d("Salihli", "Salihli"), _d("Soma", "Soma"),
        _d("Alaşehir", "Alasehir"), _d("Saruhanlı", "Saruhanli"), _d("Kula", "Kula"),
        _d("Demirci", "Demirci"), _d("Kırkağaç", "Kirkagac"), _d("Sarıgöl", "Sarigol"),
        _d("Gördes", "Gordes"), _d("Selendi", "Selendi"), _d("Ahmetli", "Ahmetli"),
        _d("Gölmarmara", "Golmarmara"), _d("Köprübaşı", "Koprubasi"),
    ]),
    # 46 KAHRAMANMARAŞ
    "kahramanmaras": ProvinceInfo(46, "Kahramanmaraş", "Kahramanmaras", True, [
        _d("Onikişubat", "Onikisubat"), _d("Dulkadiroğlu", "Dulkadiroglu"), _d("Elbistan", "Elbistan"),
        _d("Afşin", "Afsin"), _d("Türkoğlu", "Turkoglu"), _d("Pazarcık", "Pazarcik"),
        _d("Göksun", "Goksun"), _d("Andırın", "Andirin"), _d("Çağlayancerit", "Caglayancerit"),
        _d("Nurhak", "Nurhak"), _d("Ekinözü", "Ekinozu"),
    ]),
    # 47 MARDİN
    "mardin": ProvinceInfo(47, "Mardin", "Mardin", True, [
        _d("Kızıltepe", "Kiziltepe"), _d("Artuklu", "Artuklu"), _d("Midyat", "Midyat"),
        _d("Nusaybin", "Nusaybin"), _d("Derik", "Derik"), _d("Mazıdağı", "Mazidagi"),
        _d("Dargeçit", "Dargecit"), _d("Savur", "Savur"), _d("Yeşilli", "Yesilli"),
        _d("Ömerli", "Omerli"),
    ]),
    # 48 MUĞLA (Tüm 13 İlçe)
    "mugla": ProvinceInfo(48, "Muğla", "Mugla", True, [
        _d("Bodrum", "Bodrum"), _d("Fethiye", "Fethiye"), _d("Milas", "Milas"),
        _d("Menteşe", "Mentese"), _d("Marmaris", "Marmaris"), _d("Seydikemer", "Seydikemer"),
        _d("Ortaca", "Ortaca"), _d("Yatağan", "Yatagan"), _d("Dalaman", "Dalaman"),
        _d("Köyceğiz", "Koycegiz"), _d("Ula", "Ula"), _d("Datça", "Datca"),
        _d("Kavaklıdere", "Kavaklidere"),
    ]),
    # 49 MUŞ
    "mus": ProvinceInfo(49, "Muş", "Mus", False, [
        _d("Merkez", "Merkez"), _d("Bulanık", "Bulanik"), _d("Malazgirt", "Malazgirt"),
        _d("Varto", "Varto"), _d("Hasköy", "Haskoy"), _d("Korkut", "Korkut"),
    ]),
    # 50 NEVŞEHİR
    "nevsehir": ProvinceInfo(50, "Nevşehir", "Nevsehir", False, [
        _d("Merkez", "Merkez"), _d("Ürgüp", "Urgup"), _d("Avanos", "Avanos"),
        _d("Gülşehir", "Gulsehir"), _d("Derinkuyu", "Derinkuyu"), _d("Acıgöl", "Acigol"),
        _d("Kozaklı", "Kozakli"), _d("Hacıbektaş", "Hacibektas"),
    ]),
    # 51 NİĞDE
    "nigde": ProvinceInfo(51, "Niğde", "Nigde", False, [
        _d("Merkez", "Merkez"), _d("Bor", "Bor"), _d("Çiftlik", "Ciftlik"),
        _d("Ulukışla", "Ulukisla"), _d("Altunhisar", "Altunhisar"), _d("Çamardı", "Camardi"),
    ]),
    # 52 ORDU
    "ordu": ProvinceInfo(52, "Ordu", "Ordu", True, [
        _d("Altınordu", "Altinordu"), _d("Ünye", "Unye"), _d("Fatsa", "Fatsa"),
        _d("Gölköy", "Golkoy"), _d("Perşembe", "Persembe"), _d("Kumru", "Kumru"),
        _d("Aybastı", "Aybasti"), _d("Korgan", "Korgan"), _d("Akkuş", "Akkus"),
        _d("Ulubey", "Ulubey"), _d("Mesudiye", "Mesudiye"), _d("İkizce", "Ikizce"),
        _d("Gürgentepe", "Gurgentepe"), _d("Çatalpınar", "Catalpinar"), _d("Çaybaşı", "Caybasi"),
        _d("Kabataş", "Kabatas"), _d("Kabadüz", "Kabaduz"), _d("Çamaş", "Camas"),
        _d("Gülyalı", "Gulyali"),
    ]),
    # 53 RİZE
    "rize": ProvinceInfo(53, "Rize", "Rize", False, [
        _d("Merkez", "Merkez"), _d("Çayeli", "Cayeli"), _d("Ardeşen", "Ardesen"),
        _d("Pazar", "Pazar"), _d("Fındıklı", "Findikli"), _d("Güneysu", "Guneysu"),
        _d("Kalkandere", "Kalkandere"), _d("İyidere", "Iyidere"), _d("Derepazarı", "Derepazari"),
        _d("Çamlıhemşin", "Camlihemsin"), _d("İkizdere", "Ikizdere"), _d("Hemşin", "Hemsin"),
    ]),
    # 54 SAKARYA
    "sakarya": ProvinceInfo(54, "Sakarya", "Sakarya", True, [
        _d("Adapazarı", "Adapazari"), _d("Serdivan", "Serdivan"), _d("Akyazı", "Akyazi"),
        _d("Erenler", "Erenler"), _d("Hendek", "Hendek"), _d("Karasu", "Karasu"),
        _d("Geyve", "Geyve"), _d("Arifiye", "Arifiye"), _d("Sapanca", "Sapanca"),
        _d("Pamukova", "Pamukova"), _d("Ferizli", "Ferizli"), _d("Kaynarca", "Kaynarca"),
        _d("Kocaali", "Kocaali"), _d("Söğütlü", "Sogutlu"), _d("Karapürçek", "Karapurcek"),
        _d("Taraklı", "Tarakli"),
    ]),
    # 55 SAMSUN
    "samsun": ProvinceInfo(55, "Samsun", "Samsun", True, [
        _d("İlkadım", "Ilkadim"), _d("Atakum", "Atakum"), _d("Bafra", "Bafra"),
        _d("Çarşamba", "Carsamba"), _d("Canik", "Canik"), _d("Vezirköprü", "Vezirkopru"),
        _d("Terme", "Terme"), _d("Tekkeköy", "Tekkekoy"), _d("Havza", "Havza"),
        _d("Alaçam", "Alacam"), _d("19 Mayıs", "19Mayis"), _d("Ayvacık", "Ayvacik"),
        _d("Kavak", "Kavak"), _d("Salıpazarı", "Salipazari"), _d("Asarcık", "Asarcik"),
        _d("Ladık", "Ladik"), _d("Yakakent", "Yakakent"),
    ]),
    # 56 SİİRT
    "siirt": ProvinceInfo(56, "Siirt", "Siirt", False, [
        _d("Merkez", "Merkez"), _d("Kurtalan", "Kurtalan"), _d("Pervari", "Pervari"),
        _d("Baykan", "Baykan"), _d("Şirvan", "Sirvan"), _d("Eruh", "Eruh"),
        _d("Tillo", "Tillo"),
    ]),
    # 57 SİNOP
    "sinop": ProvinceInfo(57, "Sinop", "Sinop", False, [
        _d("Merkez", "Merkez"), _d("Boyabat", "Boyabat"), _d("Gerze", "Gerze"),
        _d("Ayancık", "Ayancik"), _d("Durağan", "Duragan"), _d("Türkeli", "Turkeli"),
        _d("Erfelek", "Erfelek"), _d("Saraydüzü", "Sarayduzu"), _d("Dikmen", "Dikmen"),
    ]),
    # 58 SİVAS
    "sivas": ProvinceInfo(58, "Sivas", "Sivas", False, [
        _d("Merkez", "Merkez"), _d("Şarkışla", "Sarkisla"), _d("Yıldızeli", "Yildizeli"),
        _d("Suşehri", "Susehri"), _d("Gemerek", "Gemerek"), _d("Zara", "Zara"),
        _d("Kangal", "Kangal"), _d("Gürün", "Gurun"), _d("Divriği", "Divrigi"),
        _d("Koyulhisar", "Koyulhisar"), _d("Altınyayla", "Altinyayla"), _d("Hafik", "Hafik"),
        _d("Ulaş", "Ulas"), _d("İmranlı", "Imranli"), _d("Akıncılar", "Akincilar"),
        _d("Gölova", "Golova"), _d("Doğanşar", "Dogansar"),
    ]),
    # 59 TEKİRDAĞ
    "tekirdag": ProvinceInfo(59, "Tekirdağ", "Tekirdag", True, [
        _d("Çorlu", "Corlu"), _d("Süleymanpaşa", "Suleymanpasa"), _d("Çerkezköy", "Cerkezkoy"),
        _d("Kapaklı", "Kapakli"), _d("Ergene", "Ergene"), _d("Malkara", "Malkara"),
        _d("Saray", "Saray"), _d("Hayrabolu", "Hayrabolu"), _d("Şarköy", "Sarkoy"),
        _d("Muratlı", "Muratli"), _d("Marmaraereğlisi", "Marmaraereglisi"),
    ]),
    # 60 TOKAT
    "tokat": ProvinceInfo(60, "Tokat", "Tokat", False, [
        _d("Merkez", "Merkez"), _d("Erbaa", "Erbaa"), _d("Turhal", "Turhal"),
        _d("Niksar", "Niksar"), _d("Zile", "Zile"), _d("Reşadiye", "Resadiye"),
        _d("Almus", "Almus"), _d("Pazar", "Pazar"), _d("Yeşilyurt", "Yesilyurt"),
        _d("Artova", "Artova"), _d("Sulusaray", "Sulusaray"), _d("Başçiftlik", "Basciftlik"),
    ]),
    # 61 TRABZON
    "trabzon": ProvinceInfo(61, "Trabzon", "Trabzon", True, [
        _d("Ortahisar", "Ortahisar"), _d("Akçaabat", "Akcaabat"), _d("Araklı", "Arakli"),
        _d("Of", "Of"), _d("Yomra", "Yomra"), _d("Arsin", "Arsin"),
        _d("Vakfıkebir", "Vakfikebir"), _d("Sürmene", "Surmene"), _d("Maçka", "Macka"),
        _d("Beşikdüzü", "Besikduzu"), _d("Çarşıbaşı", "Carsibasi"), _d("Tonya", "Tonya"),
        _d("Düzköy", "Duzkoy"), _d("Çaykara", "Caykara"), _d("Şalpazarı", "Salpazari"),
        _d("Hayrat", "Hayrat"), _d("Köprübaşı", "Koprubasi"), _d("Dernekpazarı", "Dernekpazari"),
    ]),
    # 62 TUNCELİ
    "tunceli": ProvinceInfo(62, "Tunceli", "Tunceli", False, [
        _d("Merkez", "Merkez"), _d("Pertek", "Pertek"), _d("Mazgirt", "Mazgirt"),
        _d("Çemişgezek", "Cemisgezek"), _d("Hozat", "Hozat"), _d("Ovacık", "Ovacik"),
        _d("Pülümür", "Pulumur"), _d("Nazımiye", "Nazimiye"),
    ]),
    # 63 ŞANLIURFA
    "sanliurfa": ProvinceInfo(63, "Şanlıurfa", "Sanliurfa", True, [
        _d("Eyyübiye", "Eyyubiye"), _d("Haliliye", "Haliliye"), _d("Siverek", "Siverek"),
        _d("Viranşehir", "Viransehir"), _d("Karaköprü", "Karakopru"), _d("Akçakale", "Akcakale"),
        _d("Suruç", "Suruc"), _d("Birecik", "Birecik"), _d("Ceylanpınar", "Ceylanpinar"),
        _d("Harran", "Harran"), _d("Bozova", "Bozova"), _d("Hilvan", "Hilvan"),
        _d("Halfeti", "Halfeti"),
    ]),
    # 64 UŞAK
    "usak": ProvinceInfo(64, "Uşak", "Usak", False, [
        _d("Merkez", "Merkez"), _d("Banaz", "Banaz"), _d("Eşme", "Esme"),
        _d("Sivaslı", "Sivasli"), _d("Ulubey", "Ulubey"), _d("Karahallı", "Karahalli"),
    ]),
    # 65 VAN
    "van": ProvinceInfo(65, "Van", "Van", True, [
        _d("İpekyolu", "Ipekyolu"), _d("Erciş", "Ercis"), _d("Tuşba", "Tusba"),
        _d("Edremit", "Edremit"), _d("Özalp", "Ozalp"), _d("Çaldıran", "Caldiran"),
        _d("Başkale", "Baskale"), _d("Muradiye", "Muradiye"), _d("Gürpınar", "Gurpinar"),
        _d("Gevaş", "Gevas"), _d("Saray", "Saray"), _d("Çatak", "Catak"),
        _d("Bahçesaray", "Bahcesaray"),
    ]),
    # 66 YOZGAT
    "yozgat": ProvinceInfo(66, "Yozgat", "Yozgat", False, [
        _d("Merkez", "Merkez"), _d("Sorgun", "Sorgun"), _d("Akdağmadeni", "Akdagmadeni"),
        _d("Yerköy", "Yerkoy"), _d("Boğazlıyan", "Bogazliyan"), _d("Sarıkaya", "Sarikaya"),
        _d("Çekerek", "Cekerek"), _d("Şefaatli", "Sefaatli"), _d("Saraykent", "Saraykent"),
        _d("Çayıralan", "Cayiralan"), _d("Kadışehri", "Kadissehri"), _d("Aydıncık", "Aydincik"),
        _d("Yenifakılı", "Yenifakili"), _d("Çandır", "Candir"),
    ]),
    # 67 ZONGULDAK
    "zonguldak": ProvinceInfo(67, "Zonguldak", "Zonguldak", False, [
        _d("Ereğli", "Eregli"), _d("Merkez", "Merkez"), _d("Çaycuma", "Caycuma"),
        _d("Devrek", "Devrek"), _d("Kozlu", "Kozlu"), _d("Alaplı", "Alapli"),
        _d("Kilimli", "Kilimli"), _d("Gökçebey", "Gokcebey"),
    ]),
    # 68 AKSARAY
    "aksaray": ProvinceInfo(68, "Aksaray", "Aksaray", False, [
        _d("Merkez", "Merkez"), _d("Ortaköy", "Ortakoy"), _d("Eskil", "Eskil"),
        _d("Gülağaç", "Gulagac"), _d("Güzelyurt", "Guzelyurt"), _d("Ağaçören", "Agacoren"),
        _d("Sarıyahşi", "Sariyahsi"), _d("Sultanhanı", "Sultanhani"),
    ]),
    # 69 BAYBURT
    "bayburt": ProvinceInfo(69, "Bayburt", "Bayburt", False, [
        _d("Merkez", "Merkez"), _d("Demirözü", "Demirozu"), _d("Aydıntepe", "Aydintepe"),
    ]),
    # 70 KARAMAN
    "karaman": ProvinceInfo(70, "Karaman", "Karaman", False, [
        _d("Merkez", "Merkez"), _d("Ermenek", "Ermenek"), _d("Sarıveliler", "Sariveliler"),
        _d("Ayrancı", "Ayranci"), _d("Kazımkarabekir", "Kazimkarabekir"), _d("Başyayla", "Basyayla"),
    ]),
    # 71 KIRIKKALE
    "kirikkale": ProvinceInfo(71, "Kırıkkale", "Kirikkale", False, [
        _d("Merkez", "Merkez"), _d("Yahşihan", "Yahsihan"), _d("Keskin", "Keskin"),
        _d("Delice", "Delice"), _d("Sulakyurt", "Sulakyurt"), _d("Bahşılı", "Bahsili"),
        _d("Balışeyh", "Baliseyh"), _d("Karakeçili", "Karakecili"), _d("Çelebi", "Celebi"),
    ]),
    # 72 BATMAN
    "batman": ProvinceInfo(72, "Batman", "Batman", False, [
        _d("Merkez", "Merkez"), _d("Kozluk", "Kozluk"), _d("Sason", "Sason"),
        _d("Beşiri", "Besiri"), _d("Gercüş", "Gercus"), _d("Hasankeyf", "Hasankeyf"),
    ]),
    # 73 ŞIRNAK
    "sirnak": ProvinceInfo(73, "Şırnak", "Sirnak", False, [
        _d("Cizre", "Cizre"), _d("Silopi", "Silopi"), _d("Merkez", "Merkez"),
        _d("İdil", "Idil"), _d("Uludere", "Uludere"), _d("Beytüşşebap", "Beytussebap"),
        _d("Güçlükonak", "Guclukonak"),
    ]),
    # 74 BARTIN
    "bartin": ProvinceInfo(74, "Bartın", "Bartin", False, [
        _d("Merkez", "Merkez"), _d("Ulus", "Ulus"), _d("Amasra", "Amasra"),
        _d("Kurucaşile", "Kurucasile"),
    ]),
    # 75 ARDAHAN
    "ardahan": ProvinceInfo(75, "Ardahan", "Ardahan", False, [
        _d("Merkez", "Merkez"), _d("Göle", "Gole"), _d("Çıldır", "Cildir"),
        _d("Hanak", "Hanak"), _d("Posof", "Posof"), _d("Damal", "Damal"),
    ]),
    # 76 IĞDIR
    "igdir": ProvinceInfo(76, "Iğdır", "Igdir", False, [
        _d("Merkez", "Merkez"), _d("Tuzluca", "Tuzluca"), _d("Aralık", "Aralik"),
        _d("Karakoyunlu", "Karakoyunlu"),
    ]),
    # 77 YALOVA
    "yalova": ProvinceInfo(77, "Yalova", "Yalova", False, [
        _d("Merkez", "Merkez"), _d("Çiftlikköy", "Ciftlikkoy"), _d("Çınarcık", "Cinarcik"),
        _d("Altınova", "Altinova"), _d("Armutlu", "Armutlu"), _d("Termal", "Termal"),
    ]),
    # 78 KARABÜK
    "karabuk": ProvinceInfo(78, "Karabük", "Karabuk", False, [
        _d("Merkez", "Merkez"), _d("Safranbolu", "Safranbolu"), _d("Yenice", "Yenice"),
        _d("Eskipazar", "Eskipazar"), _d("Eflani", "Eflani"), _d("Ovacık", "Ovacik"),
    ]),
    # 79 KİLİS
    "kilis": ProvinceInfo(79, "Kilis", "Kilis", False, [
        _d("Merkez", "Merkez"), _d("Musabeyli", "Musabeyli"), _d("Elbeyli", "Elbeyli"),
        _d("Polateli", "Polateli"),
    ]),
    # 80 OSMANİYE
    "osmaniye": ProvinceInfo(80, "Osmaniye", "Osmaniye", False, [
        _d("Merkez", "Merkez"), _d("Kadirli", "Kadirli"), _d("Düziçi", "Duzici"),
        _d("Bahçe", "Bahce"), _d("Toprakkale", "Toprakkale"), _d("Sumbas", "Sumbas"),
        _d("Hasanbeyli", "Hasanbeyli"),
    ]),
    # 81 DÜZCE
    "duzce": ProvinceInfo(81, "Düzce", "Duzce", False, [
        _d("Merkez", "Merkez"), _d("Akçakoca", "Akcakoca"), _d("Kaynaşlı", "Kaynasli"),
        _d("Gölyaka", "Golyaka"), _d("Çilimli", "Cilimli"), _d("Yığılca", "Yigilca"),
        _d("Gümüşova", "Gumusova"), _d("Cumayeri", "Cumayeri"),
    ]),
}


def _normalize_turkish(text: str) -> str:
    t = text.lower().strip()
    replacements = {
        "ç": "c", "ğ": "g", "ı": "i", "i̇": "i", "ö": "o", "ş": "s", "ü": "u",
    }
    for k, v in replacements.items():
        t = t.replace(k, v)
    return t


def resolve_jurisdiction(location_query: str) -> tuple[str, Optional[str], Optional[str]]:
    """Kullanıcının yazdığı il, ilçe veya mahalle ifadesini Türkiye'nin 81 ili
    ve 973 ilçesi arasından hiyerarşik jurisdiction koduna (TR.Il.Ilce) çözümler.

    Dönüş: (jurisdiction_code, province_name, district_name)
    Örnekler:
      "Kadıköy Fikirtepe" -> ("TR.Istanbul.Kadikoy", "İstanbul", "Kadıköy")
      "Selçuklu Bosna Hersek" -> ("TR.Konya.Selcuklu", "Konya", "Selçuklu")
      "Bodrum Yalıkavak" -> ("TR.Mugla.Bodrum", "Muğla", "Bodrum")
      "Muratpaşa Lara" -> ("TR.Antalya.Muratpasa", "Antalya", "Muratpaşa")
      "İzmir Karşıyaka" -> ("TR.Izmir.Karsiyaka", "İzmir", "Karşıyaka")
      "Trabzon Akçaabat" -> ("TR.Trabzon.Akcaabat", "Trabzon", "Akçaabat")
    """
    raw_norm = _normalize_turkish(location_query)

    # 1. Önce ilçe isimlerini tara (spesifik eşleşme)
    for prov_key, prov in ALL_81_PROVINCES.items():
        for dist in prov.districts:
            # 'Merkez' ilçesi tek başına aranamaz, il adı ile aranır
            if dist.name == "Merkez":
                continue
            dist_norm = _normalize_turkish(dist.name)
            if re.search(rf"\b{dist_norm}\b", raw_norm):
                return (f"TR.{prov.code}.{dist.code}", prov.name, dist.name)

    # 2. İl isimlerini tara
    for prov_key, prov in ALL_81_PROVINCES.items():
        prov_norm = _normalize_turkish(prov.name)
        if re.search(rf"\b{prov_norm}\b", raw_norm):
            return (f"TR.{prov.code}", prov.name, None)

    return ("TR", None, None)
