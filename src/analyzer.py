"""
analyzer.py — Iki portfoy snapshot'i arasindaki degisiklikleri analiz eder
"""

import logging
import json
from datetime import date
from pathlib import Path
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)


class PortfolioChange:
    """Iki tarih arasindaki portfoy degisiklik analizi."""

    def __init__(self, prev_date: date, curr_date: date, prev_df: pd.DataFrame, curr_df: pd.DataFrame):
        self.prev_date = prev_date
        self.curr_date = curr_date
        self.prev_df = prev_df.copy()
        self.curr_df = curr_df.copy()
        self.unchanged = pd.DataFrame()
        self.new_entries_detail = pd.DataFrame()
        self.exits_detail = pd.DataFrame()
        self.sector_analysis = pd.DataFrame()
        
        # Quant Engine variables
        self.total_fund_flow_usd = 0.0
        self.quant_signals = []

        # Tum analizleri calistir
        self._run_analysis()

    @property
    def has_changes(self) -> bool:
        """Portfoyde gercek bir agirlik veya hisse degisimi olup olmadigini dondurur."""
        return bool(len(self.increased) > 0 or len(self.decreased) > 0 or self.new_entries or self.exits)

    def _run_analysis(self):
        """Tum analiz hesaplamalarini yapar."""
        prev_tickers = set(self.prev_df["ticker"])
        curr_tickers = set(self.curr_df["ticker"])

        # Yeni girenler (onceki listede yok, simdi var)
        self.new_entries = sorted(curr_tickers - prev_tickers)

        # Cikanlar (onceki listede vardi, simdi yok)
        self.exits = sorted(prev_tickers - curr_tickers)

        # Ortak hisseler icin agirlik degisimi
        common = prev_tickers & curr_tickers

        prev_weights = self.prev_df.set_index("ticker")["weight_pct"]
        curr_weights = self.curr_df.set_index("ticker")["weight_pct"]
        prev_quantities = self.prev_df.set_index("ticker")["quantity"]
        prev_prices = self.prev_df.set_index("ticker")["price"]

        total_etf_return = 0.0
        changes = []
        for ticker in common:
            pw = float(prev_weights.get(ticker, 0))
            cw = float(curr_weights.get(ticker, 0))
            change_pp = round(cw - pw, 4)
            change_pct = round((change_pp / pw * 100) if pw > 0 else 0, 2)

            curr_row = self.curr_df[self.curr_df["ticker"] == ticker].iloc[0]
            pq = float(prev_quantities.get(ticker, 0))
            cq = float(curr_row.get("quantity", 0))
            qty_change = cq - pq

            ppr = float(prev_prices.get(ticker, 0))
            cpr = float(curr_row.get("price", 0))
            price_change_pct = round(((cpr / ppr) - 1) * 100, 2) if ppr > 0 else 0.0
            
            # 1. Fund Flow (Net Nakit Akışı)
            flow_usd = qty_change * cpr
            self.total_fund_flow_usd += flow_usd
            
            # 2. Anomali Tespiti (Blok Alım/Satım)
            if pq > 0 and abs(qty_change) / pq > 0.05: # %5 adet değişimi
                action = "Alım" if qty_change > 0 else "Satım"
                self.quant_signals.append({
                    "ticker": ticker,
                    "name": curr_row.get("name", ticker),
                    "signal_type": f"🚨 ANOMALİ (Blok {action})",
                    "description": f"Hisse adedi tek günde %{round(abs(qty_change)/pq*100, 1)} değişti!"
                })

            if qty_change > 0:
                reason = "🟢 Gerçek Fon Alımı"
            elif qty_change < 0:
                reason = "🔴 Gerçek Fon Satışı"
            elif change_pp > 0:
                reason = "📈 Sadece Fiyat Etkisi"
            elif change_pp < 0:
                reason = "📉 Sadece Fiyat Etkisi"
            else:
                reason = "➖ Sıfır Değişim"

            changes.append({
                "ticker": ticker,
                "name": curr_row.get("name", ticker),
                "sector": curr_row.get("sector", ""),
                "prev_weight": pw,
                "curr_weight": cw,
                "change_pp": change_pp,
                "change_pct": change_pct,
                "curr_price": cpr,
                "prev_price": ppr,
                "price_change_pct": price_change_pct,
                "curr_market_value": float(curr_row.get("market_value", 0)),
                "curr_quantity": cq,
                "prev_quantity": pq,
                "qty_change": qty_change,
                "reason": reason
            })
            
            # Endeks günlük getirisine katkısını hesapla
            total_etf_return += (pw / 100.0) * price_change_pct

        self.changes_df = pd.DataFrame(changes).sort_values("change_pp", ascending=False)
        self.etf_daily_return_pct = round(total_etf_return, 2)

        # Artanlar (pozitif degisim)
        self.increased = self.changes_df[self.changes_df["change_pp"] > 0.001].copy()

        # Azalanlar (negatif degisim)
        self.decreased = self.changes_df[self.changes_df["change_pp"] < -0.001].copy()

        # Sabit kalanlar
        self.unchanged = self.changes_df[
            (self.changes_df["change_pp"] >= -0.001) &
            (self.changes_df["change_pp"] <= 0.001)
        ].copy()

        # Yeni girenlerin detaylari
        self.new_entries_detail = self.curr_df[
            self.curr_df["ticker"].isin(self.new_entries)
        ].copy()

        # Cikanlarin detaylari
        self.exits_detail = self.prev_df[
            self.prev_df["ticker"].isin(self.exits)
        ].copy()

        # Geçmiş ağırlıkları (Tüm zamanların ilk ağırlığı) hesapla
        self.initial_weights = {}
        try:
            # Sadece local import kullanıyoruz
            from src.analyzer import build_historical_weight_matrix
            hist_weights = build_historical_weight_matrix("data/snapshots")
            for t in curr_tickers:
                if not hist_weights.empty and t in hist_weights.columns:
                    series = hist_weights[t]
                    nonzero = series[series > 0]
                    if not nonzero.empty:
                        self.initial_weights[t] = float(nonzero.iloc[0])
                    else:
                        self.initial_weights[t] = float(curr_weights.get(t, 0))
                else:
                    self.initial_weights[t] = float(curr_weights.get(t, 0))
        except Exception as e:
            logger.error(f"Kümülatif hesaplama hatası: {e}")
            self.initial_weights = {t: float(curr_weights.get(t, 0)) for t in curr_tickers}

        # Sektor bazli analiz
        self.sector_analysis = self._compute_sector_analysis()

        # Ozet istatistikler
        self.summary = {
            "prev_date": self.prev_date.strftime("%Y-%m-%d"),
            "curr_date": self.curr_date.strftime("%Y-%m-%d"),
            "prev_holdings_count": len(self.prev_df),
            "curr_holdings_count": len(self.curr_df),
            "new_entries_count": len(self.new_entries),
            "exits_count": len(self.exits),
            "increased_count": len(self.increased),
            "decreased_count": len(self.decreased),
            "unchanged_count": len(self.unchanged),
            "top_gainer": self.increased.iloc[0]["ticker"] if not self.increased.empty else None,
            "top_gainer_change": float(self.increased.iloc[0]["change_pp"]) if not self.increased.empty else 0,
            "top_loser": self.decreased.iloc[-1]["ticker"] if not self.decreased.empty else None,
            "top_loser_change": float(self.decreased.iloc[-1]["change_pp"]) if not self.decreased.empty else 0,
            "etf_daily_return_pct": self.etf_daily_return_pct,
            "total_fund_flow_usd": self.total_fund_flow_usd
        }

    def _compute_sector_analysis(self) -> pd.DataFrame:
        """Sektor bazli agirlik degisimi hesaplar."""
        prev_sector = (
            self.prev_df.groupby("sector")["weight_pct"].sum().reset_index()
            .rename(columns={"weight_pct": "prev_weight"})
        )
        curr_sector = (
            self.curr_df.groupby("sector")["weight_pct"].sum().reset_index()
            .rename(columns={"weight_pct": "curr_weight"})
        )
        sector_df = pd.merge(prev_sector, curr_sector, on="sector", how="outer").fillna(0)
        sector_df["change_pp"] = (sector_df["curr_weight"] - sector_df["prev_weight"]).round(4)
        sector_df["change_pct"] = (
            sector_df.apply(
                lambda r: round((r["change_pp"] / r["prev_weight"] * 100) if r["prev_weight"] > 0 else 0, 2),
                axis=1
            )
        )
        return sector_df.sort_values("change_pp", ascending=False)

    def print_report(self):
        """Konsola analiz raporunu yazdirir."""
        print(f"\n{'='*70}")
        print(f"  TUR ETF PORTFOY DEGISIKLIK RAPORU")
        print(f"  Tarih: {self.prev_date} --> {self.curr_date}")
        print(f"{'='*70}\n")

        print(f"  Toplam Hisse: {self.summary['prev_holdings_count']} --> {self.summary['curr_holdings_count']}")
        if self.new_entries:
            print(f"  [YENi GIREN] ({len(self.new_entries)}): {', '.join(self.new_entries)}")
        if self.exits:
            print(f"  [CIKAN]      ({len(self.exits)}): {', '.join(self.exits)}")

        # En cok artan
        if not self.increased.empty:
            print(f"\n  AGIRLIK ARTAN POZISYONLAR (Ilk 10):")
            print(f"  {'Tiker':<12} {'Isim':<38} {'Onceki':>8} {'Yeni':>8} {'Degisim':>10}")
            print(f"  {'-'*80}")
            for _, row in self.increased.head(10).iterrows():
                print(
                    f"  {row['ticker']:<12} {str(row['name'])[:37]:<38} "
                    f"{row['prev_weight']:>7.2f}% {row['curr_weight']:>7.2f}% "
                    f"+{row['change_pp']:>8.4f}pp"
                )

        # En cok azalan
        if not self.decreased.empty:
            print(f"\n  AGIRLIK AZALAN POZISYONLAR (Ilk 10):")
            print(f"  {'Tiker':<12} {'Isim':<38} {'Onceki':>8} {'Yeni':>8} {'Degisim':>10}")
            print(f"  {'-'*80}")
            for _, row in self.decreased.tail(10).iterrows():
                print(
                    f"  {row['ticker']:<12} {str(row['name'])[:37]:<38} "
                    f"{row['prev_weight']:>7.2f}% {row['curr_weight']:>7.2f}% "
                    f"{row['change_pp']:>9.4f}pp"
                )

        # Sektor analizi
        print(f"\n  SEKTOR BAZLI DEGISIM:")
        print(f"  {'Sektor':<32} {'Onceki':>8} {'Yeni':>8} {'Degisim':>10}")
        print(f"  {'-'*65}")
        for _, row in self.sector_analysis.iterrows():
            change_str = f"{row['change_pp']:+.4f}pp"
            print(
                f"  {str(row['sector'])[:31]:<32} "
                f"{row['prev_weight']:>7.2f}% {row['curr_weight']:>7.2f}% "
                f"{change_str:>10}"
            )

        print(f"\n{'='*70}\n")

    def to_dict(self) -> dict:
        """Tum analiz sonuclarini dict'e donusturur."""
        return {
            "summary": self.summary,
            "increased": self.increased.to_dict(orient="records"),
            "decreased": self.decreased.to_dict(orient="records"),
            "unchanged": self.unchanged.to_dict(orient="records"),
            "new_entries": self.new_entries_detail.to_dict(orient="records"),
            "exits": self.exits_detail.to_dict(orient="records"),
            "sector_analysis": self.sector_analysis.to_dict(orient="records"),
            "quant_signals": self.quant_signals,
            "cumulative_initial_weights": self.initial_weights,
        }

    def save_json(self, changes_dir: str = "data/changes"):
        """Analiz sonucunu JSON dosyasina kaydeder."""
        Path(changes_dir).mkdir(parents=True, exist_ok=True)
        filename = f"{self.curr_date.strftime('%Y%m%d')}_changes.json"
        path = Path(changes_dir) / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Degisim raporu kaydedildi: {path}")
        return path

    def _calculate_advanced_signals(self):
        """Tarihsel matrisi kullanarak SMA-20 (Golden Cross) sinyallerini üretir."""
        try:
            pivot_df = build_historical_weight_matrix("data/snapshots")
            if pivot_df is None or pivot_df.empty:
                return
                
            date_cols = [c for c in pivot_df.columns if c not in ["ticker", "name"]]
            date_cols.sort()
            
            if len(date_cols) >= 20:
                last_20 = date_cols[-20:]
                last_19 = date_cols[-21:-1] # Önceki günün 20 günlük penceresi
                
                for _, row in pivot_df.iterrows():
                    ticker = row["ticker"]
                    curr_w = float(row[date_cols[-1]])
                    prev_w = float(row[date_cols[-2]])
                    
                    sma20_curr = float(row[last_20].mean())
                    sma20_prev = float(row[last_19].mean())
                    
                    if curr_w > sma20_curr and prev_w <= sma20_prev:
                        self.quant_signals.append({
                            "ticker": ticker,
                            "name": row.get("name", ""),
                            "signal_type": "🟢 GOLDEN CROSS",
                            "description": "Hisse ağırlığı 20 günlük hareketli ortalamayı (SMA-20) YUKARI kesti."
                        })
                    elif curr_w < sma20_curr and prev_w >= sma20_prev:
                        self.quant_signals.append({
                            "ticker": ticker,
                            "name": row.get("name", ""),
                            "signal_type": "🔴 DEATH CROSS",
                            "description": "Hisse ağırlığı 20 günlük hareketli ortalamayı (SMA-20) AŞAĞI kesti."
                        })
        except Exception as e:
            logger.error(f"Sinyal hesaplama hatasi: {e}")


