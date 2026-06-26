# TUR ETF Portfoy Takip Sistemi

iShares MSCI Turkey ETF (TUR) portfoy degisikliklerini gunluk olarak takip eden,
onceki gun ile karsilastirma yapan ve sonuclari Google Sheets'e yazan otomatik sistem.

---

## Ozellikler

- BlackRock API'den gunluk portfoy verisi cekilmesi
- Bir onceki is gunuyle agirlik karsilastirmasi
- Yeni giren / cikan hisse tespiti
- Sektor bazli analiz
- 8 farkli sekmeli Google Sheets entegrasyonu
- Windows Task Scheduler ile gunluk otomatik calistirma
- Geriye donuk (backfill) veri destegi

---

## Kurulum

### 1. Python Bagimliliklarini Yukle

```bash
pip install -r requirements.txt
```

### 2. Google Sheets Baglantisini Kur

```bash
python setup_google_sheets.py
```

Bu sihirbaz size adim adim rehberlik eder:
- Google Cloud'da service account olusturma
- API izinleri aktiflestirilmesi
- Spreadsheet'e erisim verilmesi
- Sekme yapisinin olusturulmasi

### 3. Geecmis Veri Yukle (90 Gunluk Backfill)

```bash
python main.py --backfill
```

### 4. Windows Task Scheduler Kur (Gunluk 09:00 Otomatik Calistirma)

```bash
python setup_task_scheduler.py
```

---

## Kullanim

```bash
# En son gecerli is gunu verisini cek ve analiz et
python main.py

# Belirli bir tarih icin
python main.py --date 20260624

# Son 30 gunu backfill
python main.py --backfill --days 30

# Google Sheets'e yazmadan sadece yerel analiz
python main.py --no-sheets

# Task Scheduler gorevini kaldir
python setup_task_scheduler.py --remove
```

---

## Google Sheets Yapisi

| Sekme | Aciklama |
|-------|----------|
| Guncel Portfoy | Her gun yenilenen mevcut holdings listesi |
| Degisim Gecmisi | Her gunun ozet karsilastirma satiri |
| Pozisyon Artislari | Agirlik artan tum hisseler (kumulatif) |
| Pozisyon Dususleri | Agirlik azalan tum hisseler (kumulatif) |
| Yeni Girenler | ETF'e yeni eklenen hisseler |
| Cikanlar | ETF'den cikarilan hisseler |
| Ham Veri | Tum tarihsel raw data |
| Sektor Analizi | Sektor bazli agirlik degisimleri |

---

## Proje Yapisi

```
TUR-analiz/
├── main.py                    # Ana giris noktasi
├── setup_google_sheets.py     # Google Sheets kurulum sihirbazi
├── setup_task_scheduler.py    # Windows Task Scheduler kurulumu
├── requirements.txt           # Python bagimliliklari
├── .env                       # Konfigurasyonlar (gizli)
├── src/
│   ├── fetcher.py             # BlackRock API veri cekilmesi
│   ├── analyzer.py            # Portfoy degisiklik analizi
│   ├── sheets_writer.py       # Google Sheets yazicisi
│   └── logger.py              # Loglama yapisi
├── data/
│   ├── snapshots/             # Gunluk CSV snapshot'lar (YYYYMMDD.csv)
│   └── changes/               # Gunluk degisim JSON raporlari
├── credentials/               # Service account JSON (gizli, git'e eklenmez)
└── logs/                      # Gunluk log dosyalari
```

---

## Google Sheets Baglantisi Olmadan Test

Service account kurulmadan once sistemin calisip calismdigini dogrulamak icin:

```bash
python main.py --no-sheets
```

Snapshot'lar `data/snapshots/` dizinine kaydedilir, degisim raporlari `data/changes/` dizinine JSON olarak yazilir.

---

## Kaynak

- ETF Sayfasi: https://www.ishares.com/us/products/239689/ishares-msci-turkey-etf
- BlackRock API: asOfDate parametresi ile YYYYMMDD formatinda tarih girin
- Google Sheets Tablosu: https://docs.google.com/spreadsheets/d/1tg5OBvX_ohCrxdiz_2JvtQxTPKmE-hNW27C2WGxH7n0
