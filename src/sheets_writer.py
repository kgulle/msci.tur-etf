"""
sheets_writer.py — Google Sheets'e portföy analiz verisi yazar
"""

import logging
import time
from datetime import date, datetime
from typing import Optional
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

# Google Sheets API'si için gerekli izinler
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Sabit sekme siralamasi
SHEET_NAMES = {
    "readme":       "📖 Kılavuz",
    "strategy":     "💡 Yatırım Stratejisi",
    "summary":      "📊 Güncel Portföy",
    "history":      "📈 Değişim Geçmişi",
    "increased":    "🚀 Pozisyon Artışları",
    "decreased":    "📉 Pozisyon Düşüşleri",
    "new_entries":  "🆕 Yeni Girenler",
    "exits":        "🚪 Çıkanlar",
    "raw_data":     "📋 Ham Veri",
    "sector":       "🏭 Sektör Analizi",
    "weight_matrix":"📅 Ağırlık Matrisi",
    "price_matrix": "💵 Fiyat Matrisi (USD)",
    "correlation_analysis": "📉 Korelasyon Analizi",
    "advanced_signals": "🎯 Gelişmiş Sinyaller",
    "sector_matrix": "📊 Sektör Trendleri",
    "ai_summary":   "🤖 Yapay Zeka Özeti",
    "revisions":    "🔄 Dönemsel Revizyonlar",
    "benchmark":    "⚖️ BIST100 vs TUR",
    "trades":       "⏳ Pozisyon Getirileri",
}

# Gorsellestirme icin sabit renkler
SHEET_COLORS = {
    "readme":      {"red": 0.20, "green": 0.20, "blue": 0.20},
    "strategy":    {"red": 0.90, "green": 0.70, "blue": 0.10},
    "summary":     {"red": 0.20, "green": 0.60, "blue": 0.86},
    "history":     {"red": 0.18, "green": 0.80, "blue": 0.44},
    "increased":   {"red": 0.07, "green": 0.53, "blue": 0.30},
    "decreased":   {"red": 0.70, "green": 0.15, "blue": 0.15},
    "new_entries": {"red": 0.07, "green": 0.53, "blue": 0.35},
    "exits":       {"red": 0.65, "green": 0.25, "blue": 0.10},
    "raw_data":    {"red": 0.35, "green": 0.35, "blue": 0.35},
    "sector":      {"red": 0.40, "green": 0.20, "blue": 0.60},
    "weight_matrix":{"red": 0.80, "green": 0.40, "blue": 0.20},
    "price_matrix": {"red": 0.85, "green": 0.65, "blue": 0.13},
    "correlation_analysis": {"red": 0.20, "green": 0.40, "blue": 0.60},
    "advanced_signals": {"red": 0.80, "green": 0.10, "blue": 0.40},
    "sector_matrix": {"red": 0.50, "green": 0.30, "blue": 0.80},
    "ai_summary":  {"red": 0.10, "green": 0.60, "blue": 0.30},
    "revisions":   {"red": 0.55, "green": 0.20, "blue": 0.65},
    "benchmark":   {"red": 0.15, "green": 0.45, "blue": 0.85},
    "trades":      {"red": 0.80, "green": 0.60, "blue": 0.10},
}