def compare_snapshots(
    prev_df: pd.DataFrame,
    curr_df: pd.DataFrame,
    prev_date: date,
    curr_date: date,
) -> Optional[PortfolioChange]:
    """Iki snapshot'i karsilastirir ve PortfolioChange dondurur."""
    if prev_df is None or curr_df is None:
        logger.error("Karsilastirma icin her iki snapshot da gereklidir")
        return None
    if prev_df.empty or curr_df.empty:
        logger.warning("Bos snapshot'lar karsilastirilamaz")
        return None

    return PortfolioChange(prev_date, curr_date, prev_df, curr_df)


def build_historical_weight_matrix(snapshot_dir: str = "data/snapshots") -> pd.DataFrame:
    """
    Tum snapshot'lardan zaman serisi agirlik matrisi olusturur.
    Satirlar = tarihler, Sutunlar = tiker sembolleri
    """
    from fetcher import get_available_snapshots, load_snapshot

    dates = get_available_snapshots(snapshot_dir)
    if not dates:
        logger.warning("Hic snapshot bulunamadi")
        return pd.DataFrame()

    all_data = []
    for d in dates:
        path = Path(snapshot_dir) / f"{d.strftime('%Y%m%d')}.csv"
        df = load_snapshot(path)
        if df is not None and not df.empty:
            row = {"date": d.strftime("%Y-%m-%d")}
            for _, stock_row in df.iterrows():
                row[stock_row["ticker"]] = stock_row["weight_pct"]
            all_data.append(row)

    if not all_data:
        return pd.DataFrame()

    matrix = pd.DataFrame(all_data).set_index("date").fillna(0)
    matrix = matrix.sort_index()
    logger.info(f"Tarihsel agirlik matrisi olusturuldu: {matrix.shape[0]} gun x {matrix.shape[1]} hisse")
    return matrix


