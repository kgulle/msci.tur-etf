"""
setup_google_sheets.py — Google Sheets kurulum sihirbazı

Bu scripti çalıştırarak:
1. Service account JSON dosyanızı yapılandırın
2. Google Sheets bağlantısını test edin
3. Sekme yapısını otomatik oluşturun
"""

import os
import sys
import json
import shutil
from pathlib import Path

# Proje kök dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv, set_key

load_dotenv()


def print_header():
    print("\n" + "="*65)
    print("  [TR] TUR ETF Portföy Takip — Google Sheets Kurulum Sihirbazı")
    print("="*65 + "\n")


def check_credentials_dir():
    """credentials/ dizinini oluşturur."""
    cred_dir = Path("credentials")
    cred_dir.mkdir(exist_ok=True)
    gitignore = cred_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("# Service account credentials — asla commit etmeyin!\n*\n")
    return cred_dir


def guide_service_account_creation():
    """Kullanıcıya service account oluşturma adımlarını gösterir."""
    print("📋 GOOGLE SERVICE ACCOUNT OLUŞTURMA ADIMLARI:")
    print("-"*60)
    print("""
1. Google Cloud Console'a gidin:
   https://console.cloud.google.com/

2. Yeni proje oluşturun veya mevcut projeyi seçin
   (örn: "tur-etf-tracker")

3. Sol menüden: APIs & Services → Library
   - "Google Sheets API" arayın → ENABLE
   - "Google Drive API" arayın → ENABLE

4. Sol menüden: APIs & Services → Credentials
   - "CREATE CREDENTIALS" → "Service Account"
   - İsim: tur-etf-tracker
   - Role: "Editor" seçin
   - Oluştur

5. Oluşturulan service account'a tıklayın
   - "KEYS" sekmesi → "ADD KEY" → "Create new key"
   - JSON seçin → İNDİR

6. İndirilen JSON dosyasını şuraya kopyalayın:
   credentials/service_account.json

7. JSON dosyasındaki "client_email" değerini kopyalayın
   (örn: tur-etf-tracker@proje-id.iam.gserviceaccount.com)

8. Google Sheets tablonuzu açın:
   https://docs.google.com/spreadsheets/d/1tg5OBvX_ohCrxdiz_2JvtQxTPKmE-hNW27C2WGxH7n0
   
   "Share" → "Add people" → service account e-postasını ekleyin
   → "Editor" rolü → Done
""")


def get_service_account_file() -> str:
    """Service account dosyasını bulur veya kullanıcıdan ister."""
    default_path = "credentials/service_account.json"
    
    if Path(default_path).exists():
        print(f"✅ Service account dosyası bulundu: {default_path}")
        return default_path
    
    print("\n⚠️  credentials/service_account.json bulunamadı.")
    guide_service_account_creation()
    
    print("\n📁 Alternatif olarak başka bir konumdaki dosyayı belirtebilirsiniz.")
    custom_path = input("Service account JSON dosyasının yolu (Enter=varsayılan): ").strip()
    
    if not custom_path:
        print(f"\n⏳ Dosyayı indirip şuraya kopyalayın: {Path(default_path).absolute()}")
        print("   Sonra bu scripti tekrar çalıştırın.")
        return None
    
    if Path(custom_path).exists():
        # Dosyayı doğru konuma kopyala
        dest = Path(default_path)
        dest.parent.mkdir(exist_ok=True)
        shutil.copy(custom_path, dest)
        print(f"✅ Dosya kopyalandı: {dest}")
        return str(dest)
    
    print(f"❌ Dosya bulunamadı: {custom_path}")
    return None


def validate_service_account(file_path: str) -> dict:
    """Service account JSON dosyasını doğrular."""
    try:
        with open(file_path) as f:
            creds = json.load(f)
        
        required_fields = ["type", "project_id", "client_email", "private_key"]
        missing = [f for f in required_fields if f not in creds]
        
        if missing:
            print(f"❌ Geçersiz service account dosyası. Eksik alanlar: {missing}")
            return None
        
        if creds.get("type") != "service_account":
            print(f"❌ Bu bir service account dosyası değil (type={creds.get('type')})")
            return None
        
        print(f"✅ Service account geçerli:")
        print(f"   Project ID  : {creds.get('project_id')}")
        print(f"   Client Email: {creds.get('client_email')}")
        
        return creds
    
    except json.JSONDecodeError:
        print(f"❌ JSON parse hatası: {file_path}")
        return None
    except Exception as e:
        print(f"❌ Dosya okuma hatası: {e}")
        return None


def test_sheets_connection(service_account_file: str, sheets_id: str) -> bool:
    """Google Sheets bağlantısını test eder."""
    print("\n🔗 Google Sheets bağlantısı test ediliyor...")
    
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(service_account_file, scopes=scopes)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(sheets_id)
        
        print(f"✅ Bağlantı başarılı!")
        print(f"   Tablo adı: '{spreadsheet.title}'")
        print(f"   Mevcut sekmeler: {[ws.title for ws in spreadsheet.worksheets()]}")
        return True
    
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ Tablo bulunamadı: {sheets_id}")
        print("   → Service account e-postasını tabloya editör olarak eklediğinizden emin olun")
        return False
    except gspread.exceptions.APIError as e:
        print(f"❌ API Hatası: {e}")
        print("   → Google Sheets API'nin aktif olduğundan emin olun")
        return False
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return False


