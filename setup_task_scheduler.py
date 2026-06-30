"""
setup_task_scheduler.py — Windows Task Scheduler otomatik kurulum

Bu script, Windows'ta her gün sabah 09:00'da main.py'yi çalıştırmak için
Task Scheduler görevini otomatik olarak oluşturur.

Yönetici yetkisiyle çalıştırın.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import date


def create_task_scheduler_task(
    task_name: str = "TUR_ETF_Analiz",
    hour: int = 20,
    minute: int = 0,
):
    """
    Windows Task Scheduler'a günlük görev ekler.
    Saat 20:00 olarak ayarlanmıştır — BlackRock kapanış verisini 
    genellikle bu saate kadar yayınlar.
    """
    project_dir = Path(__file__).parent.absolute()
    python_exe = sys.executable
    script_path = project_dir / "main.py"
    log_dir = project_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # PowerShell komutu ile task oluştur
    ps_script = f"""
$Action = New-ScheduledTaskAction `
    -Execute "{python_exe}" `
    -Argument "{script_path}" `
    -WorkingDirectory "{project_dir}"

$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "{hour:02d}:{minute:02d}AM"

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName "{task_name}" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "TUR ETF (iShares MSCI Turkey) portföy değişiklik analizini günlük çalıştırır" `
    -Force

Write-Host "✅ Görev oluşturuldu: {task_name}"
Write-Host "   Çalışma saati: Her gün {hour:02d}:{minute:02d}"
Write-Host "   Script: {script_path}"
"""
    
    ps_path = project_dir / "_create_task.ps1"
    ps_path.write_text(ps_script, encoding="utf-8")
    
    print(f"📋 Task Scheduler görevi oluşturuluyor...")
    print(f"   Görev adı  : {task_name}")
    print(f"   Çalışma    : Her gün {hour:02d}:{minute:02d}")
    print(f"   Python     : {python_exe}")
    print(f"   Script     : {script_path}")
    print()
    
    try:
        result = subprocess.run(
            [
                "powershell", "-ExecutionPolicy", "Bypass",
                "-File", str(ps_path)
            ]
        )
        
        if result.returncode == 0:
            print("\n✅ Task Scheduler görevi başarıyla oluşturuldu!")
            print(f"\nKontrol etmek için:")
            print(f"  Windows + R → taskschd.msc → '{task_name}' görevini bulun")
        else:
            print(f"❌ Görev oluşturulamadı (Hata kodu: {result.returncode})")
            print("\n💡 PowerShell'i Yönetici olarak açıp şu komutu çalıştırın:")
            print(f"   powershell -ExecutionPolicy Bypass -File {ps_path}")
    
    except FileNotFoundError:
        print("❌ PowerShell bulunamadı. Bu script sadece Windows'ta çalışır.")
    
    finally:
        # Geçici dosyayı sil
        if ps_path.exists():
            ps_path.unlink()


def verify_task(task_name: str = "TUR_ETF_Analiz"):
    """Görevin oluşturulduğunu doğrular."""
    result = subprocess.run(
        ["schtasks", "/query", "/tn", task_name, "/fo", "LIST"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"\n📅 Görev durumu:\n{result.stdout}")
    else:
        print(f"\n⚠️  Görev bulunamadı: {task_name}")


def remove_task(task_name: str = "TUR_ETF_Analiz"):
    """Görevi kaldırır."""
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"✅ Görev kaldırıldı: {task_name}")
    else:
        print(f"❌ Görev kaldırılamadı: {result.stderr}")


def main():
    print("\n" + "="*60)
    print("  ⏰ Windows Task Scheduler Kurulumu")
    print("="*60 + "\n")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--remove":
            remove_task()
            return
        if sys.argv[1] == "--verify":
            verify_task()
            return
    
    print("Görev: Her gün sabah 09:00'da TUR ETF analizi çalıştırılacak")
    print("       (Önceki iş günü kapanış verisi ile karşılaştırma yapılır)\n")
    
    confirm = input("Devam etmek istiyor musunuz? (e/h): ").strip().lower()
    if confirm not in ["e", "evet", "y", "yes"]:
        print("İptal edildi.")
        return
    
    create_task_scheduler_task(hour=9, minute=0)
    
    print("\n" + "="*60)
    print("  Yararlı komutlar:")
    print("="*60)
    print("""
  Görevi test etmek için hemen çalıştır:
    schtasks /run /tn TUR_ETF_Analiz

  Görev durumunu kontrol et:
    python setup_task_scheduler.py --verify

  Görevi kaldır:
    python setup_task_scheduler.py --remove

  Manuel çalıştır:
    python main.py
""")


if __name__ == "__main__":
    main()
