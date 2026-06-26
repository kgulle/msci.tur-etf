import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sheets_writer import SheetsWriter
from analyzer import compare_snapshots

load_dotenv()

def run_periodic_analysis():
    sheets_id = os.getenv("GOOGLE_SHEETS_ID", "1tg5OBvX_ohCrxdiz_2JvtQxTPKmE-hNW27C2WGxH7n0")
    service_account = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")

    writer = SheetsWriter(sheets_id, service_account)
    writer.connect()
    writer.setup_sheets()

    target_dates = ["20251231", "20260331", "20260529", "20260624"]
    periods_data = []

    for i in range(1, len(target_dates)):
        prev_date_str = target_dates[i-1]
        curr_date_str = target_dates[i]
        
        prev_file = os.path.join("data/snapshots", f"{prev_date_str}.csv")
        curr_file = os.path.join("data/snapshots", f"{curr_date_str}.csv")
        
        if not os.path.exists(prev_file) or not os.path.exists(curr_file):
            print(f"Eksik dosya: {prev_file} veya {curr_file}")
            continue

        prev_date = datetime.strptime(prev_date_str, "%Y%m%d").date()
        curr_date = datetime.strptime(curr_date_str, "%Y%m%d").date()
        
        prev_df = pd.read_csv(prev_file)
        curr_df = pd.read_csv(curr_file)
        
        analysis = compare_snapshots(prev_df, curr_df, prev_date, curr_date)
        
        if analysis and analysis.has_changes:
            analysis_dict = analysis.to_dict()
            analysis_dict["start_date"] = str(prev_date)
            analysis_dict["end_date"] = str(curr_date)
            
            # En cok artan ve azalanlari sıralama
            analysis_dict["increased"] = sorted(analysis_dict.get("increased", []), key=lambda x: x["change_pp"], reverse=True)
            analysis_dict["decreased"] = sorted(analysis_dict.get("decreased", []), key=lambda x: x["change_pp"]) # En cok dusenden en aza
            
            periods_data.append(analysis_dict)

    if periods_data:
        writer.write_periodic_revisions(periods_data)
        print("Donemsel revizyon analizi Google Sheets'e basariyla yazildi!")
    else:
        print("İncelenen tarihler arasında yeterli değişim bulunamadı.")

if __name__ == "__main__":
    run_periodic_analysis()
