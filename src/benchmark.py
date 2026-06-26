import os
import sys
import logging
import pandas as pd

# Eğer yfinance kurulu değilse hata yutulsun, main.py çökmesin.
try:
    import yfinance as yf
except ImportError:
    yf = None

logger = logging.getLogger(__name__)

def fetch_and_calculate_benchmark(start_date="2025-12-31"):
    """
    TUR ETF, BIST 100 (TRY) ve USD/TRY verilerini çeker, 
    BIST 100'ü dolara çevirir ve karşılaştırmalı kümülatif getiri tablosu üretir.
    """
    if yf is None:
        logger.error("yfinance kütüphanesi kurulu değil. Lütfen 'pip install yfinance' çalıştırın.")
        return None

    logger.info(f"Yahoo Finance üzerinden benchmark verileri çekiliyor (Başlangıç: {start_date})...")
    
    # 1. Verileri İndir (TUR ETF, BIST 100, USDTRY)
    tickers = ["TUR", "XU100.IS", "TRY=X"]
    
    try:
        # data indirme (sadece Close fiyatları yeterli)
        df = yf.download(tickers, start=start_date, progress=False)["Close"]
    except Exception as e:
        logger.error(f"Yahoo Finance'ten veri çekerken hata: {e}")
        return None

    if df is None or df.empty:
        logger.error("Yahoo Finance veri döndürmedi.")
        return None
        
    # Sütun isimlerini güvene al (MultiIndex vs olabilir)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(1)  # Ticker isimlerini al
        
    # Eksik sütun var mı kontrolü
    for t in tickers:
        if t not in df.columns:
            logger.error(f"{t} verisi bulunamadı.")
            return None

    # İleriye/Geriye dönük doldurma (Tatiller vs nedeniyle verilerin tam oturması için)
    df = df.ffill().dropna()
    
    if df.empty:
        return None

    # 2. Dolar Bazlı BIST 100 Hesaplama
    # BIST 100 (TRY) / USDTRY = BIST 100 (USD)
    df["BIST100_USD"] = df["XU100.IS"] / df["TRY=X"]
    
    # 3. Kümülatif Getiri (Yüzde) Hesaplama
    # İlk gün kapanış fiyatlarını taban (base) olarak alalım
    base_tur = df["TUR"].iloc[0]
    base_bist = df["BIST100_USD"].iloc[0]
    
    df["TUR_Return"] = (df["TUR"] / base_tur) - 1.0
    df["BIST_Return"] = (df["BIST100_USD"] / base_bist) - 1.0
    
    # Alfa = TUR Getirisi - BIST 100 (USD) Getirisi
    df["Alpha"] = df["TUR_Return"] - df["BIST_Return"]
    
    # Sadece ihtiyacımız olan kısımları tut
    result_df = df[["TUR", "XU100.IS", "TRY=X", "BIST100_USD", "TUR_Return", "BIST_Return", "Alpha"]].copy()
    
    # Index (Tarihler) temiz bir string'e dönüştür
    result_df.index = result_df.index.strftime('%Y-%m-%d')
    result_df = result_df.reset_index()
    result_df.rename(columns={"index": "Date", "Date": "Date"}, inplace=True)
    
    return result_df

def run_benchmark_and_write(writer):
    """Benchmark verisini çeker ve Google Sheets'e yazar."""
    df = fetch_and_calculate_benchmark("2025-12-31")
    if df is not None and not df.empty:
        writer.write_benchmark_comparison(df)
        logger.info("✅ BIST100 vs TUR Karşılaştırması başarıyla tamamlandı.")
    else:
        logger.warning("Benchmark verisi hesaplanamadı.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from sheets_writer import SheetsWriter
    from dotenv import load_dotenv
    load_dotenv()
    
    sheets_id = os.getenv("GOOGLE_SHEETS_ID", "1tg5OBvX_ohCrxdiz_2JvtQxTPKmE-hNW27C2WGxH7n0")
    service_account = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")
    
    writer = SheetsWriter(sheets_id, service_account)
    if writer.connect():
        writer.setup_sheets()
        run_benchmark_and_write(writer)
