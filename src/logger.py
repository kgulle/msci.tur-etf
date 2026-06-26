"""
logger.py — Merkezi loglama yapılandırması
"""

import io
import logging
import sys
from pathlib import Path
from datetime import date


def setup_logger(log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """
    Hem konsola hem dosyaya yazan logger oluşturur.
    Her gün yeni bir log dosyası açılır.
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    log_file = Path(log_dir) / f"{date.today().strftime('%Y%m%d')}.log"
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    log_level = level_map.get(level.upper(), logging.INFO)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Konsol handler — Windows'ta UTF-8 encoding zorla
    if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout 
               for h in root_logger.handlers):
        # Windows cp1254 yerine UTF-8 kullan
        utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        console_handler = logging.StreamHandler(utf8_stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)
    
    # Dosya handler
    if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    
    return logging.getLogger("tur_analiz")
