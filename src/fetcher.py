"""
fetcher.py — BlackRock API'den TUR ETF holdings verisi ceker
"""

import os
import io
import logging
import requests
import pandas as pd
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BLACKROCK_API_URL = (
    "https://www.blackrock.com/varnish-api/blk-one01-product-data"
    "/product-data/api/v1/get-fund-document"
)

DEFAULT_PARAMS = {
    "appType": "PRODUCT_PAGE",
    "appSubType": "ISHARES",
    "targetSite": "us-ishares",
    "locale": "en_US",
    "portfolioId": "239689",
    "userType": "individual",
    "component": "holdings",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.ishares.com/",
}


def get_all_available_trading_dates() -> list[date]:
    """
    iShares ürün sayfasını (HTML) tarayarak açılır menüde (As of Dates) yer alan 
    tüm geçerli tarihleri (YYYYMMDD) tespit eder ve liste olarak döner.
    """
    url = "https://www.ishares.com/us/products/239689/ishares-msci-turkey-etf"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.ok:
            # HTML içindeki 2024, 2025, 2026 ile başlayan 8 haneli YYYYMMDD stringlerini bul
            dates_str = set(re.findall(r'202[456]\d{4}', resp.text))
            
            valid_dates = []
            for d in dates_str:
                if len(d) == 8:
                    try:
                        valid_dates.append(datetime.strptime(d, "%Y%m%d").date())
                    except ValueError:
                        pass
                        
            # En yeniden en eskiye doğru sırala
            valid_dates.sort(reverse=True)
            if valid_dates:
                return valid_dates
    except Exception as e:
        logger.error(f"Tarih listesi okuma hatasi: {e}")
        
    # Eger siteye ulasilamazsa veya hata olursa bos liste don
    return []

def get_latest_trading_date() -> date:
    """
    BlackRock API'sinde mevcut en son is gunu tarihini bulur.
    Sayfadan okunan tarihler arasindan en yenisini secer.
    """
    available = get_all_available_trading_dates()
    if available:
        logger.debug(f"Sayfadan okunan en son gecerli tarih: {available[0]}")
        return available[0]
        
    # Fallback: Eger liste okunamadiysa eski metodla (1 gun onceki is gunu) devam et
    today = date.today()
    candidate = today - timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate


def fetch_holdings(as_of_date: Optional[date] = None, snapshot_dir: str = "data/snapshots") -> Optional[pd.DataFrame]:
    """
    BlackRock API'den belirtilen tarihin holdings verisini ceker.

    Args:
        as_of_date: Veri tarihi. None ise en son gecerli tarih kullanilir.
        snapshot_dir: CSV'nin kaydedilecegi dizin.

    Returns:
        Holdings DataFrame veya None (hata durumunda)
    """
    if as_of_date is None:
        as_of_date = get_latest_trading_date()

    date_str = as_of_date.strftime("%Y%m%d")
    display_date = as_of_date.strftime("%d %B %Y")

    snapshot_path = Path(snapshot_dir) / f"{date_str}.csv"

    # Eger bu gunun snapshot'i zaten varsa, tekrar cekme
    if snapshot_path.exists():
        logger.info(f"Snapshot zaten mevcut: {snapshot_path}")
        return load_snapshot(snapshot_path)

    logger.info(f"Holdings verisi cekiliyor: {display_date}...")

    params = {**DEFAULT_PARAMS, "asOfDate": date_str}

    try:
        response = requests.get(
            BLACKROCK_API_URL,
            params=params,
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()

        raw_text = response.text

        # API bazen bos veri veya hata doner
        if not raw_text or "iShares MSCI Turkey ETF" not in raw_text:
            logger.warning(f"{display_date} icin gecerli veri bulunamadi (piyasa kapali veya veri yok)")
            return None

        df = _parse_csv_response(raw_text, as_of_date)

        if df is None or df.empty:
            logger.warning(f"{display_date} icin parse edilecek veri yok")
            return None

        # Snapshot'i kaydet
        Path(snapshot_dir).mkdir(parents=True, exist_ok=True)
        df.to_csv(snapshot_path, index=False, encoding="utf-8-sig")
        logger.info(f"Kaydedildi: {len(df)} hisse -> {snapshot_path}")

        return df

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Hatasi {display_date}: {e}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Baglanti hatasi. Internet baglantinizi kontrol edin.")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Zaman asimi: {display_date}")
        return None
    except Exception as e:
        logger.error(f"Beklenmeyen hata {display_date}: {e}")
        return None