def build_historical_sector_matrix(snapshot_dir: str = "data/snapshots") -> pd.DataFrame:
    """
    Tum snapshot'lardan zaman serisi sektör agirlik matrisi olusturur.
    Satirlar = tarihler, Sutunlar = sektor isimleri
    """
    from fetcher import get_available_snapshots, load_snapshot

    dates = get_available_snapshots(snapshot_dir)
    if not dates:
        logger.warning("Hic snapshot bulunamadi (Sektor Matrisi icin)")
        return pd.DataFrame()

    all_data = []
    for d in dates:
        path = Path(snapshot_dir) / f"{d.strftime('%Y%m%d')}.csv"
        df = load_snapshot(path)
        if df is not None and not df.empty:
            row = {"date": d.strftime("%Y-%m-%d")}
            
            # Sektor bazinda agirliklari topla
            # Not: df icindeki weight_pct degerini kullan, ya da weight (%) i donustur.
            # Normalde fetcher.py weight_pct yi yuzde olarak ayarlar
            if "weight_pct" in df.columns:
                sector_sums = df.groupby("sector")["weight_pct"].sum()
                for sector, weight in sector_sums.items():
                    if pd.notna(sector) and sector.strip():
                        row[sector] = weight
            all_data.append(row)

    if not all_data:
        return pd.DataFrame()

    matrix_df = pd.DataFrame(all_data)
    if matrix_df.empty:
        return matrix_df
        
    matrix = matrix_df.set_index("date").fillna(0).T
    # Sutunlari (tarihleri) ve satirlari sirala
    matrix = matrix[sorted(matrix.columns)]
    matrix = matrix.sort_index()
    logger.info(f"Tarihsel sektor matrisi olusturuldu: {matrix.shape[0]} sektor x {matrix.shape[1]} gun")
    return matrix

