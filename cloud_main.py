import os
import sys
import logging
import json
from datetime import date, datetime
from pathlib import Path
import pandas as pd

# Cloud ortamında src klasörüne erişim sağlamak için
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fetcher import fetch_holdings, get_latest_trading_date
from analyzer import compare_snapshots
from sheets_writer import SheetsWriter

logger = logging.getLogger("cloud_function")
logging.basicConfig(level=logging.INFO)

def run_cloud_analysis(request):
    """Google Cloud Functions giriş noktası (HTTP Trigger)."""
    
    # 1. Ortam değişkenlerinden yapılandırmayı al
    sheets_id = os.environ.get("GOOGLE_SHEETS_ID")
    service_account_json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if not sheets_id or not service_account_json_str:
        logger.error("Eksik ortam degiskeni: GOOGLE_SHEETS_ID veya GOOGLE_SERVICE_ACCOUNT_JSON")
        return ("Eksik ortam degiskeni yapilandirmasi", 500)
    
    # JSON metnini gecici dosyaya yaz (gspread from_service_account_file kullandigi icin)
    sa_file = "/tmp/service_account.json"
    try:
        with open(sa_file, "w", encoding="utf-8") as f:
            f.write(service_account_json_str)
    except Exception as e:
        logger.error(f"Service account dosyasi yazilamadi: {e}")
        return ("Kimlik dosyasi olusturulamadi", 500)
        
    writer = SheetsWriter(sheets_id, sa_file)
    if not writer.connect():
        logger.error("Google Sheets baglantisi basarisiz.")
        return ("Google Sheets baglantisi basarisiz", 500)
        
    target_date = get_latest_trading_date()
    logger.info(f"Cloud Tetiklendi. Hedef tarih: {target_date}")
    
    # 2. Güncel veriyi çek (/tmp dizinini kullan, cloud function sadece buraya yazabilir)
    tmp_snapshot_dir = "/tmp/snapshots"
    curr_df = fetch_holdings(target_date, tmp_snapshot_dir)
    
    if curr_df is None or curr_df.empty:
        msg = f"{target_date} icin veri alinamadi. API veya piyasa kapali."
        logger.warning(msg)
        return (msg, 200)
        
    # 3. Google Sheets'ten dünün verisini oku (Stateless Yapi)
    prev_df, prev_date = read_previous_portfolio(writer)
    
    if prev_df is None or prev_df.empty:
        logger.warning("Google Sheets'ten onceki veri okunamadi (ilk calistirma olabilir).")
        writer.setup_sheets()
        writer.write_current_portfolio(curr_df, None)
        writer.append_raw_data(curr_df)
        return ("Ilk veri seti Google Sheets'e islendi.", 200)
        
    if prev_date >= target_date:
        msg = f"Hedef tarih ({target_date}) onceki kaydedilen tarihten ({prev_date}) yeni degil. islem atlandi."
        logger.info(msg)
        return (msg, 200)
        
    # 4. Karsilastirma yap
    logger.info(f"Karsilastirma yapiliyor: {prev_date} -> {target_date}")
    analysis = compare_snapshots(prev_df, curr_df, prev_date, target_date)
    
    if analysis is None:
        logger.error("Analiz basarisiz oldu")
        return ("Analiz basarisiz", 500)
        
    # 5. Degisiklik varsa Google Sheets'e yaz (Akilli Kontrol)
    if analysis.has_changes:
        logger.info("Degisiklikler tespit edildi, Google Sheets guncelleniyor...")
        writer.setup_sheets()
        writer.write_all(curr_df, analysis.to_dict(), target_date, prev_date)
        msg = f"Basarili: {target_date} analiz edildi ve degisimler Sheets'e yazildi."
        logger.info(msg)
    else:
        msg = "Basarili: Analiz yapildi ancak agirlik bazinda hicbir degisim (has_changes=False) tespit edilmedi. Sheets guncellenmedi."
        logger.info(msg)
        
    return (msg, 200)

def read_previous_portfolio(writer) -> tuple[pd.DataFrame, date]:
    """Google Sheets üzerinden son portföy durumunu okur."""
    ws = writer._get_sheet("current")
    if ws is None:
        return None, None
        
    try:
        records = ws.get_all_records()
        if not records:
            return None, None
            
        df = pd.DataFrame(records)
        col_map = {
            "Tiker": "ticker",
            "Şirket Adı": "name",
            "Sektör": "sector",
            "Ağırlık (%)": "weight_pct",
            "Piyasa Değeri (USD)": "market_value",
            "Adet": "quantity",
            "Fiyat (USD)": "price",
            "Tarih": "date_str"
        }
        df = df.rename(columns=col_map)
        
        def parse_pct(x):
            if isinstance(x, str):
                if '%' in x:
                    return float(x.replace('%', '').replace(',', '')) / 100.0
                return float(x.replace(',', ''))
            return float(x) if pd.notnull(x) else 0.0
            
        def parse_num(x):
            if isinstance(x, str):
                return float(x.replace(',', '').replace('$', ''))
            return float(x) if pd.notnull(x) else 0.0
            
        df["weight_pct"] = df["weight_pct"].apply(parse_pct)
        df["market_value"] = df["market_value"].apply(parse_num)
        df["quantity"] = df["quantity"].apply(parse_num)
        df["price"] = df["price"].apply(parse_num)
        
        date_str = df.iloc[0]["date_str"]
        try:
            prev_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except:
            prev_date = date.today()
            
        needed = ["ticker", "name", "sector", "weight_pct", "market_value", "quantity", "price"]
        for n in needed:
            if n not in df.columns:
                df[n] = 0.0 if n in ["weight_pct", "market_value", "quantity", "price"] else ""
                
        return df[needed], prev_date
    except Exception as e:
        logger.error(f"Sheets'ten okuma hatasi: {e}")
        return None, None
