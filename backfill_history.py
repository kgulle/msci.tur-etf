import os
import time
import logging
from datetime import date, timedelta
from src.fetcher import fetch_holdings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("backfill")

def run_backfill(start_date: date, end_date: date):
    logger.info(f"🚀 Geriye donuk veri indirme basliyor: {start_date} -> {end_date}")
    
    current_date = start_date
    success_count = 0
    fail_count = 0
    
    while current_date <= end_date:
        # Hafta sonlarini atla
        if current_date.weekday() < 5:
            date_str = current_date.strftime("%Y%m%d")
            snapshot_path = f"data/snapshots/{date_str}.csv"
            
            if os.path.exists(snapshot_path):
                logger.info(f"⏭️ {current_date} zaten mevcut, atlanıyor.")
                success_count += 1
            else:
                logger.info(f"⬇️ Indiriliyor: {current_date}")
                try:
                    df = fetch_holdings(current_date, snapshot_dir="data/snapshots")
                    if df is not None:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    logger.error(f"Hata {current_date}: {e}")
                    fail_count += 1
                
                # BlackRock API limitlerine takilmamak icin bekle
                time.sleep(1.5)
                
        current_date += timedelta(days=1)
        
    logger.info(f"✅ Geriye donuk islem tamamlandi. Basarili: {success_count}, Basarisiz/Tatil: {fail_count}")

if __name__ == "__main__":
    start = date(2025, 12, 31)
    # Bugunden bir onceki gune kadar cekelim (bugun henuz kapanmamis olabilir)
    end = date.today() - timedelta(days=1)
    run_backfill(start, end)
