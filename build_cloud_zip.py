import os
import zipfile
from pathlib import Path

def create_cloud_function_zip():
    zip_path = "tur-etf-cloud-function.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add main.py (from cloud_main.py)
        zipf.write("cloud_main.py", arcname="main.py")
        
        # Add requirements.txt
        with open("requirements.txt", "r") as f:
            reqs = f.read()
        if "functions-framework" not in reqs:
            reqs += "\nfunctions-framework==3.*"
            
        zipf.writestr("requirements.txt", reqs)
        
        # Add src folder
        src_dir = Path("src")
        for file in src_dir.glob("*.py"):
            zipf.write(file, arcname=f"src/{file.name}")
            
    print(f"Bitti! Google Cloud Functions icin {zip_path} dosyasi hazirlandi.")

if __name__ == "__main__":
    create_cloud_function_zip()