class SheetsWriter:
    """Google Sheets yazıcı sınıfı."""

    def __init__(self, spreadsheet_id: str, service_account_file: str):
        self.spreadsheet_id = spreadsheet_id
        self.service_account_file = service_account_file
        self.gc: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None

    def connect(self):
        """Google Sheets API'ye bağlanır."""
        try:
            creds = Credentials.from_service_account_file(
                self.service_account_file, scopes=SCOPES
            )
            self.gc = gspread.authorize(creds)
            self.spreadsheet = self.gc.open_by_key(self.spreadsheet_id)
            logger.info(f"✅ Google Sheets bağlantısı başarılı: '{self.spreadsheet.title}'")
            return True
        except FileNotFoundError:
            logger.error(
                f"❌ Service account dosyası bulunamadı: {self.service_account_file}\n"
                f"   setup_google_sheets.py ile kurulumu tamamlayın."
            )
            return False
        except gspread.exceptions.APIError as e:
            logger.error(f"❌ Google Sheets API hatası: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Bağlantı hatası: {e}")
            return False

    def setup_sheets(self):
        """Gerekli sekmeleri oluşturur veya günceller."""
        if not self.spreadsheet:
            logger.error("Önce connect() çağırın")
            return

        existing = {ws.title: ws for ws in self.spreadsheet.worksheets()}

        for key, name in SHEET_NAMES.items():
            if name not in existing:
                logger.info(f"  📑 '{name}' sekmesi oluşturuluyor...")
                ws = self.spreadsheet.add_worksheet(title=name, rows=5000, cols=30)
                # Sekme rengi ayarla
                color = SHEET_COLORS.get(key, {"red": 0.5, "green": 0.5, "blue": 0.5})
                self.spreadsheet.batch_update({
                    "requests": [{
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": ws.id,
                                "tabColor": color,
                            },
                            "fields": "tabColor",
                        }
                    }]
                })
                time.sleep(0.5)
            else:
                logger.debug(f"  ✓ '{name}' sekmesi zaten mevcut")

        logger.info("✅ Tüm sekmeler hazır")

    def _get_sheet(self, key: str) -> Optional[gspread.Worksheet]:
        """Sekme adına göre worksheet döndürür."""
        name = SHEET_NAMES.get(key)
        if not name:
            return None
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            logger.error(f"'{name}' sekmesi bulunamadı. setup_sheets() çalıştırın.")
            return None

    def _rate_limit(self, seconds: float = 4.0):
        """API rate limit için bekler."""
        time.sleep(seconds)

    def write_current_portfolio(self, df: pd.DataFrame, analysis=None):
        """
        📊 Güncel Portföy sekmesini günceller.
        Her çalıştırmada tamamen yeniden yazılır.
        """
        ws = self._get_sheet("summary")
        if ws is None:
            return

        headers = [
            "Sıra", "Tiker", "📈 Fiyat Trendi", "Şirket Adı", "Sektör",
            "Ağırlık (%)", "İlk Ağırlık (%)", "📊 Kümülatif Ağırlık Değişimi (%)", "Piyasa Değeri (USD)",
            "Adet", "Fiyat (USD)",
            "Önceki Ağırlık (%)", "📊 Günlük Ağırlık Değişimi (%)", "Durum",
            "Tarih"
        ]

        rows = [headers]
        for i, row in enumerate(df.itertuples(), 1):
            # Önceki veriden değişim bilgisi
            change_pp = ""
            status = ""
            prev_weight = ""
            weight_change_pct = ""
            initial_weight = ""
            cumulative_change_pct = ""

            if analysis:
                ticker = row.ticker
                
                # Kümülatif istatistikleri cek
                initial_weights_dict = analysis.get("cumulative_initial_weights", {})
                if ticker in initial_weights_dict:
                    iw = float(initial_weights_dict[ticker])
                    cw = float(getattr(row, "weight_pct", 0))
                    initial_weight = iw
                    if iw > 0:
                        cumulative_change_pct = (cw / iw) - 1.0
                    else:
                        cumulative_change_pct = 0.0

                if ticker in [e["ticker"] for e in analysis.get("new_entries", []) if isinstance(e, dict)]:
                    status = "🆕 Yeni"
                    weight_change_pct = 1.0 # 100% since it's new
                else:
                    # changes_df'ten bul
                    changes = {c["ticker"]: c for c in (
                        analysis.get("increased", []) +
                        analysis.get("decreased", []) +
                        analysis.get("unchanged", [])
                    ) if isinstance(c, dict)}
                    if ticker in changes:
                        c = changes[ticker]
                        prev_weight = c.get("prev_weight", "")
                        cp = c.get("change_pp", 0)
                        change_pp = f"+{cp:.4f}" if cp > 0 else f"{cp:.4f}"
                        if cp > 0.01:
                            status = "📈 Artan"
                        elif cp < -0.01:
                            status = "📉 Azalan"
                        else:
                            status = "➡️ Sabit"
                            
                        # Calculate proportional weight change %
                        try:
                            pw = float(prev_weight) if prev_weight else 0.0
                            weight_change_pct = (cp / pw) if pw > 0 else 0.0
                        except:
                            weight_change_pct = 0.0
            
            row_idx = i + 1
            sparkline_formula = f'=IFNA(SPARKLINE(INDEX(\'💵 Fiyat Matrisi (USD)\'!E:ZZ; MATCH(B{row_idx}; \'💵 Fiyat Matrisi (USD)\'!A:A; 0))); "")'

            rows.append([
                i,
                getattr(row, "ticker", ""),
                sparkline_formula,
                getattr(row, "name", ""),
                getattr(row, "sector", ""),
                getattr(row, "weight_pct", ""),
                initial_weight,
                cumulative_change_pct,
                getattr(row, "market_value", ""),
                getattr(row, "quantity", ""),
                getattr(row, "price", ""),
                prev_weight,
                weight_change_pct,
                status,
                getattr(row, "as_of_date", ""),
            ])

        ws.clear()
        self._rate_limit()
        ws.update(values=rows, range_name="A1", value_input_option='USER_ENTERED')
        self._rate_limit()

        # Sütun formatlama (Ağırlık değişimi yüzdeleri için G ve M kolonları)
        try:
            ws.format("H2:H", {
                "numberFormat": {
                    "type": "PERCENT",
                    "pattern": "0.00%"
                }
            })
            ws.format("M2:M", {
                "numberFormat": {
                    "type": "PERCENT",
                    "pattern": "0.00%"
                }
            })
        except:
            pass

        # Başlık satırı formatı
        ws.format("A1:O1", {
            "backgroundColor": {"red": 0.13, "green": 0.33, "blue": 0.55},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        })
        self._rate_limit()

        # Sütun genişlikleri ve Satır yükseklikleri
        self.spreadsheet.batch_update({
            "requests": [
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": ws.id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 15,
                        },
                        "properties": {"pixelSize": 120},
                        "fields": "pixelSize",
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": ws.id,
                            "dimension": "COLUMNS",
                            "startIndex": 2, # Trend
                            "endIndex": 3,
                        },
                        "properties": {"pixelSize": 180},
                        "fields": "pixelSize",
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": ws.id,
                            "dimension": "ROWS",
                            "startIndex": 1,
                            "endIndex": len(rows),
                        },
                        "properties": {"pixelSize": 45},
                        "fields": "pixelSize",
                    }
                }
            ]
        })
        logger.info(f"  ✅ '{SHEET_NAMES['summary']}' güncellendi ({len(df)} hisse)")
        self._rate_limit()

    def append_change_history(self, analysis: dict):
        """📈 Değişim Geçmişi sekmesine yeni satır ekler."""
        ws = self._get_sheet("history")
        if ws is None:
            return

        # Başlık yoksa ekle
        existing = ws.get_all_values()
        if not existing or len(existing) == 0 or len(existing[0]) == 0 or existing[0][0] != "Tarih":
            headers = [
                "Tarih", "Önceki Tarih",
                "Toplam Hisse (Önceki)", "Toplam Hisse (Yeni)",
                "Yeni Giren", "Çıkan",
                "Ağırlığı Artan", "Ağırlığı Azalan",
                "En Çok Artan Tiker", "En Çok Artan (pp)",
                "En Çok Azalan Tiker", "En Çok Azalan (pp)",
            ]
            ws.insert_row(headers, 1)
            ws.format("A1:L1", {
                "backgroundColor": {"red": 0.20, "green": 0.40, "blue": 0.60},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            })
            self._rate_limit()

        s = analysis.get("summary", {})
        new_row = [
            s.get("curr_date", ""),
            s.get("prev_date", ""),
            s.get("prev_holdings_count", ""),
            s.get("curr_holdings_count", ""),
            s.get("new_entries_count", 0),
            s.get("exits_count", 0),
            s.get("increased_count", 0),
            s.get("decreased_count", 0),
            s.get("top_gainer", ""),
            s.get("top_gainer_change", 0),
            s.get("top_loser", ""),
            s.get("top_loser_change", 0),
        ]
        ws.append_row(new_row)
        self._rate_limit()
        logger.info(f"  ✅ '{SHEET_NAMES['history']}' güncellendi")

    def append_position_changes(self, analysis: dict, curr_date: date):
        """🚀📉 Pozisyon artış/düşüş sekmelerine yeni satırlar ekler."""
        date_str = curr_date.strftime("%Y-%m-%d")
        
        for key, data_key in [("increased", "increased"), ("decreased", "decreased")]:
            ws = self._get_sheet(key)
            if ws is None:
                continue

            records = analysis.get(data_key, [])
            if not records:
                continue

            existing = ws.get_all_values()
            if not existing or len(existing) == 0 or len(existing[0]) == 0 or existing[0][0] != "Tarih":
                headers = [
                    "Tarih", "Tiker", "📈 Fiyat Trendi", "Şirket Adı", "Sektör",
                    "Önceki Ağırlık (%)", "Yeni Ağırlık (%)",
                    "Değişim (pp)", "Oransal Değişim (%)",
                    "Adet Değişimi", "Fiyat Getirisi (%)", "Değişim Kaynağı",
                    "Piyasa Değeri (USD)"
                ]
                ws.insert_row(headers, 1)
                color = {"red": 0.07, "green": 0.53, "blue": 0.30} if key == "increased" else {"red": 0.70, "green": 0.15, "blue": 0.15}
                ws.format("A1:L1", {
                    "backgroundColor": color,
                    "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                })
                self._rate_limit()

            rows_to_add = []
            base_row_num = max(len(existing) if existing else 0, 1)
            
            for i, rec in enumerate(records):
                if not isinstance(rec, dict):
                    continue
                    
                row_num = base_row_num + i + 1
                sparkline_formula = f'=IFNA(SPARKLINE(INDEX(\'💵 Fiyat Matrisi (USD)\'!E:ZZ; MATCH(B{row_num}; \'💵 Fiyat Matrisi (USD)\'!A:A; 0))); "")'
                
                rows_to_add.append([
                    date_str,
                    rec.get("ticker", ""),
                    sparkline_formula,
                    rec.get("name", ""),
                    rec.get("sector", ""),
                    rec.get("prev_weight", 0) / 100.0,
                    rec.get("curr_weight", 0) / 100.0,
                    rec.get("change_pp", 0),
                    rec.get("change_pct", 0) / 100.0,
                    rec.get("qty_change", 0),
                    rec.get("price_change_pct", 0) / 100.0,
                    rec.get("reason", ""),
                    rec.get("curr_market_value", 0),
                ])

            if rows_to_add:
                ws.append_rows(rows_to_add, value_input_option='USER_ENTERED')
                
                # Formatlama
                try:
                    # % kolonları formati
                    ws.format("F2:G", {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}})
                    ws.format("I2:I", {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}})
                    ws.format("K2:K", {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}})
                    
                    # Satır ve sütun boyutlandırması
                    self.spreadsheet.batch_update({
                        "requests": [
                            {
                                "updateDimensionProperties": {
                                    "range": {
                                        "sheetId": ws.id,
                                        "dimension": "COLUMNS",
                                        "startIndex": 2, # Trend
                                        "endIndex": 3,
                                    },
                                    "properties": {"pixelSize": 180},
                                    "fields": "pixelSize",
                                }
                            },
                            {
                                "updateDimensionProperties": {
                                    "range": {
                                        "sheetId": ws.id,
                                        "dimension": "ROWS",
                                        "startIndex": 1,
                                        "endIndex": base_row_num + len(rows_to_add) + 1,
                                    },
                                    "properties": {"pixelSize": 45},
                                    "fields": "pixelSize",
                                }
                            }
                        ]
                    })
                except Exception as e:
                    logger.warning(f"{key} sekmesi formatlanamadi: {e}")
                    
                self._rate_limit()
                logger.info(f"  ✅ '{SHEET_NAMES[key]}': {len(rows_to_add)} satır eklendi")

    def append_new_entries_exits(self, analysis: dict, curr_date: date, prev_date: date):
        """🆕🚪 Yeni girenler ve çıkanlar sekmelerini günceller."""
        date_str = curr_date.strftime("%Y-%m-%d")
        
        for key, data_key in [("new_entries", "new_entries"), ("exits", "exits")]:
            ws = self._get_sheet(key)
            if ws is None:
                continue

            records = analysis.get(data_key, [])
            if not records:
                continue

            existing = ws.get_all_values()
            if not existing or len(existing) == 0 or len(existing[0]) == 0 or existing[0][0] != "Tarih":
                headers = [
                    "Tarih", "Önceki Tarih", "Tiker", "📈 Fiyat Trendi", "Şirket Adı", "Sektör",
                    "Ağırlık (%)", "Piyasa Değeri (USD)", "Adet", "Fiyat (USD)",
                ]
                ws.insert_row(headers, 1)
                color = {"red": 0.07, "green": 0.53, "blue": 0.35} if key == "new_entries" else {"red": 0.65, "green": 0.25, "blue": 0.10}
                ws.format("A1:I1", {
                    "backgroundColor": color,
                    "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                })
                self._rate_limit()

            rows_to_add = []
            base_row_num = max(len(existing) if existing else 0, 1)
            
            for i, rec in enumerate(records):
                if not isinstance(rec, dict):
                    continue
                
                row_num = base_row_num + i + 1
                sparkline_formula = f'=IFNA(SPARKLINE(INDEX(\'💵 Fiyat Matrisi (USD)\'!E:ZZ; MATCH(C{row_num}; \'💵 Fiyat Matrisi (USD)\'!A:A; 0))); "")'
                
                rows_to_add.append([
                    date_str,
                    prev_date.strftime("%Y-%m-%d"),
                    rec.get("ticker", ""),
                    sparkline_formula,
                    rec.get("name", ""),
                    rec.get("sector", ""),
                    rec.get("weight_pct", ""),
                    rec.get("market_value", ""),
                    rec.get("quantity", ""),
                    rec.get("price", ""),
                ])

            if rows_to_add:
                ws.append_rows(rows_to_add, value_input_option='USER_ENTERED')
                
                try:
                    self.spreadsheet.batch_update({
                        "requests": [
                            {
                                "updateDimensionProperties": {
                                    "range": {
                                        "sheetId": ws.id,
                                        "dimension": "COLUMNS",
                                        "startIndex": 3, # Trend
                                        "endIndex": 4,
                                    },
                                    "properties": {"pixelSize": 180},
                                    "fields": "pixelSize",
                                }
                            },
                            {
                                "updateDimensionProperties": {
                                    "range": {
                                        "sheetId": ws.id,
                                        "dimension": "ROWS",
                                        "startIndex": 1,
                                        "endIndex": base_row_num + len(rows_to_add) + 1,
                                    },
                                    "properties": {"pixelSize": 45},
                                    "fields": "pixelSize",
                                }
                            }
                        ]
                    })
                except Exception as e:
                    logger.warning(f"{key} sekmesi formatlanamadi: {e}")
                    
                self._rate_limit()
                logger.info(f"  ✅ '{SHEET_NAMES[key]}': {len(rows_to_add)} satır eklendi")

    def append_sector_analysis(self, analysis: dict, curr_date: date):
        """🏭 Sektör analizi sekmesine veri ekler."""
        ws = self._get_sheet("sector")
        if ws is None:
            return

        records = analysis.get("sector_analysis", [])
        if not records:
            return

        existing = ws.get_all_values()
        if not existing or len(existing) == 0 or len(existing[0]) == 0 or existing[0][0] != "Tarih":
            headers = [
                "Tarih", "Sektör",
                "Önceki Ağırlık (%)", "Yeni Ağırlık (%)",
                "Değişim (pp)", "Değişim (%)",
            ]
            ws.insert_row(headers, 1)
            ws.format("A1:F1", {
                "backgroundColor": {"red": 0.40, "green": 0.20, "blue": 0.60},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            })
            self._rate_limit()

        date_str = curr_date.strftime("%Y-%m-%d")
        rows_to_add = []
        for rec in records:
            if not isinstance(rec, dict):
                continue
            rows_to_add.append([
                date_str,
                rec.get("sector", ""),
                rec.get("prev_weight", ""),
                rec.get("curr_weight", ""),
                rec.get("change_pp", ""),
                rec.get("change_pct", ""),
            ])

        if rows_to_add:
            ws.append_rows(rows_to_add)
            self._rate_limit()
            logger.info(f"  ✅ '{SHEET_NAMES['sector']}': {len(rows_to_add)} sektör güncellendi")

    def write_periodic_revisions(self, periods_data: list, append: bool = False):
        """🔄 Dönemsel Revizyonlar sekmesine seçili tarih aralıklarındaki değişiklikleri yazar."""
        ws = self._get_sheet("revisions")
        if ws is None:
            return

        if not append:
            ws.clear()
            current_row = 1
            base_row = 0
        else:
            existing = ws.get_all_values()
            base_row = len(existing) if existing else 0
            current_row = base_row + 1
            
        all_rows = []
        fmt_requests = []
        
        for period in periods_data:
            start_date = period["start_date"]
            end_date = period["end_date"]
            new_entries = period.get("new_entries", [])
            exits = period.get("exits", [])
            increased = period.get("increased", [])
            decreased = period.get("decreased", [])
            
            # Ana Başlık
            all_rows.append([f"DÖNEM: {start_date} --> {end_date}"])
            fmt_requests.append({
                "repeatCell": {
                    "range": {"sheetId": ws.id, "startRowIndex": current_row-1, "endRowIndex": current_row, "startColumnIndex": 0, "endColumnIndex": 10},
                    "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.55, "green": 0.20, "blue": 0.65}, "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}},
                    "fields": "userEnteredFormat(backgroundColor,textFormat)"
                }
            })
            current_row += 1
            all_rows.append([])
            current_row += 1
            
            # Yeni Girenler
            if new_entries:
                all_rows.append(["🆕 YENİ EKLENEN HİSSELER"])
                all_rows.append(["Tarih", "Tiker", "Şirket Adı", "Sektör", "Yeni Ağırlık (%)", "Piyasa Değeri (USD)", "Adet", "Fiyat (USD)"])
                fmt_requests.append({
                    "repeatCell": {
                        "range": {"sheetId": ws.id, "startRowIndex": current_row-1, "endRowIndex": current_row+1, "startColumnIndex": 0, "endColumnIndex": 8},
                        "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.07, "green": 0.53, "blue": 0.35}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}},
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                })
                current_row += 2
                
                for rec in new_entries:
                    all_rows.append([
                        end_date, rec.get("ticker", ""), rec.get("name", ""), rec.get("sector", ""),
                        rec.get("weight_pct", 0) / 100.0 if "weight_pct" in rec else rec.get("weight (%)", 0) / 100.0,
                        rec.get("market_value", 0), rec.get("quantity", 0), rec.get("price", 0)
                    ])
                    current_row += 1
                all_rows.append([])
                current_row += 1
                
            # Çıkanlar
            if exits:
                all_rows.append(["🚪 PORTFÖYDEN ÇIKARILAN HİSSELER"])
                all_rows.append(["Çıkarılma Tarihi", "Tiker", "Şirket Adı", "Sektör", "Eski Ağırlık (%)", "Eski Piyasa Değeri (USD)", "Eski Adet", "Eski Fiyat (USD)"])
                fmt_requests.append({
                    "repeatCell": {
                        "range": {"sheetId": ws.id, "startRowIndex": current_row-1, "endRowIndex": current_row+1, "startColumnIndex": 0, "endColumnIndex": 8},
                        "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.65, "green": 0.25, "blue": 0.10}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}},
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                })
                current_row += 2
                
                for rec in exits:
                    all_rows.append([
                        end_date, rec.get("ticker", ""), rec.get("name", ""), rec.get("sector", ""),
                        rec.get("weight_pct", 0) / 100.0 if "weight_pct" in rec else rec.get("weight (%)", 0) / 100.0,
                        rec.get("market_value", 0), rec.get("quantity", 0), rec.get("price", 0)
                    ])
                    current_row += 1
                all_rows.append([])
                current_row += 1
                
            # Ağırlığı Artanlar
            if increased:
                all_rows.append(["🚀 AĞIRLIĞI EN ÇOK ARTANLAR (İlk 10)"])
                all_rows.append(["Tarih", "Tiker", "Şirket Adı", "Sektör", "Önceki Ağırlık (%)", "Yeni Ağırlık (%)", "Değişim (pp)", "Oransal Değişim (%)"])
                fmt_requests.append({
                    "repeatCell": {
                        "range": {"sheetId": ws.id, "startRowIndex": current_row-1, "endRowIndex": current_row+1, "startColumnIndex": 0, "endColumnIndex": 8},
                        "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.07, "green": 0.53, "blue": 0.30}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}},
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                })
                current_row += 2
                
                for rec in increased[:10]:
                    all_rows.append([
                        end_date, rec.get("ticker", ""), rec.get("name", ""), rec.get("sector", ""),
                        rec.get("prev_weight", 0) / 100.0, rec.get("curr_weight", 0) / 100.0, rec.get("change_pp", 0), rec.get("change_pct", 0) / 100.0
                    ])
                    current_row += 1
                all_rows.append([])
                current_row += 1
                
            # Ağırlığı Azalanlar
            if decreased:
                all_rows.append(["📉 AĞIRLIĞI EN ÇOK AZALANLAR (İlk 10)"])
                all_rows.append(["Tarih", "Tiker", "Şirket Adı", "Sektör", "Önceki Ağırlık (%)", "Yeni Ağırlık (%)", "Değişim (pp)", "Oransal Değişim (%)"])
                fmt_requests.append({
                    "repeatCell": {
                        "range": {"sheetId": ws.id, "startRowIndex": current_row-1, "endRowIndex": current_row+1, "startColumnIndex": 0, "endColumnIndex": 8},
                        "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.70, "green": 0.15, "blue": 0.15}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}},
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                })
                current_row += 2
                
                for rec in decreased[:10]: # En dusen 10 tanesi rebalance_analyzer'dan sirali gelecek
                    all_rows.append([
                        end_date, rec.get("ticker", ""), rec.get("name", ""), rec.get("sector", ""),
                        rec.get("prev_weight", 0) / 100.0, rec.get("curr_weight", 0) / 100.0, rec.get("change_pp", 0), rec.get("change_pct", 0) / 100.0
                    ])
                    current_row += 1
                    
            all_rows.append([])
            all_rows.append([])
            current_row += 2
            
        if all_rows:
            if not append:
                ws.update(values=all_rows, range_name="A1", value_input_option='USER_ENTERED')
            else:
                ws.append_rows(all_rows, value_input_option='USER_ENTERED')
            
            # Yuzde formatlari
            fmt_requests.append({
                "repeatCell": {
                    "range": {"sheetId": ws.id, "startRowIndex": base_row, "endRowIndex": current_row, "startColumnIndex": 4, "endColumnIndex": 6},
                    "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}}},
                    "fields": "userEnteredFormat.numberFormat"
                }
            })
            fmt_requests.append({
                "repeatCell": {
                    "range": {"sheetId": ws.id, "startRowIndex": base_row, "endRowIndex": current_row, "startColumnIndex": 7, "endColumnIndex": 8},
                    "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}}},
                    "fields": "userEnteredFormat.numberFormat"
                }
            })
            
            try:
                self.spreadsheet.batch_update({"requests": fmt_requests})
            except Exception as e:
                logger.warning(f"Revisions sekmesi formatlanamadi: {e}")
                
            self._rate_limit()
            logger.info(f"  ✅ '{SHEET_NAMES['revisions']}': {len(periods_data)} dönem eklendi")

    def append_raw_data(self, df: pd.DataFrame):
        """📋 Ham Veri sekmesine tüm holdings satırlarını ekler."""
        ws = self._get_sheet("raw_data")
        if ws is None:
            return

        existing = ws.get_all_values()
        if not existing or len(existing) == 0 or len(existing[0]) == 0 or existing[0][0] != "as_of_date":
            # Başlıkları yaz
            headers = list(df.columns)
            ws.insert_row(headers, 1)
            ws.format("A1:P1", {
                "backgroundColor": {"red": 0.35, "green": 0.35, "blue": 0.35},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            })
            self._rate_limit()

        # Veri satırlarını ekle
        rows = df.values.tolist()
        # Sayısal None/NaN'ları boş string'e çevir
        clean_rows = []
        for row in rows:
            clean_rows.append([
                "" if (isinstance(v, float) and str(v) == "nan") else v
                for v in row
            ])

        if clean_rows:
            ws.append_rows(clean_rows)
            self._rate_limit()
            logger.info(f"  ✅ '{SHEET_NAMES['raw_data']}': {len(clean_rows)} satır eklendi")

    def write_all(self, curr_df: pd.DataFrame, analysis: dict, curr_date: date, prev_date: date):
        """Tüm sekmelere yazan ana metot."""
        logger.info(f"\n📝 Google Sheets yazılıyor ({curr_date})...")

        # 0. Kullanım Kılavuzu (README)
        self.write_readme_tab()
        
        # 0.1 Yatırım Stratejisi
        self.write_strategy_tab(analysis)

        # 1. Guncel Portfoy
        self.write_current_portfolio(curr_df, analysis)

        # 2. Değişim geçmişi (satır ekle)
        self.append_change_history(analysis)

        # 3. Pozisyon değişimleri
        self.append_position_changes(analysis, curr_date)

        # 4. Yeni girenler / çıkanlar
        self.append_new_entries_exits(analysis, curr_date, prev_date)

        # 5. Sektör analizi
        self.append_sector_analysis(analysis, curr_date)

        # 6. Ham veri
        self.append_raw_data(curr_df)
        
        # 7. Tarihsel Ağırlık Matrisi
        self.write_weight_matrix()
        
        # 8. Tarihsel Fiyat Matrisi
        self.write_price_matrix()
        
        # 9. Korelasyon Analizi
        self.write_correlation_analysis()
        
        # 10. Gelişmiş Sinyaller
        self.write_advanced_signals(analysis)
        
        # 11. Sektör Trendleri Matrisi
        self.write_sector_matrix()
        
        # 12. Yapay Zeka Özeti
        self.write_ai_summary(analysis, curr_date, prev_date)

        logger.info("✅ Tüm Google Sheets güncellemeleri tamamlandı!\n")

    def write_ai_summary(self, analysis: dict, curr_date: date, prev_date: date):
        """🤖 Yapay Zeka Özeti sekmesini günceller."""
        ws = self._get_sheet("ai_summary")
        if ws is None:
            return
            
        increased = analysis.get("increased", [])
        real_buys = [x for x in increased if "Gerçek Fon Alımı" in str(x.get("reason", ""))]
        price_effects = [x for x in increased if "Fiyat Etkisi" in str(x.get("reason", ""))]
        
        decreased = analysis.get("decreased", [])
        real_sells = [x for x in decreased if "Gerçek Fon Satışı" in str(x.get("reason", ""))]
        
        report = []
        report.append([f"Yapay Zeka Günlük Özeti ({curr_date.strftime('%Y-%m-%d')})"])
        report.append([f"Kıyaslanan Tarih: {prev_date.strftime('%Y-%m-%d')}"])
        
        # Endeks Getirisi
        etf_return = analysis.get("summary", {}).get("etf_daily_return_pct", 0.0)
        report.append([f"MSCI TUR Endeksi Günlük Performansı: %{etf_return:.2f}"])
        report.append([""])
        
        report.append(["🟢 GERÇEKTEN ALINAN (LOT ARTAN) HİSRELER"])
        if real_buys:
            for x in real_buys[:5]:
                report.append([f" - {x['ticker']}: Fon, elindeki lot miktarını arttırdı. Ağırlığı {x['prev_weight']}% -> {x['curr_weight']}% oldu."])
        else:
            report.append([" - Bugün fonda gerçek bir hisse alımı (adet artışı) tespit edilmedi."])
            
        report.append([""])
        report.append(["🔴 GERÇEKTEN SATILAN (LOT AZALAN) HİSRELER"])
        if real_sells:
            for x in real_sells[:5]:
                report.append([f" - {x['ticker']}: Fon, elindeki hisselerden satış yaptı. Ağırlığı {x['prev_weight']}% -> {x['curr_weight']}% düştü."])
        else:
            report.append([" - Bugün fonda gerçek bir hisse satışı tespit edilmedi."])
            
        report.append([""])
        report.append(["📈 SADECE FİYAT ARTIŞIYLA AĞIRLIĞI YÜKSELENLER"])
        if price_effects:
            for x in price_effects[:5]:
                report.append([f" - {x['ticker']}: Fon yeni hisse ALMADI. Ancak hisse fiyatı {x['price_change_pct']*100:.1f}% yükseldiği için portföy ağırlığı arttı."])
        else:
            report.append([" - Sadece fiyat etkisine bağlı bir ağırlık değişimi gözlemlenmedi."])
            
        # Sil ve yeniden yaz
        ws.clear()
        ws.update(values=report, range_name="A1")
        
        ws.format("A1:A1", {
            "backgroundColor": {"red": 0.1, "green": 0.6, "blue": 0.3},
            "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
        })
        ws.format("A4:A4", {"textFormat": {"bold": True, "foregroundColor": {"red": 0.1, "green": 0.5, "blue": 0.1}}})
        ws.format("A10:A10", {"textFormat": {"bold": True, "foregroundColor": {"red": 0.8, "green": 0.1, "blue": 0.1}}})
        
        self._rate_limit()
        logger.info(f"  ✅ '{SHEET_NAMES['ai_summary']}' güncellendi")

    def write_readme_tab(self):
        """📖 Kullanım Kılavuzu (README) sekmesini oluşturur."""
        ws = self._get_sheet("readme")
        if ws is None:
            return
            
        lines = []
        lines.append(["📖 TUR ETF YAPAY ZEKA PORTFÖY RADARI - KULLANIM KILAVUZU", "", ""])
        lines.append(["", "", ""])
        lines.append(["Bu tablo, BlackRock (iShares) MSCI Turkey ETF fonunun günlük gizli işlemlerini yapay zeka ve algoritmalarla analiz eder.", "", ""])
        lines.append(["Aşağıda her bir sekmenin ne işe yaradığı ve yatırımlarınızda nasıl kullanabileceğiniz açıklanmıştır:", "", ""])
        lines.append(["", "", ""])
        
        sections = [
            ("🎯 Gelişmiş Sinyaller", "Sistemin kalbidir. Fonun borsaya net para sokup sokmadığını (Net Dolar Akışı), 'Golden Cross' (Trend Başlangıcı) yapan hisseleri ve panik satışı/blok alım yapılan hisseleri (Anomali) burada görürsünüz."),
            ("📉 Korelasyon Analizi", "Fonun işlem mantığını (Algoritmasını) açıklar. BlackRock hangi hissede 'Dip Avcılığı' (düştükçe toplama) yapıyor, hangisinde 'Momentum' kovalıyor öğrenebilirsiniz."),
            ("📊 Sektör Trendleri", "Akıllı Paranın hangi sektörden çıkıp hangi sektöre girdiğini (Sektörel Rotasyon) mini grafiklerle gösterir. Yatırım sepetinizi kurarken en önemli kılavuzdur."),
            ("📅 Ağırlık Matrisi", "Her hissenin tüm geçmiş günlerde fon içerisindeki ağırlığını ve trendini izlemenizi sağlar."),
            ("💵 Fiyat Matrisi (USD)", "Hisselerin Dolar bazlı günlük fiyatlarını (ETF içerisindeki yansımasını) gösterir."),
            ("🤖 Yapay Zeka Özeti", "Her gün borsa kapanışı sonrası son 24 saatte olan tüm önemli olayların metin tabanlı (insan dilinde) özetini sunar."),
            ("🚀 Pozisyon Artışları", "Bir önceki güne göre fonun ağırlığını artırdığı hisselerin net listesidir."),
            ("📉 Pozisyon Düşüşleri", "Bir önceki güne göre fonun ağırlığını azalttığı veya tamamen sattığı hisselerin listesidir."),
            ("📊 Güncel Portföy", "Fonun o anki güncel durumunu, tam listeyi ve yüzdesel ağırlıkları gösterir."),
            ("📈 Değişim Geçmişi", "Son 2 gün arasındaki tüm hisse lot sayısı, fiyatı ve net değişiminin teknik tablosudur."),
            ("🏭 Sektör Analizi", "Sektörlerin dünden bugüne nasıl ağırlık değiştirdiğinin basit görünümüdür."),
            ("📋 Ham Veri", "BlackRock API'sinden çekilen doğrudan temizlenmiş ham veridir.")
        ]
        
        lines.append(["SEKME ADI", "NE İŞE YARAR / NASIL KULLANILIR?", ""])
        for title, desc in sections:
            lines.append([title, desc, ""])
            lines.append(["", "", ""])
            
        lines.append(["", "", ""])
        lines.append(["💡 STRATEJİ İPUCU:", "Eğer bir hisse 'Gelişmiş Sinyaller' sekmesinde Golden Cross yapmışsa ve 'Korelasyon Analizi' sekmesinde negatif korelasyona sahipse (dipten toplanıyorsa), bu harika bir potansiyel fırsattır.", ""])
        
        ws.clear()
        ws.update(values=lines, range_name="A1", value_input_option='USER_ENTERED')
        
        try:
            ws.format("A1:C1", {
                "backgroundColor": {"red": 0.1, "green": 0.5, "blue": 0.8},
                "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            ws.format("A6:B6", {
                "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            
            for i in range(7, 7 + len(sections)*2, 2):
                ws.format(f"A{i}:A{i}", {"textFormat": {"bold": True}})
                
            tip_row = len(lines) - 1
            ws.format(f"A{tip_row}:B{tip_row}", {
                "backgroundColor": {"red": 0.9, "green": 0.7, "blue": 0.1},
                "textFormat": {"bold": True, "foregroundColor": {"red": 0, "green": 0, "blue": 0}}
            })
            
            body = {
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 0,
                                "endIndex": 1
                            },
                            "properties": {"pixelSize": 250},
                            "fields": "pixelSize"
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 1,
                                "endIndex": 2
                            },
                            "properties": {"pixelSize": 800},
                            "fields": "pixelSize"
                        }
                    }
                ]
            }
            ws.spreadsheet.batch_update(body)
            
        except Exception as e:
            logger.warning(f"Readme formatlanamadi: {e}")
            
            self._rate_limit()
        logger.info(f"  ✅ '{SHEET_NAMES['readme']}' güncellendi")

    def write_strategy_tab(self, analysis: dict = None):
        """💡 Yatırım Stratejisi sekmesini oluşturur. Günlük verilere göre dinamik tavsiyeler üretir."""
        ws = self._get_sheet("strategy")
        if ws is None:
            return
            
        lines = []
        lines.append(["🚀 YZ TABANLI DİNAMİK ALPHA STRATEJİSİ", "", ""])
        lines.append(["", "", ""])
        lines.append(["Bu sayfa, TUR ETF verilerini günlük olarak analiz ederek, 'sabit stratejileri' güncel piyasa verileriyle birleştirir ve size o gün yapmanız gerekenleri otomatik olarak söyler.", "", ""])
        lines.append(["", "", ""])
        
        # Dinamik Veri Çıkarımı
        top_increased = []
        top_decreased = []
        new_entries = []
        golden_crosses = []
        sector_shifts = []
        
        if analysis:
            increased = analysis.get("increased", [])
            top_increased = [x["ticker"] for x in increased[:3]] if increased else []
            decreased = analysis.get("decreased", [])
            top_decreased = [x["ticker"] for x in decreased[:3]] if decreased else []
            
            entries = analysis.get("new_entries", [])
            new_entries = [x["ticker"] for x in entries] if entries else []
            
            signals = analysis.get("quant_signals", [])
            golden_crosses = [x["ticker"] for x in signals if x.get("signal") == "GOLDEN CROSS"] if signals else []
            
            sectors = analysis.get("sector_analysis", [])
            sectors = sorted(sectors, key=lambda x: x.get("change_pp", 0), reverse=True)
            if sectors:
                top_sector = sectors[0]["sector"]
                bottom_sector = sectors[-1]["sector"]
                sector_shifts = (top_sector, bottom_sector)
        
        # Dinamik Tavsiyeler Oluşturma
        s1_desc = "TUR ETF içinde 70 farklı hisse var. Hepsini alıp endeksin yavaşlığına mahkum olmayın.\n\n"
        s1_desc += "🎯 GÜNCEL AKSİYON: Bugün itibariyle BlackRock'ın en agresif alım yaptığı hisseler: "
        s1_desc += ", ".join(top_increased) if top_increased else "Şu an net bir alım trendi yok."
        if golden_crosses:
            s1_desc += f"\nAyrıca momentum olarak GOLDEN CROSS yakan hisseler: {', '.join(golden_crosses)}. Portföyünüzü sadece bu kazananlara odaklayın."
            
        s2_desc = "BlackRock panik satışlarında dipten hisse toplamayı sever. Medya kötümserken akıllı para mal toplar.\n\n"
        s2_desc += "🎯 GÜNCEL AKSİYON: Bugün itibariyle dev fonun gizli gizli topladığı, ancak henüz patlama yapmamış (ağırlığı sürekli artırılan) potansiyel dip hisseleri tespit edilip 'Pozisyon Artışları' sekmesine yansıdı. Özellikle "
        s2_desc += f"{top_increased[0] if top_increased else 'gözümüze çarpan'} hissesindeki kurumsal alım iştahını izleyin."
        
        s3_desc = "Trilyon dolarlık fonlar bir hisseye girecekleri zaman alımlarını haftalara bölerler.\n\n"
        if new_entries:
            s3_desc += f"🎯 GÜNCEL AKSİYON: ACİL! Bugün endekse yepyeni hisseler eklendi: {', '.join(new_entries)}. Fon mecburen haftalarca bu hisseleri almaya devam edecek. Balinanın yarattığı dalganın üzerine hemen sörf tahtanızı atın!"
        else:
            s3_desc += "🎯 GÜNCEL AKSİYON: Bugün endekse yeni eklenen taze bir kan (hisse) yok. Mevcut pozisyonlarınızı koruyun ve bir sonraki MSCI yeniden dengelenme (rebalancing) dönemini bekleyin."
            
        s4_desc = "Dev para bir sektörden çıkıp diğerine girdiğinde, o sektördeki tüm hisseler ralli yapar.\n\n"
        if sector_shifts:
            s4_desc += f"🎯 GÜNCEL AKSİYON: Akıllı para şu anda [{sector_shifts[1]}] sektöründen çıkıp agresif bir şekilde [{sector_shifts[0]}] sektörüne kayıyor! Portföyünüzdeki {sector_shifts[0]} ağırlığını ETF'in çok üzerine çıkararak (Overweight) devasa bir 'Alpha' yaratın."
        else:
            s4_desc += "🎯 GÜNCEL AKSİYON: Şu anda sektörler arası yatay bir seyir var. Net bir sektör rotasyonu tespit edilmedi."
            
        sections = [
            ("1. Sürüden Ayrıl (Selective Concentration)", s1_desc),
            ("2. Balina ile Dip Avı (Co-Investing on Dips)", s2_desc),
            ("3. Önceden Koşma (Front-Running)", s3_desc),
            ("4. Sektörel Rotasyon ile Çarpan Etkisi", s4_desc)
        ]
        
        lines.append(["ADIM", "STRATEJİ AÇIKLAMASI VE UYGULAMASI", ""])
        for title, desc in sections:
            lines.append([title, desc, ""])
            lines.append(["", "", ""])
            
        lines.append(["", "", ""])
        lines.append(["ÖZET FORMÜL:", "Alpha (Ekstra Getiri) = Sadece Golden Cross Hisseleri + Yabancıyla Dipten Toplama + Yükselen Sektöre Agresif Odaklanma", ""])
        
        ws.clear()
        ws.update(values=lines, range_name="A1", value_input_option='USER_ENTERED')
        
        try:
            ws.format("A1:C1", {
                "backgroundColor": {"red": 0.9, "green": 0.7, "blue": 0.1},
                "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 0, "green": 0, "blue": 0}}
            })
            ws.format("A6:B6", {
                "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            
            for i in range(7, 7 + len(sections)*2, 2):
                ws.format(f"A{i}:A{i}", {"textFormat": {"bold": True}})
                # Wrap text for long descriptions
                ws.format(f"B{i}:B{i}", {"wrapStrategy": "WRAP"})
                
            tip_row = len(lines) - 1
            ws.format(f"A{tip_row}:B{tip_row}", {
                "backgroundColor": {"red": 0.1, "green": 0.5, "blue": 0.8},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            
            body = {
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 0,
                                "endIndex": 1
                            },
                            "properties": {"pixelSize": 280},
                            "fields": "pixelSize"
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 1,
                                "endIndex": 2
                            },
                            "properties": {"pixelSize": 800},
                            "fields": "pixelSize"
                        }
                    }
                ]
            }
            ws.spreadsheet.batch_update(body)
            
        except Exception as e:
            logger.warning(f"Strateji sekmesi formatlanamadi: {e}")
            
        self._rate_limit()
        logger.info(f"  ✅ '{SHEET_NAMES['strategy']}' güncellendi")

    def write_advanced_signals(self, analysis: dict):
        """🎯 Gelişmiş Sinyaller sekmesini günceller."""
        ws = self._get_sheet("advanced_signals")
        if ws is None:
            return
            
        summary = analysis.get("summary", {})
        fund_flow = summary.get("total_fund_flow_usd", 0.0)
        
        # Sinyalleri çek (dict'te varsa). Eğer yoksa boş liste.
        # Not: analyzer JSON export'u sırasında quant_signals'i eklememiz gerekiyor.
        # Ancak analyzer dict yapısına henüz eklemediğimiz için manuel olarak bu adımı atlayıp,
        # doğrudan analyzer objesinden almıyorsak bir hata olabilir.
        # Bunun yerine JSON verisinden alıyoruz:
        signals = analysis.get("quant_signals", [])
        
        # Başlık ve Net Nakit Akışı
        flow_status = "🟢 POZİTİF (Para Girişi)" if fund_flow > 0 else "🔴 NEGATİF (Para Çıkışı)" if fund_flow < 0 else "⚪ NÖTR"
        
        lines = []
        lines.append(["📊 QUANT ENGINE - GÜNLÜK PİYASA RADARI", ""])
        lines.append(["", ""])
        lines.append(["🌊 GÜNLÜK NET FON AKIŞI (USD):", f"${fund_flow:,.2f}"])
        lines.append(["Yabancı Fon Durumu:", flow_status])
        lines.append(["", ""])
        lines.append(["🎯 OTOMATİK ALGORİTMA SİNYALLERİ (SMA-20 & Anomaliler)", ""])
        lines.append(["Tiker", "📈 Fiyat Trendi", "Şirket", "Sinyal Türü", "Açıklama"])
        
        if not signals:
            lines.append(["", "", "Sinyal Yok", "Bugün herhangi bir Golden Cross, Death Cross veya Anomali tespit edilmedi.", ""])
        else:
            base_idx = len(lines) + 1
            for i, s in enumerate(signals):
                row_idx = base_idx + i
                sparkline_formula = f'=IFNA(SPARKLINE(INDEX(\'💵 Fiyat Matrisi (USD)\'!E:ZZ; MATCH(A{row_idx}; \'💵 Fiyat Matrisi (USD)\'!A:A; 0))); "")'
                lines.append([s.get("ticker", ""), sparkline_formula, s.get("name", ""), s.get("signal_type", ""), s.get("description", "")])
                
        ws.clear()
        ws.update(values=lines, range_name="A1", value_input_option='USER_ENTERED')
        
        try:
            ws.format("A1:E1", {
                "backgroundColor": {"red": 0.8, "green": 0.1, "blue": 0.4},
                "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            ws.format("A3:A4", {"textFormat": {"bold": True}})
            ws.format("A7:E7", {
                "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            
            self.spreadsheet.batch_update({
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 1, # Trend
                                "endIndex": 2,
                            },
                            "properties": {"pixelSize": 180},
                            "fields": "pixelSize",
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "ROWS",
                                "startIndex": 7,
                                "endIndex": len(lines),
                            },
                            "properties": {"pixelSize": 45},
                            "fields": "pixelSize",
                        }
                    }
                ]
            })
        except Exception as e:
            logger.warning(f"Sinyal formatlanamadi: {e}")
            
        self._rate_limit()
        logger.info(f"  ✅ '{SHEET_NAMES['advanced_signals']}' güncellendi")

    def write_correlation_analysis(self, snapshot_dir: str = "data/snapshots"):
        """📉 Korelasyon Analizi sekmesini günceller."""
        ws = self._get_sheet("correlation_analysis")
        if ws is None:
            return
            
        from pathlib import Path
        import math
        
        path = Path(snapshot_dir)
        if not path.exists():
            return
            
        all_dfs = []
        for f in sorted(path.glob("*.csv")):
            try:
                date_str = f.stem
                try:
                    d_obj = datetime.strptime(date_str, "%Y%m%d").date()
                except ValueError:
                    continue
                    
                df = pd.read_csv(f)
                df.columns = [c.lower().strip() for c in df.columns]
                
                if "price" not in df.columns or "quantity" not in df.columns:
                    continue
                    
                df["price_val"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
                df["qty_val"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0.0)
                
                if "weight (%)" in df.columns:
                    df["weight_pct"] = pd.to_numeric(df["weight (%)"], errors="coerce") / 100.0
                elif "weight_pct" in df.columns:
                    df["weight_pct"] = pd.to_numeric(df["weight_pct"], errors="coerce") / 100.0
                else:
                    continue
                    
                df["weight_pct"] = df["weight_pct"].fillna(0.0)
                
                temp = df[["ticker", "name", "price_val", "qty_val", "weight_pct"]].copy()
                temp["date"] = d_obj
                
                temp = temp.drop_duplicates(subset=["ticker"]).dropna(subset=["ticker"])
                all_dfs.append(temp)
            except Exception as e:
                logger.error(f"Korelasyon verisi okuma hatasi {f.name}: {e}")
                
        if not all_dfs:
            return
            
        master_df = pd.concat(all_dfs, ignore_index=True)
        
        # Sadece son gunun top 20 hissesini alalim
        latest_date = master_df["date"].max()
        latest_df = master_df[master_df["date"] == latest_date].sort_values("weight_pct", ascending=False)
        top_tickers = latest_df["ticker"].head(20).tolist()
        
        analysis_data = master_df[master_df["ticker"].isin(top_tickers)].copy()
        analysis_data = analysis_data.sort_values(["ticker", "date"])
        
        analysis_data["prev_qty"] = analysis_data.groupby("ticker")["qty_val"].shift(1)
        analysis_data["prev_price"] = analysis_data.groupby("ticker")["price_val"].shift(1)
        
        analysis_data["qty_change_pct"] = (analysis_data["qty_val"] / analysis_data["prev_qty"] - 1.0)
        analysis_data["price_change_pct"] = (analysis_data["price_val"] / analysis_data["prev_price"] - 1.0)
        
        analysis_data = analysis_data.dropna(subset=["qty_change_pct", "price_change_pct"])
        
        # Calculate correlations
        lines = []
        lines.append(["📉 BLACKROCK İŞLEM MANTIĞI VE KORELASYON ANALİZİ", "", "", ""])
        lines.append(["", "", "", ""])
        
        # Genel Korelasyon
        overall_corr = analysis_data["qty_change_pct"].corr(analysis_data["price_change_pct"])
        
        lines.append(["GENEL FON MANTIĞI", "Korelasyon Skoru", "Yorum", ""])
        if overall_corr < 0:
            yorum = "Fon, fiyat düştükçe alım yapıyor (Value Investing / Dip Avcısı)."
        else:
            yorum = "Fon, fiyat yükseldikçe alım yapıyor (Momentum / Trend Takibi)."
            
        lines.append(["Lot Alımı ile Fiyat Artışı", f"{overall_corr:.3f}", yorum, ""])
        lines.append(["", "", "", ""])
        
        lines.append(["İLK 20 HİSSE BAZINDA KORELASYONLAR", "", "", ""])
        lines.append(["Tiker", "Şirket", "Alım/Fiyat Korelasyonu", "Analiz Yorumu"])
        
        for ticker in top_tickers:
            t_df = analysis_data[analysis_data["ticker"] == ticker]
            if len(t_df) > 5:
                corr = t_df["qty_change_pct"].corr(t_df["price_change_pct"])
                
                if math.isnan(corr):
                    corr_str = "N/A"
                    yorum_str = "Yeterli veri veya dalgalanma yok."
                else:
                    corr_str = f"{corr:.3f}"
                    if corr < -0.5:
                        yorum_str = "Fiyat düştüğünde GÜÇLÜ ALIM yapıyor."
                    elif corr < -0.1:
                        yorum_str = "Fiyat düştüğünde ALIM eğilimi var."
                    elif corr > 0.5:
                        yorum_str = "Fiyat yükseldiğinde GÜÇLÜ ALIM yapıyor."
                    elif corr > 0.1:
                        yorum_str = "Fiyat yükseldiğinde ALIM eğilimi var."
                    else:
                        yorum_str = "Belirgin bir işlem mantığı (korelasyon) yok."
                        
                name = latest_df[latest_df["ticker"] == ticker].iloc[0]["name"]
                lines.append([ticker, name, corr_str, yorum_str])
                
        ws.clear()
        ws.update(values=lines, range_name="A1", value_input_option='USER_ENTERED')
        
        try:
            ws.format("A1:D1", {
                "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.6},
                "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            ws.format("A4:C4", {
                "backgroundColor": {"red": 0.3, "green": 0.3, "blue": 0.3},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            ws.format("A8:D8", {
                "backgroundColor": {"red": 0.3, "green": 0.3, "blue": 0.3},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
        except Exception as e:
            logger.warning(f"Korelasyon formatlanamadi: {e}")
            
        self._rate_limit()
        logger.info(f"  ✅ '{SHEET_NAMES['correlation_analysis']}' güncellendi")

    def write_sector_matrix(self, snapshot_dir: str = "data/snapshots"):
        """📊 Sektör Trendleri sekmesini günceller."""
        ws = self._get_sheet("sector_matrix")
        if ws is None:
            return
            
        from analyzer import build_historical_sector_matrix
        import math
        
        pivot_df = build_historical_sector_matrix(snapshot_dir)
        if pivot_df is None or pivot_df.empty:
            return
            
        # Sektor sutununu index'ten cikarip listeye alalim
        pivot_df.index.name = "Sektör"
        pivot_df = pivot_df.reset_index()
        
        # Sort by the latest date's weight (descending) to show biggest sectors first
        latest_date_col = pivot_df.columns[-1]
        pivot_df = pivot_df.sort_values(latest_date_col, ascending=False)
        
        headers = list(pivot_df.columns)
        headers.insert(1, "📈 Sektörel Trend")
        headers.insert(2, "📊 Rotasyon (Son 1 Gün % Değişim)")
        raw_rows = pivot_df.values.tolist()
        
        num_cols = len(headers)
        
        def col_name(n):
            s = ""
            while n > 0:
                n, remainder = divmod(n - 1, 26)
                s = chr(65 + remainder) + s
            return s
            
        end_col = col_name(num_cols)
        
        rows = []
        for i, row in enumerate(raw_rows):
            clean_row = [0.0 if (isinstance(x, float) and math.isnan(x)) else x for x in row]
            
            # % Change between last 2 available dates
            if len(clean_row) >= 4:
                prev_weight = float(clean_row[-2])
                curr_weight = float(clean_row[-1])
                change_pct = (curr_weight / prev_weight - 1.0) if prev_weight > 0 else 0.0
            else:
                change_pct = 0.0
                
            row_num = i + 2
            # Data dates start at column D (4th column)
            formula = f'=SPARKLINE(D{row_num}:{end_col}{row_num})'
            
            clean_row.insert(1, formula)
            clean_row.insert(2, change_pct)
            
            rows.append(clean_row)
            
        ws.clear()
        ws.update(values=[headers] + rows, range_name="A1", value_input_option='USER_ENTERED')
        
        try:
            # Format numbers as PERCENT
            ws.format(f"C2:{end_col}", {
                "numberFormat": {
                    "type": "PERCENT",
                    "pattern": "0.00%"
                }
            })
            # Header format
            ws.format(f"A1:{end_col}1", {
                "backgroundColor": {"red": 0.5, "green": 0.3, "blue": 0.8},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            
            # Otomatik hucre buyutme
            body = {
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 1,
                                "endIndex": 2
                            },
                            "properties": {"pixelSize": 180},
                            "fields": "pixelSize"
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 3,
                                "endIndex": num_cols
                            },
                            "properties": {"pixelSize": 70},
                            "fields": "pixelSize"
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "ROWS",
                                "startIndex": 1,
                                "endIndex": len(rows) + 1
                            },
                            "properties": {"pixelSize": 45},
                            "fields": "pixelSize"
                        }
                    }
                ]
            }
            ws.spreadsheet.batch_update(body)
            
        except Exception as e:
            logger.warning(f"Sektor matrisi formatlanamadi: {e}")
            
        self._rate_limit()
        logger.info(f"  ✅ '{SHEET_NAMES['sector_matrix']}' güncellendi")

    def write_weight_matrix(self, snapshot_dir: str = "data/snapshots"):
        """📅 Ağırlık Matrisi sekmesini günceller. Tüm tarihleri kapsayan bir pivot tablo oluşturur."""
        ws = self._get_sheet("weight_matrix")
        if ws is None:
            return

        from pathlib import Path
        import math
        
        path = Path(snapshot_dir)
        if not path.exists():
            return
            
        all_dfs = []
        for f in sorted(path.glob("*.csv")):
            try:
                date_str = f.stem
                try:
                    d_obj = datetime.strptime(date_str, "%Y%m%d").date()
                except ValueError:
                    continue
                    
                df = pd.read_csv(f)
                df.columns = [c.lower().strip() for c in df.columns]
                
                if "weight (%)" in df.columns:
                    df["weight_pct"] = pd.to_numeric(df["weight (%)"], errors="coerce") / 100.0
                elif "weight_pct" in df.columns:
                    # BlackRock's weight_pct is typically "11.71" which means 11.71%
                    df["weight_pct"] = pd.to_numeric(df["weight_pct"], errors="coerce") / 100.0
                    
                if "weight_pct" not in df.columns:
                    continue
                    
                df["weight_pct"] = df["weight_pct"].fillna(0.0)
                
                temp = df[["ticker", "name", "weight_pct"]].copy()
                temp["date"] = str(d_obj)
                
                # Temizle
                temp = temp.drop_duplicates(subset=["ticker"]).dropna(subset=["ticker"])
                all_dfs.append(temp)
            except Exception as e:
                logger.error(f"Matrix okuma hatasi {f.name}: {e}")
                
        if not all_dfs:
            return
            
        master_df = pd.concat(all_dfs, ignore_index=True)
        
        # Şirket isimlerindeki geçmişe dönük ufak değişikliklerin matrisi ikiye bölmesini engellemek için
        # Her hissenin ismini, o hissenin en son görüldüğü isme eşitliyoruz
        name_map = master_df.groupby("ticker")["name"].last().to_dict()
        master_df["name"] = master_df["ticker"].map(name_map)
        
        # Pivot
        pivot_df = master_df.pivot(index=["ticker", "name"], columns="date", values="weight_pct").fillna(0.0)
        
        # Sütunları tarihe göre sırala
        pivot_df = pivot_df[sorted(pivot_df.columns)]
        
        pivot_df = pivot_df.reset_index()
        
        headers = list(pivot_df.columns)
        headers.insert(2, "📈 Trend")
        headers.insert(3, "📊 Son Oransal Değişim (%)")
        raw_rows = pivot_df.values.tolist()
        
        num_cols = len(headers)
        
        def col_name(n):
            s = ""
            while n > 0:
                n, remainder = divmod(n - 1, 26)
                s = chr(65 + remainder) + s
            return s
            
        end_col = col_name(num_cols)
        
        # Clean NaNs and insert Sparklines + Proportional Change
        rows = []
        for i, row in enumerate(raw_rows):
            clean_row = [0.0 if (isinstance(x, float) and math.isnan(x)) else x for x in row]
            
            # Calculate % change between the last two available dates
            if len(clean_row) >= 4:
                prev_weight = float(clean_row[-2])
                curr_weight = float(clean_row[-1])
                change_pct = (curr_weight / prev_weight - 1.0) if prev_weight > 0 else 0.0
            else:
                change_pct = 0.0
                
            row_num = i + 2
            # The data dates start at column E (5th column)
            formula = f'=SPARKLINE(E{row_num}:{end_col}{row_num})'
            
            clean_row.insert(2, formula)
            clean_row.insert(3, change_pct)
            
            rows.append(clean_row)
        
        ws.clear()
        ws.update(values=[headers] + rows, range_name="A1", value_input_option='USER_ENTERED')
        
        try:
            ws.format(f"D2:{end_col}", {
                "numberFormat": {
                    "type": "PERCENT",
                    "pattern": "0.00%"
                }
            })
            ws.format(f"A1:{end_col}1", {
                "backgroundColor": {"red": 0.8, "green": 0.4, "blue": 0.2},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            
            # Otomatik hucre buyutme (Sparkline'lar icin)
            body = {
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "ROWS",
                                "startIndex": 1,
                                "endIndex": len(rows) + 1
                            },
                            "properties": {"pixelSize": 45},
                            "fields": "pixelSize"
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 2,
                                "endIndex": 3
                            },
                            "properties": {"pixelSize": 180},
                            "fields": "pixelSize"
                        }
                    }
                ]
            }
            ws.spreadsheet.batch_update(body)
            
        except Exception as e:
            logger.warning(f"Formatlanamadi: {e}")
            
        self._rate_limit()
        logger.info(f"  ✅ '{SHEET_NAMES['weight_matrix']}' güncellendi")

    def write_price_matrix(self, snapshot_dir: str = "data/snapshots"):
        """💵 Fiyat Matrisi (USD) sekmesini günceller. Tüm tarihleri kapsayan bir pivot tablo oluşturur."""
        ws = self._get_sheet("price_matrix")
        if ws is None:
            return

        from pathlib import Path
        import math
        
        path = Path(snapshot_dir)
        if not path.exists():
            return
            
        all_dfs = []
        for f in sorted(path.glob("*.csv")):
            try:
                date_str = f.stem
                try:
                    d_obj = datetime.strptime(date_str, "%Y%m%d").date()
                except ValueError:
                    continue
                    
                df = pd.read_csv(f)
                df.columns = [c.lower().strip() for c in df.columns]
                
                if "price" not in df.columns:
                    continue
                    
                df["price_val"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
                
                temp = df[["ticker", "name", "price_val"]].copy()
                temp["date"] = str(d_obj)
                
                # Temizle
                temp = temp.drop_duplicates(subset=["ticker"]).dropna(subset=["ticker"])
                all_dfs.append(temp)
            except Exception as e:
                logger.error(f"Fiyat Matrix okuma hatasi {f.name}: {e}")
                
        if not all_dfs:
            return
            
        master_df = pd.concat(all_dfs, ignore_index=True)
        
        # Şirket isimlerindeki geçmişe dönük ufak değişikliklerin matrisi ikiye bölmesini engellemek için
        # Her hissenin ismini, o hissenin en son görüldüğü isme eşitliyoruz
        name_map = master_df.groupby("ticker")["name"].last().to_dict()
        master_df["name"] = master_df["ticker"].map(name_map)
        
        # Pivot
        pivot_df = master_df.pivot(index=["ticker", "name"], columns="date", values="price_val").fillna(0.0)
        
        # Sütunları tarihe göre sırala
        pivot_df = pivot_df[sorted(pivot_df.columns)]
        pivot_df = pivot_df.reset_index()
        
        headers = list(pivot_df.columns)
        headers.insert(2, "📈 Fiyat Trendi")
        headers.insert(3, "📊 Son Fiyat Değişimi (%)")
        raw_rows = pivot_df.values.tolist()
        
        num_cols = len(headers)
        
        def col_name(n):
            s = ""
            while n > 0:
                n, remainder = divmod(n - 1, 26)
                s = chr(65 + remainder) + s
            return s
            
        end_col = col_name(num_cols)
        
        # Clean NaNs and insert Sparklines + Proportional Change
        rows = []
        for i, row in enumerate(raw_rows):
            clean_row = [0.0 if (isinstance(x, float) and math.isnan(x)) else x for x in row]
            
            if len(clean_row) >= 4:
                prev_price = float(clean_row[-2])
                curr_price = float(clean_row[-1])
                change_pct = (curr_price / prev_price - 1.0) if prev_price > 0 else 0.0
            else:
                change_pct = 0.0
                
            row_num = i + 2
            # The data dates start at column E (5th column)
            formula = f'=SPARKLINE(E{row_num}:{end_col}{row_num})'
            
            clean_row.insert(2, formula)
            clean_row.insert(3, change_pct)
            
            rows.append(clean_row)
        
        ws.clear()
        ws.update(values=[headers] + rows, range_name="A1", value_input_option='USER_ENTERED')
        
        try:
            ws.format(f"E2:{end_col}", {
                "numberFormat": {
                    "type": "CURRENCY",
                    "pattern": "\"$\"#,##0.00"
                }
            })
            ws.format(f"D2:D", {
                "numberFormat": {
                    "type": "PERCENT",
                    "pattern": "0.00%"
                }
            })
            ws.format(f"A1:{end_col}1", {
                "backgroundColor": {"red": 0.85, "green": 0.65, "blue": 0.13},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            
            # Otomatik hucre buyutme
            body = {
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "ROWS",
                                "startIndex": 1,
                                "endIndex": len(rows) + 1
                            },
                            "properties": {"pixelSize": 45},
                            "fields": "pixelSize"
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 2,
                                "endIndex": 3
                            },
                            "properties": {"pixelSize": 180},
                            "fields": "pixelSize"
                        }
                    }
                ]
            }
            ws.spreadsheet.batch_update(body)
            
        except Exception as e:
            logger.warning(f"Formatlanamadi: {e}")
            
        self._rate_limit()
        logger.info(f"  ✅ '{SHEET_NAMES['price_matrix']}' güncellendi")

    def write_benchmark_comparison(self, df: pd.DataFrame):
        """⚖️ BIST100 vs TUR ETF Karşılaştırma sekmesini günceller."""
        ws = self._get_sheet("benchmark")
        if ws is None:
            return

        # Sütunları hazırla
        # df beklenen sütunlar: Date, TUR, XU100.IS, TRY=X, BIST100_USD, TUR_Return, BIST_Return, Alpha
        headers = [
            "Tarih",
            "TUR ETF (USD)",
            "BIST 100 (TRY)",
            "USD/TRY Kuru",
            "BIST 100 (USD)",
            "📊 TUR ETF Kümülatif Getiri",
            "📊 BIST 100 (USD) Kümülatif Getiri",
            "🔥 ALPHA (Fark)"
        ]
        
        rows = [headers]
        for _, row in df.iterrows():
            alpha = row.get("Alpha", 0)
            rows.append([
                row.get("Date", ""),
                row.get("TUR", 0),
                row.get("XU100.IS", 0),
                row.get("TRY=X", 0),
                row.get("BIST100_USD", 0),
                row.get("TUR_Return", 0),
                row.get("BIST_Return", 0),
                alpha
            ])
            
        ws.clear()
        ws.update(values=rows, range_name="A1", value_input_option='USER_ENTERED')
        
        try:
            # Fiyat formatlamaları
            ws.format("B2:E", {
                "numberFormat": {
                    "type": "NUMBER",
                    "pattern": "#,##0.00"
                }
            })
            
            # Yüzde formatlamaları (Getiriler ve Alfa)
            ws.format("F2:H", {
                "numberFormat": {
                    "type": "PERCENT",
                    "pattern": "0.00%"
                }
            })
            
            # Başlık
            ws.format("A1:H1", {
                "backgroundColor": {"red": 0.15, "green": 0.45, "blue": 0.85},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            })
            
            # Koşullu biçimlendirme (Alfa için)
            body = {
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 5,
                                "endIndex": 8
                            },
                            "properties": {"pixelSize": 180},
                            "fields": "pixelSize"
                        }
                    }
                ]
            }
            ws.spreadsheet.batch_update(body)
            
        except Exception as e:
            logger.warning(f"Benchmark sekmesi formatlanamadı: {e}")
            
        self._rate_limit()
        logger.info(f"  ✅ '{SHEET_NAMES['benchmark']}' güncellendi")

    def write_trade_performance(self, trades: list):
        """⏳ Pozisyon Getirileri sekmesini günceller."""
        ws = self._get_sheet("trades")
        if ws is None or not trades:
            return

        headers = [
            "Tiker", "Şirket Adı", "Durum", 
            "Fona Giriş Tarihi", "Giriş Fiyatı (USD)", 
            "Fondan Çıkış Tarihi", "Çıkış Fiyatı (USD)", 
            "Net Getiri (USD Bazlı)", "Elde Tutma Süresi (Gün)"
        ]
        
        rows = [headers]
        for t in trades:
            rows.append([
                t.get("ticker", ""),
                t.get("name", ""),
                t.get("status", ""),
                t.get("entry_date", ""),
                t.get("entry_price", 0),
                t.get("exit_date", ""),
                t.get("exit_price", 0),
                t.get("return_pct", 0),
                t.get("days_held", 0)
            ])
            
        ws.clear()
        ws.update(values=rows, range_name="A1", value_input_option='USER_ENTERED')
        
        try:
            # Fiyat formatı (E ve G sütunları)
            ws.format("E2:E", {
                "numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}
            })
            ws.format("G2:G", {
                "numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}
            })
            
            # Yüzde formatı (H sütunu)
            ws.format("H2:H", {
                "numberFormat": {"type": "PERCENT", "pattern": "0.00%"}
            })
            
            # Başlık
            ws.format("A1:I1", {
                "backgroundColor": {"red": 0.80, "green": 0.60, "blue": 0.10},
                "textFormat": {"bold": True, "foregroundColor": {"red": 0, "green": 0, "blue": 0}}
            })
            
            # Koşullu biçimlendirme - Durum Sütunu (Aktif vs Kapalı)
            ws.format("C2:C", {"horizontalAlignment": "CENTER"})
            
            # Otomatik kolon ayarı
            body = {
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 1,
                                "endIndex": 2
                            },
                            "properties": {"pixelSize": 180},
                            "fields": "pixelSize"
                        }
                    },
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 3,
                                "endIndex": 7
                            },
                            "properties": {"pixelSize": 120},
                            "fields": "pixelSize"
                        }
                    }
                ]
            }
            ws.spreadsheet.batch_update(body)
            
        except Exception as e:
            logger.warning(f"Pozisyon Getirileri formatlanamadı: {e}")
            
        self._rate_limit()
        logger.info(f"  ✅ '{SHEET_NAMES['trades']}' güncellendi")
