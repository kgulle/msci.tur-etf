import sys
import os
import pandas as pd
from datetime import datetime
from pathlib import Path
sys.path.insert(0, 'src')
from fetcher import get_available_snapshots, load_snapshot
from analyzer import compare_snapshots, build_historical_weight_matrix

dates = get_available_snapshots("data/snapshots")
if len(dates) < 2:
    print("Not enough data")
    sys.exit()

prev_date = dates[-2]
curr_date = dates[-1]

prev_df = load_snapshot(prev_date, "data/snapshots")
curr_df = load_snapshot(curr_date, "data/snapshots")

# Load historical matrix
pivot_df = build_historical_weight_matrix("data/snapshots")

quant_signals = []
total_fund_flow = 0.0

# Calculate fund flow
for _, row in curr_df.iterrows():
    ticker = row["ticker"]
    curr_qty = float(row.get("quantity", 0))
    curr_price = float(row.get("price", 0))
    
    prev_rows = prev_df[prev_df["ticker"] == ticker]
    if not prev_rows.empty:
        prev_qty = float(prev_rows.iloc[0].get("quantity", 0))
    else:
        prev_qty = 0.0
        
    qty_change = curr_qty - prev_qty
    flow_usd = qty_change * curr_price
    total_fund_flow += flow_usd
    
    # Anomaly
    if prev_qty > 0 and abs(qty_change) / prev_qty > 0.05: # 5% change in quantity is an anomaly
        quant_signals.append({
            "ticker": ticker,
            "name": row["name"],
            "signal_type": "🚨 ANOMALİ (Blok İşlem)",
            "description": f"Hisse adedi %{round(qty_change/prev_qty*100, 1)} değişti!"
        })
    elif prev_qty == 0 and curr_qty > 0:
        quant_signals.append({
            "ticker": ticker,
            "name": row["name"],
            "signal_type": "🆕 YENİ GİRİŞ",
            "description": "Fona yeni eklendi."
        })

# Golden cross
# Get last 20 columns from pivot_df
date_cols = [c for c in pivot_df.columns if c not in ["ticker", "name"]]
date_cols.sort()
if len(date_cols) >= 20:
    last_20 = date_cols[-20:]
    last_19 = date_cols[-21:-1] # Prev day 20-day window
    for _, row in pivot_df.iterrows():
        ticker = row["ticker"]
        curr_w = row[date_cols[-1]]
        prev_w = row[date_cols[-2]]
        
        sma20_curr = row[last_20].mean()
        sma20_prev = row[last_19].mean()
        
        if curr_w > sma20_curr and prev_w <= sma20_prev:
            quant_signals.append({
                "ticker": ticker,
                "name": row["name"],
                "signal_type": "🟢 GOLDEN CROSS",
                "description": "Ağırlık 20 günlük ortalamayı yukarı kesti."
            })
        elif curr_w < sma20_curr and prev_w >= sma20_prev:
            quant_signals.append({
                "ticker": ticker,
                "name": row["name"],
                "signal_type": "🔴 DEATH CROSS",
                "description": "Ağırlık 20 günlük ortalamayı aşağı kesti."
            })

print(f"Total Fund Flow USD: ${total_fund_flow:,.2f}")
print("Signals:")
for s in quant_signals:
    print(s)
