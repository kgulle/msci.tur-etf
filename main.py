"""
main.py — TUR ETF Portfoy Takip Sistemi — Ana Giris Noktasi

Kullanim:
  python main.py                     # En son gecerli tarih icin calistir
  python main.py --date 20260624     # Belirli bir tarih icin
  python main.py --backfill          # Son 90 gunu geriye donuk doldur
  python main.py --backfill --days 30  # Son 30 gunu geriye donuk doldur
  python main.py --no-sheets         # Sheets'e yazmadan sadece analiz et
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import date, datetime, timedelta

# Proje kok dizinini Python path'e ekle
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from logger import setup_logger
from fetcher import fetch_holdings, get_available_snapshots, load_snapshot, backfill_snapshots, get_latest_trading_date
from analyzer import compare_snapshots, build_historical_weight_matrix

# .env yukle
load_dotenv()


def get_config() -> dict:
    """Ortam degiskenlerinden konfigurasyonu yukler."""
    return {
        "sheets_id": os.getenv("GOOGLE_SHEETS_ID", "1tg5OBvX_ohCrxdiz_2JvtQxTPKmE-hNW27C2WGxH7n0"),
        "service_account_file": os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json"),
        "snapshot_dir": os.getenv("SNAPSHOT_DIR", "data/snapshots"),
        "changes_dir": os.getenv("CHANGES_DIR", "data/changes"),
        "log_dir": os.getenv("LOG_DIR", "logs"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "backfill_days": int(os.getenv("BACKFILL_DAYS", "90")),
    }


def run_daily_analysis(
    target_date: date = None,
    write_sheets: bool = True,
    config: dict = None
):
    """
    Gunluk analiz pipeline'i:
    1. Belirtilen tarihin holdings verisini cek
    2. Bir onceki snapshot ile karsilastir
    3. Sonuclari Google Sheets'e yaz
    4. JSON rapor kaydet
    """
    if config is None:
        config = get_config()

    logger = logging.getLogger("tur_analiz")

    if target_date is None:
        target_date = get_latest_trading_date()

    logger.info(f"{'='*60}")
    logger.info(f"TUR ETF Portfoy Analizi --- {target_date}")
    logger.info(f"{'='*60}")

    # 1. Guncel veriyi cek
    curr_df = fetch_holdings(target_date, config["snapshot_dir"])
    if curr_df is None or curr_df.empty:
        logger.warning(f"{target_date} icin veri alinamadi. Piyasa kapali olabilir.")
        return False

    logger.info(f"Portfoy yuklendi: {len(curr_df)} hisse, {target_date}")

    # 2. Bir onceki snapshot'i bul
    available_dates = get_available_snapshots(config["snapshot_dir"])
    prev_dates = [d for d in available_dates if d < target_date]

    if not prev_dates:
        logger.info("Ilk snapshot kaydedildi. Karsilastirma icin en az 2 gun verisi gerekiyor.")
        if write_sheets:
            _write_to_sheets(curr_df, None, target_date, target_date, config)
        return True

    prev_date = prev_dates[-1]
    prev_snapshot_path = Path(config["snapshot_dir"]) / f"{prev_date.strftime('%Y%m%d')}.csv"
    prev_df = load_snapshot(prev_snapshot_path)

    if prev_df is None:
        logger.error(f"Onceki snapshot yuklenemedi: {prev_snapshot_path}")
        return False

    logger.info(f"Karsilastirma: {prev_date} --> {target_date}")

    # 2.5 Zaten analiz edilmis mi kontrol et (Google Sheets'e cift kayit atmasini onler)
    changes_path = Path(config["changes_dir"]) / f"{target_date.strftime('%Y%m%d')}_changes.json"
    if changes_path.exists():
        logger.info(f"Bu tarih ({target_date}) zaten analiz edilmis. Islem atlandi.")
        return True

    # 3. Analizi calistir
    analysis = compare_snapshots(prev_df, curr_df, prev_date, target_date)
    if analysis is None:
        logger.error("Analiz basarisiz oldu")
        return False

    # 4. Konsol raporu
    analysis.print_report()

    # 5. JSON kaydet
    analysis.save_json(config["changes_dir"])

    # 6. Google Sheets'e yaz
    if write_sheets:
        if analysis.has_changes:
            analysis_dict = analysis.to_dict()
            _write_to_sheets(curr_df, analysis_dict, target_date, prev_date, config)
        else:
            logger.info("Portföyde (ağırlık bazında) hiçbir değişiklik tespit edilmedi. Google Sheets'e işlenmeyecek.")
    else:
        logger.info("--no-sheets aktif, Sheets'e yazilmadi")

    return True


def _write_to_sheets(curr_df, analysis_dict, curr_date, prev_date, config):
    """Google Sheets yazma islemlerini yonetir."""
    logger = logging.getLogger("tur_analiz")

    service_account_file = config["service_account_file"]
    if not Path(service_account_file).exists():
        logger.warning(
            f"Service account dosyasi bulunamadi: {service_account_file}\n"
            f"Google Sheets yazimi atlandi.\n"
            f"Kurulum icin: python setup_google_sheets.py"
        )
        return

    try:
        from sheets_writer import SheetsWriter
        from benchmark import run_benchmark_and_write
        from analyzer import calculate_trade_performance
        writer = SheetsWriter(config["sheets_id"], service_account_file)

        if not writer.connect():
            return

        writer.setup_sheets()

        if analysis_dict:
            writer.write_all(curr_df, analysis_dict, curr_date, prev_date)
            
            # Eger o gün yeni giren veya cikan bir hisse varsa (Yapisal bir revizyon),
            # bunu da Donemsel Revizyonlar sekmesinin en altina "yeni bir donem" olarak ekle!
            if analysis_dict.get("new_entries") or analysis_dict.get("exits"):
                period_data = analysis_dict.copy()
                period_data["start_date"] = str(prev_date)
                period_data["end_date"] = str(curr_date)
                period_data["increased"] = sorted(period_data.get("increased", []), key=lambda x: x.get("change_pp", 0), reverse=True)
                period_data["decreased"] = sorted(period_data.get("decreased", []), key=lambda x: x.get("change_pp", 0))
                writer.write_periodic_revisions([period_data], append=True)
                logger.info(f"Yapisal degisiklik (yeni giren/cikan) tespit edildi. Donemsel Revizyonlar sekmesine otomatik eklendi.")
        else:
            # Ilk calistirma
            writer.write_current_portfolio(curr_df)
            writer.append_raw_data(curr_df)

        # BIST 100 Benchmark Karşılaştırmasını Çalıştır
        try:
            run_benchmark_and_write(writer)
        except Exception as e:
            logger.error(f"Benchmark karsilastirmasi sirasinda hata: {e}")
            
        # Pozisyon Getirileri (Giriş-Çıkış Performansı) Hesapla ve Yaz
        try:
            trades = calculate_trade_performance()
            if trades:
                writer.write_trade_performance(trades)
        except Exception as e:
            logger.error(f"Trade performans hesaplamasi sirasinda hata: {e}")

    except Exception as e:
        logger.error(f"Google Sheets'e yazarken beklenmeyen hata: {e}", exc_info=True)


def run_backfill(days: int = 90, write_sheets: bool = True, config: dict = None):
    """Son N gunun verilerini geriye donuk doldurur."""
    if config is None:
        config = get_config()

    logger = logging.getLogger("tur_analiz")
    logger.info(f"{days} gunluk backfill basliyor...")

    # Once tum snapshot'lari cek
    results = backfill_snapshots(days, config["snapshot_dir"])

    logger.info(f"Analizler hesaplaniyor...")

    # Sonra kronolojik sirada analiz et
    available_dates = get_available_snapshots(config["snapshot_dir"])

    success_count = 0
    for i, curr_date in enumerate(available_dates[1:], 1):
        prev_date = available_dates[i - 1]

        prev_path = Path(config["snapshot_dir"]) / f"{prev_date.strftime('%Y%m%d')}.csv"
        curr_path = Path(config["snapshot_dir"]) / f"{curr_date.strftime('%Y%m%d')}.csv"

        # Zaten analiz edilmis mi?
        changes_path = Path(config["changes_dir"]) / f"{curr_date.strftime('%Y%m%d')}_changes.json"
        if changes_path.exists():
            logger.debug(f"Analiz zaten mevcut, atlandi: {curr_date}")
            continue

        prev_df = load_snapshot(prev_path)
        curr_df = load_snapshot(curr_path)

        analysis = compare_snapshots(prev_df, curr_df, prev_date, curr_date)
        if analysis:
            analysis.save_json(config["changes_dir"])

            if write_sheets:
                if analysis.has_changes:
                    analysis_dict = analysis.to_dict()
                    _write_to_sheets(curr_df, analysis_dict, curr_date, prev_date, config)
                else:
                    logger.debug(f"Değişim yok, Sheets'e yazılmayacak: {curr_date}")

            success_count += 1

    logger.info(f"Backfill tamamlandi: {success_count} analiz islendi")


def main():
    parser = argparse.ArgumentParser(
        description="TUR ETF Portfoy Degisiklik Takip Sistemi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ornekler:
  python main.py                      # En son gecerli tarih icin calistir
  python main.py --date 20260624      # 24 Haziran 2026 icin
  python main.py --backfill           # Son 90 gunu doldur
  python main.py --backfill --days 7  # Son 7 gunu doldur
  python main.py --no-sheets          # Sheets'e yazmadan calistir
        """
    )

    parser.add_argument(
        "--date",
        type=str,
        help="Analiz tarihi (YYYYMMDD formatinda). Varsayilan: en son gecerli tarih",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Gecmis verileri geriye donuk doldur",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Backfill icin kac gun geriye gidilsin",
    )
    parser.add_argument(
        "--no-sheets",
        action="store_true",
        help="Google Sheets'e yazma",
    )

    args = parser.parse_args()

    # Logger kurulumu
    config = get_config()
    logger = setup_logger(config["log_dir"], config["log_level"])

    write_sheets = not args.no_sheets

    if args.backfill:
        days = args.days or config["backfill_days"]
        run_backfill(days, write_sheets, config)
    else:
        target_date = None
        if args.date:
            try:
                target_date = datetime.strptime(args.date, "%Y%m%d").date()
            except ValueError:
                logger.error(f"Gecersiz tarih formati: {args.date}. YYYYMMDD kullanin.")
                sys.exit(1)

        success = run_daily_analysis(target_date, write_sheets, config)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
