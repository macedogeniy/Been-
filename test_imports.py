#!/usr/bin/env python3
"""
Тест импортов всех модулей торговой системы
"""

import sys
import traceback

def test_core_imports():
    """Тест импортов core модулей"""
    print("🔵 Тестирование core модулей...")
    
    try:
        from core.data_types import TimeFrame, MarketStructure, SignalType
        print("  ✅ core.data_types")
    except Exception as e:
        print(f"  ❌ core.data_types: {e}")
        return False
    
    try:
        from core.interfaces import IDataProvider, IMarketStructureAnalyzer
        print("  ✅ core.interfaces")
    except Exception as e:
        print(f"  ❌ core.interfaces: {e}")
        return False
    
    try:
        from core.exceptions import TradingSystemError, DataProviderError
        print("  ✅ core.exceptions")
    except Exception as e:
        print(f"  ❌ core.exceptions: {e}")
        return False
    
    try:
        import core
        print("  ✅ core (модуль)")
    except Exception as e:
        print(f"  ❌ core (модуль): {e}")
        return False
    
    return True

def test_data_imports():
    """Тест импортов data модулей"""
    print("🔵 Тестирование data модулей...")
    
    try:
        from data.data_provider import ExchangeDataProvider
        print("  ✅ data.data_provider")
    except Exception as e:
        print(f"  ❌ data.data_provider: {e}")
        return False
    
    try:
        import data
        print("  ✅ data (модуль)")
    except Exception as e:
        print(f"  ❌ data (модуль): {e}")
        return False
    
    return True

def test_analysis_imports():
    """Тест импортов analysis модулей"""
    print("🔵 Тестирование analysis модулей...")
    
    try:
        from analysis.market_structure import MarketStructureAnalyzer
        print("  ✅ analysis.market_structure")
    except Exception as e:
        print(f"  ❌ analysis.market_structure: {e}")
        return False
    
    try:
        from analysis.liquidity_detector import LiquidityDetector
        print("  ✅ analysis.liquidity_detector")
    except Exception as e:
        print(f"  ❌ analysis.liquidity_detector: {e}")
        return False
    
    try:
        from analysis.poi_identifier import POIIdentifier
        print("  ✅ analysis.poi_identifier")
    except Exception as e:
        print(f"  ❌ analysis.poi_identifier: {e}")
        return False
    
    try:
        from analysis.timeframe_synchronizer import TimeframeSynchronizer
        print("  ✅ analysis.timeframe_synchronizer")
    except Exception as e:
        print(f"  ❌ analysis.timeframe_synchronizer: {e}")
        return False
    
    try:
        import analysis
        print("  ✅ analysis (модуль)")
    except Exception as e:
        print(f"  ❌ analysis (модуль): {e}")
        return False
    
    return True

def test_trading_imports():
    """Тест импортов trading модулей"""
    print("🔵 Тестирование trading модулей...")
    
    try:
        from trading.signal_generator import LiquidityHuntSignalGenerator
        print("  ✅ trading.signal_generator")
    except Exception as e:
        print(f"  ❌ trading.signal_generator: {e}")
        return False
    
    try:
        from trading.risk_manager import LiquidityHuntRiskManager
        print("  ✅ trading.risk_manager")
    except Exception as e:
        print(f"  ❌ trading.risk_manager: {e}")
        return False
    
    try:
        import trading
        print("  ✅ trading (модуль)")
    except Exception as e:
        print(f"  ❌ trading (модуль): {e}")
        return False
    
    return True

def test_backtesting_imports():
    """Тест импортов backtesting модулей"""
    print("🔵 Тестирование backtesting модулей...")
    
    try:
        from backtesting.trade import Trade
        print("  ✅ backtesting.trade")
    except Exception as e:
        print(f"  ❌ backtesting.trade: {e}")
        return False
    
    try:
        from backtesting.portfolio import Portfolio
        print("  ✅ backtesting.portfolio")
    except Exception as e:
        print(f"  ❌ backtesting.portfolio: {e}")
        return False
    
    try:
        from backtesting.performance_metrics import PerformanceMetrics
        print("  ✅ backtesting.performance_metrics")
    except Exception as e:
        print(f"  ❌ backtesting.performance_metrics: {e}")
        return False
    
    try:
        from backtesting.backtest_engine import BacktestEngine
        print("  ✅ backtesting.backtest_engine")
    except Exception as e:
        print(f"  ❌ backtesting.backtest_engine: {e}")
        return False
    
    try:
        import backtesting
        print("  ✅ backtesting (модуль)")
    except Exception as e:
        print(f"  ❌ backtesting (модуль): {e}")
        return False
    
    return True