def _parse_csv_response(raw_text: str, as_of_date: date) -> Optional[pd.DataFrame]:
    """
    BlackRock API'nin CSV yanitini parse eder.

    BlackRock CSV'si ilk birkac satirda metadata icerir:
    - Satir 1: Fund Holdings as of, "Jun 24, 2026"
    - Satir 2-5: Inception Date, Shares Outstanding vb.
    - Satir 6: Bos
    - Satir 7: Baslik satiri (Ticker, Name, ...)
    - Satir 8+: Veri satirlari
    """
    lines = raw_text.strip().split("\n")

    # Baslik satirini bul (Ticker ile baslayan)
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('"Ticker"') or line.strip().startswith('Ticker'):
            header_idx = i
            break

    if header_idx is None:
        logger.error("CSV baslik satiri bulunamadi")
        return None

    # Baslik ve veri satirlarini al
    data_lines = lines[header_idx:]

    # Bos satirlari ve yasal uyarilari kaldir
    clean_lines = []
    for line in data_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('"The content') or stripped.startswith('The content'):
            break
        clean_lines.append(line)

    if len(clean_lines) < 2:
        return None

    csv_text = "\n".join(clean_lines)

    try:
        df = pd.read_csv(io.StringIO(csv_text))
        df.columns = df.columns.str.strip().str.replace('"', '')

        # Sutun isimlerini normalize et
        column_map = {
            "Ticker": "ticker",
            "Name": "name",
            "Sector": "sector",
            "Asset Class": "asset_class",
            "Market Value": "market_value",
            "Weight (%)": "weight_pct",
            "Notional Value": "notional_value",
            "Quantity": "quantity",
            "Price": "price",
            "Location": "location",
            "Exchange": "exchange",
            "Currency": "currency",
            "FX Rate": "fx_rate",
            "Market Currency": "market_currency",
            "Accrual Date": "accrual_date",
        }
        df = df.rename(columns=column_map)

        # Tarihi ekle
        df["as_of_date"] = as_of_date.strftime("%Y-%m-%d")

        # Sayisal sutunlari temizle (virgulleri kaldir)
        numeric_cols = ["market_value", "weight_pct", "notional_value", "quantity", "price", "fx_rate"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(",", "")
                    .str.replace('"', "")
                    .str.strip()
                )
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Sadece Equity (hisse senedi) satirlarini al
        equity_df = df[df["asset_class"] == "Equity"].copy()

        # Gecersiz/sifir agirlikli satirlari filtrele
        equity_df = equity_df[equity_df["weight_pct"] > 0].copy()

        # Ticker'i temizle
        equity_df["ticker"] = equity_df["ticker"].str.strip().str.replace('"', '')

        # Agirliga gore sirala
        equity_df = equity_df.sort_values("weight_pct", ascending=False).reset_index(drop=True)

        return equity_df

    except Exception as e:
        logger.error(f"CSV parse hatasi: {e}")
        return None


def load_snapshot(path) -> Optional[pd.DataFrame]:
    """Kaydedilmis bir snapshot'i yukler."""
    try:
        df = pd.read_csv(path)
        logger.debug(f"Snapshot yuklendi: {path} ({len(df)} satir)")
        return df
    except Exception as e:
        logger.error(f"Snapshot yukleme hatasi {path}: {e}")
        return None


def get_available_snapshots(snapshot_dir: str = "data/snapshots") -> list:
    """Mevcut tum snapshot tarihlerini listeler."""
    snap_path = Path(snapshot_dir)
    if not snap_path.exists():
        return []

    dates = []
    for f in sorted(snap_path.glob("*.csv")):
        try:
            d = datetime.strptime(f.stem, "%Y%m%d").date()
            dates.append(d)
        except ValueError:
            pass
    return sorted(dates)


def backfill_snapshots(days: int = 90, snapshot_dir: str = "data/snapshots") -> dict:
    """
    Sayfadan cekilen kesin gecerli tarihler listesini kullanarak,
    istenilen 'days' adedi kadar geriye donuk veri ceker.
    
    Returns:
        {"success": [...dates...], "failed": [...dates...], "skipped": [...]}
    """
    results = {"success": [], "failed": [], "skipped": []}
    
    available_dates = get_all_available_trading_dates()
    
    if not available_dates:
        logger.error("Gecerli tarihler sayfasindan okunamadi. Backfill yapilamiyor.")
        return results

    logger.info(f"iShares sayfasindan kesin is gunu takvimi alindi. (Toplam {len(available_dates)} gunluk arsiv)")
    logger.info(f"Bu listeden en son {days} adet tarih icin geriye donuk veri cekiliyor...")

    # Parametrede belirtilen N gun kadar al (ya da mevcut olanlarin hepsi)
    target_dates = available_dates[:days]

    for current in target_dates:
        snapshot_path = Path(snapshot_dir) / f"{current.strftime('%Y%m%d')}.csv"

        if snapshot_path.exists():
            results["skipped"].append(current)
            logger.debug(f"Zaten mevcut, atlandi: {current}")
        else:
            df = fetch_holdings(current, snapshot_dir)
            if df is not None and not df.empty:
                results["success"].append(current)
            else:
                results["failed"].append(current)

    logger.info(
        f"Backfill tamamlandi: "
        f"{len(results['success'])} basarili, "
        f"{len(results['failed'])} basarisiz, "
        f"{len(results['skipped'])} atlandi"
    )
    return results
