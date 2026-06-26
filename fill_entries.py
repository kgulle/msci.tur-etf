import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sheets_writer import SheetsWriter
from analyzer import compare_snapshots

load_dotenv()

sheets_id = os.getenv("GOOGLE_SHEETS_ID", "1tg5OBvX_ohCrxdiz_2JvtQxTPKmE-hNW27C2WGxH7n0")
service_account = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")

writer = SheetsWriter(sheets_id, service_account)
writer.connect()

# Get all snapshot files chronologically
files = sorted([f for f in os.listdir("data/snapshots") if f.endswith(".csv")])

print(f"Total files: {len(files)}")

for i in range(1, len(files)):
    prev_file = files[i-1]
    curr_file = files[i]
    
    prev_date = datetime.strptime(prev_file.replace(".csv", ""), "%Y%m%d").date()
    curr_date = datetime.strptime(curr_file.replace(".csv", ""), "%Y%m%d").date()
    
    prev_df = pd.read_csv(os.path.join("data/snapshots", prev_file))
    curr_df = pd.read_csv(os.path.join("data/snapshots", curr_file))
    
    analysis = compare_snapshots(prev_df, curr_df, prev_date, curr_date)
    
    if analysis and analysis.has_changes:
        analysis_dict = analysis.to_dict()
        if analysis_dict.get("new_entries") or analysis_dict.get("exits"):
            print(f"{curr_date}: {len(analysis_dict.get('new_entries', []))} entries, {len(analysis_dict.get('exits', []))} exits")
            writer.append_new_entries_exits(analysis_dict, curr_date, prev_date)

print("Done!")