def test_visualization_imports():
    """Тест импортов visualization модулей"""
    print("🔵 Тестирование visualization модулей...")
    
    try:
        from visualization.chart_visualizer import ChartVisualizer
        print("  ✅ visualization.chart_visualizer")
    except Exception as e:
        print(f"  ❌ visualization.chart_visualizer: {e}")
        return False
    
    try:
        from visualization.dashboard import TradingDashboard
        print("  ✅ visualization.dashboard")
    except Exception as e:
        print(f"  ❌ visualization.dashboard: {e}")
        return False
    
    try:
        from visualization.alerts import AlertManager
        print("  ✅ visualization.alerts")
    except Exception as e:
        print(f"  ❌ visualization.alerts: {e}")
        return False
    
    try:
        import visualization
        print("  ✅ visualization (модуль)")
    except Exception as e:
        print(f"  ❌ visualization (модуль): {e}")
        return False
    
    return True

def test_config_import():
    """Тест импорта конфигурации"""
    print("🔵 Тестирование config...")
    
    try:
        from config import get_config, SystemConfig
        print("  ✅ config")
        
        # Тест получения конфигурации
        config = get_config()
        print(f"  ✅ config получен: {type(config)}")
        
    except Exception as e:
        print(f"  ❌ config: {e}")
        return False
    
    return True

def test_main_files():
    """Тест основных файлов"""
    print("🔵 Тестирование основных файлов...")
    
    try:
        # Не импортируем main.py, так как он может начать выполнение
        print("  ⚠️  main.py - пропущен (может запуститься)")
    except Exception as e:
        print(f"  ❌ main.py: {e}")
        return False
    
    try:
        # Не импортируем liquidity_hunt_bot.py полностью
        print("  ⚠️  liquidity_hunt_bot.py - пропущен (может запуститься)")
    except Exception as e:
        print(f"  ❌ liquidity_hunt_bot.py: {e}")
        return False
    
    return True

def test_optional_dependencies():
    """Тест опциональных зависимостей"""
    print("🔵 Тестирование опциональных зависимостей...")
    
    optional_deps = [
        'pandas', 'numpy', 'ccxt', 'plotly', 'streamlit',
        'loguru', 'pydantic', 'aiohttp'
    ]
    
    missing_deps = []
    
    for dep in optional_deps:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
        except ImportError:
            print(f"  ❌ {dep} - не установлен")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n⚠️  Отсутствуют зависимости: {', '.join(missing_deps)}")
        print("   Установите: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Основная функция тестирования"""
    print("🧪 ТЕСТ ИМПОРТОВ ТОРГОВОЙ СИСТЕМЫ")
    print("=" * 50)
    
    tests = [
        ("Зависимости", test_optional_dependencies),
        ("Core модули", test_core_imports),
        ("Data модули", test_data_imports),
        ("Analysis модули", test_analysis_imports),
        ("Trading модули", test_trading_imports),
        ("Backtesting модули", test_backtesting_imports),
        ("Visualization модули", test_visualization_imports),
        ("Конфигурация", test_config_import),
        ("Основные файлы", test_main_files),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"  ✅ {test_name} - УСПЕШНО")
            else:
                print(f"  ❌ {test_name} - ОШИБКА")
        except Exception as e:
            print(f"  ❌ {test_name} - КРИТИЧЕСКАЯ ОШИБКА: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ НЕ ПРОЙДЕН"
        print(f"  {status}: {test_name}")
    
    print(f"\n📈 Статистика: {passed}/{total} тестов пройдено ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ВСЕ ИМПОРТЫ РАБОТАЮТ КОРРЕКТНО!")
        return True
    else:
        print("⚠️  ОБНАРУЖЕНЫ ПРОБЛЕМЫ С ИМПОРТАМИ")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)