def calculate_trade_performance(snapshot_dir: str = "data/snapshots") -> list:
    """
    Geçmişten bugüne tüm hisselerin fona giriş ve çıkış tarihlerini, 
    giriş-çıkış fiyatlarını ve dolar bazlı getirilerini hesaplar.
    """
    from fetcher import get_available_snapshots, load_snapshot
    from datetime import datetime

    dates = get_available_snapshots(snapshot_dir)
    if not dates:
        logger.warning("Hic snapshot bulunamadi (Trade Performansı icin)")
        return []

    # trades: dict of ticker -> list of trade records (to handle re-entries)
    # A trade record: {"name": "", "entry_date": None, "entry_price": 0, "last_date": None, "last_price": 0, "status": "Aktif"}
    trades = {}
    completed_trades = []

    for d in dates:
        path = Path(snapshot_dir) / f"{d.strftime('%Y%m%d')}.csv"
        df = load_snapshot(path)
        if df is None or df.empty:
            continue
            
        current_tickers = set()
        
        for _, row in df.iterrows():
            ticker = row["ticker"]
            name = row["name"]
            try:
                price = float(row.get("price", 0))
            except:
                price = 0.0
                
            try:
                weight_val = row.get("weight_pct") if "weight_pct" in row else row.get("weight (%)", 0)
                weight = float(weight_val)
            except:
                weight = 0.0
                
            if price == 0.0:
                # Eger fiyat yoksa kayitlari bozmamak icin atla
                continue
                
            current_tickers.add(ticker)
            
            if ticker not in trades:
                # Yeni giris
                trades[ticker] = {
                    "ticker": ticker,
                    "name": name,
                    "entry_date": d,
                    "entry_price": price,
                    "entry_weight": weight,
                    "last_date": d,
                    "last_price": price,
                    "last_weight": weight,
                    "status": "Aktif"
                }
            else:
                # Guncelleme
                trades[ticker]["last_date"] = d
                trades[ticker]["last_price"] = price
                trades[ticker]["last_weight"] = weight
                trades[ticker]["name"] = name # Isim guncellemesi (degismisse)
                
        # Bugun portfoyde olmayanlari bul ve kapat
        exited_tickers = []
        for ticker, trade in trades.items():
            if ticker not in current_tickers:
                trade["status"] = "Kapalı"
                trade["exit_date"] = trade["last_date"]
                trade["exit_price"] = trade["last_price"]
                trade["exit_weight"] = trade["last_weight"]
                completed_trades.append(trade)
                exited_tickers.append(ticker)
                
        # Kapali olanlari aktif listeden cikar
        for t in exited_tickers:
            del trades[t]

    # Dongu bittiginde hala aktif olanlari toparla
    for ticker, trade in trades.items():
        trade["exit_date"] = trade["last_date"]
        trade["exit_price"] = trade["last_price"]
        trade["exit_weight"] = trade["last_weight"]
        completed_trades.append(trade)

    # Sonuclari listele ve hesaplamalari yap
    results = []
    for t in completed_trades:
        ep = t["entry_price"]
        xp = t["exit_price"]
        ew = t.get("entry_weight", 0)
        xw = t.get("exit_weight", 0)
        
        ret_pct = (xp / ep - 1.0) if ep > 0 else 0.0
        weight_change_pp = xw - ew
        days_held = (t["exit_date"] - t["entry_date"]).days
        
        # Ayni gun girip cikanlar (hata veya kisa trade) gun 1 yapalim division by zero engellemek icin (gerekmese de gorsel icin iyi)
        if days_held == 0:
            days_held = 1
            
        results.append({
            "ticker": t["ticker"],
            "name": t["name"],
            "status": t["status"],
            "entry_date": t["entry_date"].strftime("%Y-%m-%d"),
            "entry_price": ep,
            "exit_date": t["exit_date"].strftime("%Y-%m-%d"),
            "exit_price": xp,
            "return_pct": ret_pct,
            "entry_weight": ew,
            "exit_weight": xw,
            "weight_change_pp": weight_change_pp,
            "days_held": days_held
        })

    # En yuksek getiriye gore sirala
    results = sorted(results, key=lambda x: x["return_pct"], reverse=True)
    return results
