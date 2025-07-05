#!/usr/bin/env python3
"""
🚀 Скрипт быстрого запуска торговой системы "Охота за ликвидностью"

Этот скрипт поможет вам быстро настроить и запустить торговую систему.
Он проведет базовую проверку окружения и предложит варианты запуска.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import shutil


def print_banner():
    """Выводит баннер системы"""
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   🎯 Торговая система "Охота за ликвидностью"                   ║
║                                                                  ║
║   Профессиональная система алгоритмической торговли              ║
║   с реализацией стратегии поиска и охоты за ликвидностью         ║
║                                                                  ║
║   📊 Многотаймфреймовый анализ                                   ║
║   🎯 Детекция BSL/SSL пулов                                      ║
║   📈 Интерактивная визуализация                                  ║
║   🧪 Комплексный бэк-тестинг                                     ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_python_version() -> bool:
    """Проверяет версию Python"""
    min_version = (3, 8)
    current_version = sys.version_info[:2]
    
    if current_version < min_version:
        print(f"❌ Требуется Python {min_version[0]}.{min_version[1]}+ ")
        print(f"   Текущая версия: {current_version[0]}.{current_version[1]}")
        return False
    
    print(f"✅ Python {current_version[0]}.{current_version[1]} - OK")
    return True


def check_dependencies() -> Dict[str, bool]:
    """Проверяет установленные зависимости"""
    required_packages = [
        'pandas', 'numpy', 'ccxt', 'plotly', 'streamlit', 
        'pydantic', 'loguru', 'aiohttp', 'python-dotenv'
    ]
    
    results = {}
    print("\n📦 Проверка зависимостей:")
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
            results[package] = True
        except ImportError:
            print(f"   ❌ {package}")
            results[package] = False
    
    return results


def install_dependencies() -> bool:
    """Устанавливает зависимости"""
    print("\n📥 Установка зависимостей...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Зависимости установлены успешно")
        return True
    except subprocess.CalledProcessError:
        print("❌ Ошибка установки зависимостей")
        return False


def check_config() -> bool:
    """Проверяет наличие конфигурации"""
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    if env_path.exists():
        print("✅ Файл конфигурации .env найден")
        return True
    
    if env_example_path.exists():
        print("⚠️  Файл .env не найден")
        response = input("   Создать .env из .env.example? (y/n): ").lower()
        
        if response in ['y', 'yes', 'да']:
            shutil.copy(env_example_path, env_path)
            print("✅ Файл .env создан из шаблона")
            print("⚠️  Отредактируйте .env файл перед запуском!")
            return True
    
    print("❌ Файл конфигурации не найден")
    return False


def create_directories():
    """Создает необходимые директории"""
    directories = [
        "data", "logs", "backtest_results", 
        "visualization_output", "alerts"
    ]
    
    print("\n📁 Создание директорий:")
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   ✅ {directory}/")


def show_menu() -> str:
    """Показывает меню опций"""
    print("\n🎮 Выберите действие:")
    print("   1. Запустить основной анализ (main.py)")
    print("   2. Запустить демонстрацию (demo.py)")
    print("   3. Запустить бэк-тест (simple_backtest_demo.py)")
    print("   4. Запустить веб-дашборд (run_dashboard.py)")
    print("   5. Запустить визуализацию (visualization_demo.py)")
    print("   6. Запустить все тесты")
    print("   7. Валидация системы (validate_system.py)")
    print("   8. Выход")
    
    return input("\nВаш выбор (1-8): ").strip()


def run_script(script_name: str, description: str) -> bool:
    """Запускает указанный скрипт"""
    script_path = Path(script_name)
    
    if not script_path.exists():
        print(f"❌ Файл {script_name} не найден")
        return False
    
    print(f"\n🚀 Запуск: {description}")
    print(f"   Файл: {script_name}")
    print("=" * 60)
    
    try:
        subprocess.run([sys.executable, script_name], check=True)
        print("=" * 60)
        print(f"✅ {description} завершен")
        return True
    except subprocess.CalledProcessError as e:
        print("=" * 60)
        print(f"❌ Ошибка выполнения: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  Выполнение прервано пользователем")
        return False


def run_tests() -> bool:
    """Запускает тесты системы"""
    test_files = [
        "test_system.py",
        "test_backtesting.py"
    ]
    
    success = True
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"\n🧪 Запуск тестов: {test_file}")
            try:
                subprocess.run([sys.executable, test_file], check=True)
                print(f"✅ Тесты {test_file} пройдены")
            except subprocess.CalledProcessError:
                print(f"❌ Ошибка в тестах {test_file}")
                success = False
        else:
            print(f"⚠️  Файл тестов {test_file} не найден")
    
    return success


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="Быстрый запуск торговой системы"
    )
    parser.add_argument(
        "--mode", 
        choices=["demo", "backtest", "dashboard", "viz", "analysis", "test"],
        help="Режим запуска"
    )
    parser.add_argument(
        "--install-deps", 
        action="store_true",
        help="Установить зависимости"
    )
    parser.add_argument(
        "--setup", 
        action="store_true",
        help="Выполнить первоначальную настройку"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    # Проверяем базовые требования
    if not check_python_version():
        sys.exit(1)
    
    # Установка зависимостей при необходимости
    if args.install_deps:
        if not install_dependencies():
            sys.exit(1)
    
    # Проверяем зависимости
    deps = check_dependencies()
    missing_deps = [pkg for pkg, installed in deps.items() if not installed]
    
    if missing_deps:
        print(f"\n⚠️  Отсутствуют зависимости: {', '.join(missing_deps)}")
        response = input("Установить автоматически? (y/n): ").lower()
        
        if response in ['y', 'yes', 'да']:
            if not install_dependencies():
                sys.exit(1)
        else:
            print("❌ Установите зависимости командой:")
            print("   pip install -r requirements.txt")
            sys.exit(1)
    
    # Настройка окружения
    if args.setup or not check_config():
        create_directories()
        if not check_config():
            print("\n❌ Настройте файл .env перед запуском системы")
            sys.exit(1)
    
    # Режим прямого запуска
    if args.mode:
        scripts = {
            "demo": ("demo.py", "Демонстрация системы"),
            "backtest": ("simple_backtest_demo.py", "Бэк-тест демо"),
            "dashboard": ("run_dashboard.py", "Веб-дашборд"),
            "viz": ("visualization_demo.py", "Визуализация"),
            "analysis": ("main.py", "Основной анализ"),
            "test": (None, "Тесты системы")
        }
        
        if args.mode == "test":
            run_tests()
        else:
            script, description = scripts[args.mode]
            run_script(script, description)
        
        return
    
    # Интерактивное меню
    create_directories()
    
    while True:
        choice = show_menu()
        
        if choice == "1":
            run_script("main.py", "Основной анализ рынка")
        elif choice == "2":
            run_script("demo.py", "Демонстрация возможностей")
        elif choice == "3":
            run_script("simple_backtest_demo.py", "Бэк-тест демо")
        elif choice == "4":
            run_script("run_dashboard.py", "Веб-дашборд")
        elif choice == "5":
            run_script("visualization_demo.py", "Визуализация данных")
        elif choice == "6":
            run_tests()
        elif choice == "7":
            run_script("validate_system.py", "Валидация системы")
        elif choice == "8":
            print("\n👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")
        
        if choice != "8":
            input("\nНажмите Enter для продолжения...")


if __name__ == "__main__":
    main()