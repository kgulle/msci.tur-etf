import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

sys.path.insert(0, 'src')
from analyzer import build_historical_weight_matrix, compare_snapshots
from fetcher import get_available_snapshots, load_snapshot

def generate_trend_chart(output_path):
    print("Matris olusturuluyor...")
    matrix = build_historical_weight_matrix("data/snapshots")
    if matrix.empty:
        print("Veri yok.")
        return
        
    dates = get_available_snapshots("data/snapshots")
    if len(dates) < 2:
        print("Yeterli tarih yok.")
        return
        
    target_date = dates[-1]
    prev_date = dates[-2]
    
    curr_df = load_snapshot(Path("data/snapshots") / f"{target_date.strftime('%Y%m%d')}.csv")
    prev_df = load_snapshot(Path("data/snapshots") / f"{prev_date.strftime('%Y%m%d')}.csv")
    
    analysis = compare_snapshots(prev_df, curr_df, prev_date, target_date)
    
    # Top 5 Artan
    inc = analysis.increased.head(5)["ticker"].tolist()
    # Top 5 Azalan
    dec = analysis.decreased.tail(5)["ticker"].tolist()
    
    sns.set_theme(style="darkgrid")
    fig, axes = plt.subplots(2, 1, figsize=(14, 12), sharex=True)
    
    # Plot Artanlar
    x_vals = [str(i) for i in matrix.index]
    for t in inc:
        if t in matrix.columns:
            axes[0].plot(x_vals, matrix[t].to_numpy(), marker='o', linewidth=2, label=t)
    axes[0].set_title("🟢 Sürekli Ağırlığı Artan (Toplanan) Hisseler", fontsize=16, fontweight='bold', color='green')
    axes[0].set_ylabel("Portföy Ağırlığı (%)", fontsize=12)
    axes[0].legend(loc='upper left', bbox_to_anchor=(1, 1))
    
    # Plot Azalanlar
    for t in dec:
        if t in matrix.columns:
            axes[1].plot(x_vals, matrix[t].to_numpy(), marker='o', linewidth=2, label=t)
    axes[1].set_title("🔴 Sürekli Ağırlığı Azalan (Satılan) Hisseler", fontsize=16, fontweight='bold', color='red')
    axes[1].set_ylabel("Portföy Ağırlığı (%)", fontsize=12)
    axes[1].legend(loc='upper left', bbox_to_anchor=(1, 1))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Grafik kaydedildi: {output_path}")

if __name__ == "__main__":
    # Artifact directory is the current conversation folder
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "trend.png"
    generate_trend_chart(out)