def setup_spreadsheet_tabs(service_account_file: str, sheets_id: str):
    """Tüm sekmeleri oluşturur."""
    print("\n📑 Sekme yapısı oluşturuluyor...")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from sheets_writer import SheetsWriter
        
        writer = SheetsWriter(sheets_id, service_account_file)
        if writer.connect():
            writer.setup_sheets()
            print("\n✅ Tüm sekmeler başarıyla oluşturuldu!")
        
    except Exception as e:
        print(f"❌ Sekme oluşturma hatası: {e}")


def create_env_file(service_account_file: str, sheets_id: str):
    """Konfigürasyonu .env dosyasına kaydeder."""
    env_path = Path(".env")
    
    if env_path.exists():
        print(f"\n⚠️  .env dosyası zaten mevcut. Güncelleniyor...")
    
    env_content = f"""# TUR ETF Portföy Takip Sistemi — Ortam Değişkenleri
# Bu dosya otomatik oluşturuldu: setup_google_sheets.py

GOOGLE_SHEETS_ID={sheets_id}
GOOGLE_SERVICE_ACCOUNT_FILE={service_account_file}

BLACKROCK_PORTFOLIO_ID=239689
BACKFILL_DAYS=90
LOG_LEVEL=INFO
LOG_DIR=logs
SNAPSHOT_DIR=data/snapshots
CHANGES_DIR=data/changes
WEIGHT_CHANGE_THRESHOLD=0.05
"""
    env_path.write_text(env_content, encoding="utf-8")
    print(f"\n✅ .env dosyası oluşturuldu: {env_path.absolute()}")


def create_gitignore():
    """Hassas dosyaları .gitignore'a ekler."""
    gitignore_path = Path(".gitignore")
    ignore_entries = [
        ".env",
        "credentials/",
        "*.json",
        "data/",
        "logs/",
        "__pycache__/",
        "*.pyc",
    ]
    
    existing = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    
    new_entries = []
    for entry in ignore_entries:
        if entry not in existing:
            new_entries.append(entry)
    
    if new_entries:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("\n# TUR ETF Tracker\n")
            f.write("\n".join(new_entries) + "\n")
        print(f"✅ .gitignore güncellendi")


def main():
    print_header()
    
    sheets_id = os.getenv("GOOGLE_SHEETS_ID", "1tg5OBvX_ohCrxdiz_2JvtQxTPKmE-hNW27C2WGxH7n0")
    
    print(f"📊 Google Sheets ID: {sheets_id}")
    print(f"   Tablo URL: https://docs.google.com/spreadsheets/d/{sheets_id}\n")
    
    # 1. credentials/ dizinini oluştur
    check_credentials_dir()
    
    # 2. Service account dosyasını bul/al
    service_account_file = get_service_account_file()
    if not service_account_file:
        print("\n❌ Kurulum tamamlanamadı. Service account dosyası gerekli.")
        print("\n💡 Dosyayı indirip credentials/service_account.json konumuna kopyalayın,")
        print("   ardından bu scripti tekrar çalıştırın.")
        sys.exit(1)
    
    # 3. Dosyayı doğrula
    creds_data = validate_service_account(service_account_file)
    if not creds_data:
        sys.exit(1)
    
    # 4. Kullanıcıya e-posta bilgisini göster
    print(f"\n📧 ÖNEMLİ: Aşağıdaki e-postayı Google Sheets tablonuza editör olarak ekleyin:")
    print(f"   {creds_data.get('client_email')}")
    print(f"\n   Tablo URL: https://docs.google.com/spreadsheets/d/{sheets_id}")
    
    input("\n⏎ Tabloya editör olarak ekledikten sonra Enter'a basın...")
    
    # 5. Bağlantıyı test et
    if not test_sheets_connection(service_account_file, sheets_id):
        print("\n❌ Bağlantı başarısız. Lütfen yukarıdaki hata mesajını kontrol edin.")
        sys.exit(1)
    
    # 6. .env dosyasını oluştur
    create_env_file(service_account_file, sheets_id)
    
    # 7. .gitignore güncelle
    create_gitignore()
    
    # 8. Sekme yapısını oluştur
    setup_spreadsheet_tabs(service_account_file, sheets_id)
    
    # 9. İlk veriyi çek ve yaz
    print("\n🚀 İlk veri çekimi yapılıyor...")
    import subprocess
    result = subprocess.run([sys.executable, "main.py", "--no-sheets"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ İlk snapshot alındı!")
    
    print("\n" + "="*65)
    print("  ✅ KURULUM TAMAMLANDI!")
    print("="*65)
    print("""
Sonraki adımlar:
  1. Backfill (90 günlük geçmiş veri):
     python main.py --backfill

  2. Günlük otomatik çalıştırma için Task Scheduler kurulumu:
     python setup_task_scheduler.py

  3. Manuel çalıştırma:
     python main.py
""")


if __name__ == "__main__":
    main()
