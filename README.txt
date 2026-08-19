MİM MEVZUAT
=============
Türkiye'de mimari proje üretiminde ihtiyaç duyulan mevzuat, yönetmelik,
plan notu ve teknik düzenlemeleri tek yerde toplayan; doğal dilde soru
sorulabilen; yalnızca doğrulanmış kaynaklara dayanarak cevap veren ve
mimari yorum/hesaplama yapabilen mimarlık mevzuat asistanı.

Değer önermesi:
  "AI mevzuatı biliyor" DEĞİL — "AI hangi resmi hükme baktığını
  biliyor, bunu gösteriyor, hesaplıyor, yorumluyor ve bilmiyorsa uydurmuyor."

ÇALIŞTIRMA VE DAĞITIM SEÇENEKLERİ
------------------------------------

1. TEK TIKLA ÇALIŞAN MASAÜSTÜ UYGULAMASI (.EXE):
   - `dist/MimMevzuat.exe` dosyasına çift tıklayın.
   - Python kurulumu veya terminal gerekmez!
   - Otomatik olarak tarayıcınızda açılır ve %100 çevrimdışı çalışır.
   - Yeniden derlemek için: `python build_exe.py`

2. WEB UYGULAMASI (LOKAL & BULUT):
   - python -m mim_mevzuat.cli serve
   - Tarayıcıda açın: http://127.0.0.1:8000
   - Bulut Dağıtımı: Render.com (`render.yaml`) veya Fly.io (`fly.toml`) / Dockerfile ile anında canlıya alınabilir.

3. KOMUT SATIRI (CLI):
   - python -m mim_mevzuat.cli trace "Çankaya'da 40 dairelik konut projesi yapıyorum, 30 araçlık otopark ayırdım kurtarır mı?"
   - python -m mim_mevzuat.cli trace "1500 m2 arsam var emsal 1.50, toplam inşaat alanım 2500 m2 oldu emsali aşıyor muyum?"

4. TESTLER:
   - pytest -v (42 birim, entegrasyon, NLU, kural ve web testi)

DURUM:
- Faz 1 (Çekirdek Prototip + Web UI) -> Tamamlandı
- Faz 2 (Rule Engine + NLU + Mimari Yorumlayıcı + .EXE Çıktısı) -> Tamamlandı
- 81 İl ve İlçe Çözümleme + Update Engine -> Aktif
