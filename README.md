# 📈 TUR ETF Algoritmik Portföy Takip & Alpha Analiz Sistemi

Bu proje, BlackRock (iShares) **MSCI Turkey ETF (TUR)** fonunun günlük portföy değişikliklerini analiz eden, BIST 100 endeksine karşı "Alpha" (ekstra getiri) stratejileri üreten ve sonuçları otomatik olarak **Google Sheets** tablosuna aktaran gelişmiş bir finansal veri analiz sistemidir.

🌟 **Canlı Takip Tablosu:** [Google Sheets - TUR ETF Portföy Analizi](https://docs.google.com/spreadsheets/d/1tg5OBvX_ohCrxdiz_2JvtQxTPKmE-hNW27C2WGxH7n0/edit)

---

## 🚀 Projenin Amacı ve Felsefesi

TUR ETF, Türkiye piyasasına yatırım yapan 350 Milyon Doların üzerinde devasa bir yabancı fondur. Ancak fon, ağırlıklı olarak "Market-Cap" (Büyüklük) odaklı olduğu için getiri olarak genellikle BIST100'ü birebir taklit eder. 

**Peki BIST100'ü nasıl yenebiliriz?**
Bu proje, devasa BlackRock fonunun "Hantallığını" kopyalamak yerine, **"Hareketlerini ve Kararlarını"** kopyalamak için geliştirilmiştir:
1. **Kurumsal Kuluçka:** Yabancı fonun portföye yepyeni eklediği (yeni kan) hisseleri anında tespit edip trendin ilk adımlarını yakalar.
2. **Dip Avcılığı:** Fiyat düştükçe fonun "inatla" lot miktarını artırdığı (Negatif Korelasyon) hisseleri tespit eder.
3. **Erken Kaçış:** BIST 100 yatırımcılarının inatla tuttuğu hisselerde, yabancı fonun sessiz sedasız "Gerçek Satış" yaptığı şirketleri göstererek zararı erken kesmemizi sağlar.

---

## 📊 Google Sheets Analiz Sekmeleri

Sistem verileri analiz edip şu anda aktif olan **13 farklı analitik sekmeye** basar:

| Sekme | Açıklama |
|-------|----------|
| **📖 Kılavuz** | Sistemin nasıl çalıştığını ve tabloların nasıl okunması gerektiğini anlatan rehber. |
| **💡 Yatırım Stratejisi** | BIST100'ü yenmek için kullanabileceğiniz 4 ayaklı Alpha stratejisi (Kuluçka, Negatif Korelasyon vb.) |
| **📊 Güncel Portföy** | Fonun 70 hisselik anlık portföyü, günlük/kümülatif ağırlık değişimleri, renkli AL/SAT uyarıları ve *trend grafikleri*. |
| **📉 Korelasyon Analizi** | Hisse fiyat değişimleri ile fonun alış/satış reaksiyonlarını hesaplayıp doğrudan **AL/SAT/TUT** aksiyon önerileri sunar. |
| **🎯 Gelişmiş Sinyaller** | Günlük fon akışı ve "Anormal" lot değişimlerini tespit edip alarm üreten Quant Radarı. |
| **🤖 Yapay Zeka Özeti** | Son 24 saatte olan her şeyi metin tabanlı olarak (Sadece fiyatla artanlar, Gerçekten satılanlar vb.) insan dilinde özetler. |
| **⚖️ BIST100 vs TUR** | Fonun Amerikan Doları (USD) bazındaki tarihsel performansı ile XU100'ün USD bazlı getirisini karşılaştıran görsel grafikler. |
| **⏳ Pozisyon Getirileri** | Bir hisse fona ilk girdiği günden çıktığı güne kadar fonun o hisseden tam olarak yüzde kaç kâr/zarar ettiğini hesaplar. |
| **📈 / 📉 Pozisyon Artışları** | Ağırlığı artırılan veya azaltılan hisselerin geçmişten bugüne anlık bildirimleri. |
| **🏭 Sektör Trendleri** | Fonun bankacılık, sanayi vb. hangi sektörlere para kaydırdığını takip eden Matris. |

---

## ⚙️ Kurulum ve Otomasyon

Projeyi yerel makinenizde çalıştırmak ve günlük otomatik olarak güncellemek için:

### 1. Gereksinimleri Yükleyin
```bash
pip install -r requirements.txt
```

### 2. Google Sheets Bağlantısını Kurun
Bu sihirbaz, Google Cloud üzerinde bir service account açıp tablonuza yetki vermenizi sağlar.
```bash
python setup_google_sheets.py
```

### 3. Otomatik Görev Zamanlayıcı (Task Scheduler)
Windows Görev Zamanlayıcı'ya (Task Scheduler) komut ekleyerek sistemin her iş günü API'den verileri otomatik çekip bulut tablosunu güncellemesini sağlar.
```bash
python setup_task_scheduler.py
```

### 4. Manuel Kullanım
```bash
# Sadece bugünkü verileri analiz et ve Sheets'e yaz
python main.py

# Belirli bir tarihin verisini çek
python main.py --date 20260624

# Geçmiş 90 günlük verileri çek ve tüm matrisi baştan yarat (Backfill)
python main.py --backfill --days 90
```

---

## 🏗️ Mimari Yapı

- `main.py` : Sistemin orkestrasyonu.
- `src/fetcher.py` : BlackRock API'den tarihsel veri (.csv) indirilmesi.
- `src/analyzer.py` : Pandas kullanılarak ağırlık, lot farkları, getiriler ve korelasyonların hesaplanması.
- `src/sheets_writer.py` : Hazırlanan devasa analizlerin Google Sheets API (gspread) kullanılarak biçimlendirmelerle beraber buluta yazılması.
- `data/` : İndirilen günlük raw CSV dosyaları ve değişim algoritmalarının JSON formatında tutulduğu depo.

---
*Geliştirici: [kgulle](https://github.com/kgulle)*
