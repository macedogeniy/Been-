#!/usr/bin/env python3
"""
Скрипт запуска дашборда торговой системы
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("🚀 Запуск дашборда торговой системы...")
    
    # Проверка установки streamlit
    try:
        import streamlit
    except ImportError:
        print("❌ Streamlit не установлен. Установите его командой:")
        print("pip install streamlit")
        sys.exit(1)
    
    # Запуск дашборда
    dashboard_path = Path(__file__).parent / "visualization" / "dashboard.py"
    
    if not dashboard_path.exists():
        print(f"❌ Файл дашборда не найден: {dashboard_path}")
        sys.exit(1)
    
    print(f"📊 Запуск дашборда: {dashboard_path}")
    print("🌐 Дашборд будет доступен по адресу: http://localhost:8501")
    print("⏹️ Для остановки нажмите Ctrl+C")
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        str(dashboard_path), "--server.port", "8501"
    ])

if __name__ == "__main__":
    main()
