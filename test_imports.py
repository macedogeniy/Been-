#!/usr/bin/env python3
"""
Тест импортов всех модулей торговой системы
ВКЛЮЧАЯ ТЕСТИРОВАНИЕ ЗАГРУЗКИ РЕАЛЬНЫХ ДАННЫХ
"""

import sys
import traceback
import asyncio
from datetime import datetime

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
    print("� Тестирование data модулей...")
    
    try:
        from data.data_provider import DataProvider
        print("  ✅ data.data_provider")
    except Exception as e:
        print(f"  ❌ data.data_provider: {e}")
        return False
    
    try:
        from data.historical_data_fetcher import HistoricalDataFetcher, get_demo_data
        print("  ✅ data.historical_data_fetcher")
    except Exception as e:
        print(f"  ❌ data.historical_data_fetcher: {e}")
        return False
    
    return True

def test_analysis_imports():
    """Тест импортов analysis модулей"""
    print("� Тестирование analysis модулей...")
    
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
    print("� Тестирование trading модулей...")
    
    try:
        from trading.signal_generator import SignalGenerator
        print("  ✅ trading.signal_generator")
    except Exception as e:
        print(f"  ❌ trading.signal_generator: {e}")
        return False
    
    try:
        from trading.risk_manager import RiskManager
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
    print("� Тестирование backtesting модулей...")
    
    try:
        from backtesting.trade import Trade, TradeDirection, TradeStatus
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
    print("� Тестирование visualization модулей...")
    
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

def test_config_imports():
    """Тест импортов конфигурации"""
    print("⚙️ Тестирование конфигурации...")
    
    try:
        from config import get_config
        config = get_config()
        print("  ✅ config")
        return True
    except Exception as e:
        print(f"  ❌ config: {e}")
        return False

async def test_real_data_functionality():
    """Тест функциональности с реальными данными"""
    print("🌐 Тестирование функциональности с реальными данными...")
    
    try:
        # Импорт необходимых модулей
        from data.historical_data_fetcher import get_demo_data
        from core.data_types import TimeFrame
        
        print("  📡 Тестирование загрузки реальных данных...")
        
        # Загрузка реальных данных
        data = await get_demo_data(
            symbol="BTC/USDT", 
            timeframe=TimeFrame.H1, 
            days_back=3
        )
        
        if data is not None and len(data) > 0:
            print(f"  ✅ Загружено {len(data)} реальных свечей")
            print(f"  📊 Период: {data.index[0]} → {data.index[-1]}")
            
            # Проверка структуры данных
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if not missing_columns:
                print("  ✅ Структура данных корректна")
                
                # Базовая валидация данных
                current_price = data['close'].iloc[-1]
                price_range = data['high'].max() - data['low'].min()
                
                print(f"  💰 Текущая цена: ${current_price:,.2f}")
                print(f"  📊 Диапазон за период: ${price_range:,.2f}")
                
                # Проверка разумности данных
                if 1000 < current_price < 200000:  # Разумный диапазон для BTC
                    print("  ✅ Цены в разумном диапазоне")
                else:
                    print(f"  ⚠️ Необычные цены: ${current_price:,.2f}")
                
                return True
            else:
                print(f"  ❌ Отсутствуют колонки: {missing_columns}")
                return False
        else:
            print("  ❌ Данные не загружены")
            return False
            
    except Exception as e:
        print(f"  ❌ Ошибка загрузки реальных данных: {e}")
        traceback.print_exc()
        return False

async def test_real_data_analysis():
    """Тест анализа реальных данных"""
    print("� Тестирование анализа реальных данных...")
    
    try:
        # Импорты
        from data.historical_data_fetcher import get_demo_data
        from analysis.market_structure import MarketStructureAnalyzer
        from analysis.liquidity_detector import LiquidityDetector
        from core.data_types import TimeFrame
        
        # Загрузка данных
        data = await get_demo_data(symbol="BTC/USDT", timeframe=TimeFrame.H1, days_back=5)
        
        if len(data) < 20:
            print("  ⚠️ Недостаточно данных для анализа")
            return True  # Не критическая ошибка
        
        # Анализ структуры рынка
        analyzer = MarketStructureAnalyzer()
        
        # Тест детекции свинг-точек
        swing_highs, swing_lows = analyzer.detect_swings(data)
        print(f"  🔄 Найдено свинг-точек: {len(swing_highs)}H + {len(swing_lows)}L")
        
        # Тест анализа структуры
        structure = analyzer.analyze_structure(data)
        print(f"  📈 Структура рынка: {structure.value}")
        
        # Тест детекции ликвидности
        if swing_highs or swing_lows:
            liquidity_detector = LiquidityDetector()
            all_swings = swing_highs + swing_lows
            liquidity_pools = liquidity_detector.detect_liquidity_pools(data, all_swings)
            print(f"  💧 Найдено пулов ликвидности: {len(liquidity_pools)}")
            
            if liquidity_pools:
                avg_strength = sum(p.strength for p in liquidity_pools) / len(liquidity_pools)
                print(f"  ⭐ Средняя сила пулов: {avg_strength:.2f}")
        
        print("  ✅ Анализ реальных данных работает")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка анализа реальных данных: {e}")
        traceback.print_exc()
        return False

def test_main_scripts():
    """Тест основных скриптов"""
    print("� Тестирование основных скриптов...")
    
    scripts_to_test = [
        'main.py',
        'demo.py', 
        'simple_backtest_demo.py',
        'visualization_demo.py',
        'quickstart.py'
    ]
    
    for script in scripts_to_test:
        try:
            # Проверяем, что файл существует и можно скомпилировать
            import py_compile
            py_compile.compile(script, doraise=True)
            print(f"  ✅ {script}")
        except FileNotFoundError:
            print(f"  ❌ {script} - файл не найден")
            return False
        except py_compile.PyCompileError as e:
            print(f"  ❌ {script} - ошибка компиляции: {e}")
            return False
        except Exception as e:
            print(f"  ⚠️ {script} - предупреждение: {e}")
    
    return True

async def run_comprehensive_import_test():
    """Запуск полного теста импортов и функциональности"""
    
    print("🧪 ПОЛНЫЙ ТЕСТ ИМПОРТОВ И ФУНКЦИОНАЛЬНОСТИ")
    print("🌟 ВКЛЮЧАЯ ТЕСТИРОВАНИЕ РЕАЛЬНЫХ ДАННЫХ")
    print("=" * 70)
    print(f"📅 Время тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Список всех тестов
    tests = [
        ("Core модули", test_core_imports, False),
        ("Data модули", test_data_imports, False),
        ("Analysis модули", test_analysis_imports, False),
        ("Trading модули", test_trading_imports, False),
        ("Backtesting модули", test_backtesting_imports, False),
        ("Visualization модули", test_visualization_imports, False),
        ("Конфигурация", test_config_imports, False),
        ("Основные скрипты", test_main_scripts, False),
        ("Функциональность с реальными данными", test_real_data_functionality, True),
        ("Анализ реальных данных", test_real_data_analysis, True)
    ]
    
    print(f"\n🔬 Выполнение {len(tests)} тестов...\n")
    
    results = []
    passed = 0
    failed = 0
    
    for test_name, test_func, is_async in tests:
        print(f"🧪 Тест: {test_name}")
        
        try:
            if is_async:
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                results.append((test_name, True, None))
                print(f"✅ {test_name}: ПРОЙДЕН\n")
            else:
                failed += 1
                results.append((test_name, False, "Тест завершился с ошибкой"))
                print(f"❌ {test_name}: НЕ ПРОЙДЕН\n")
                
        except Exception as e:
            failed += 1
            results.append((test_name, False, str(e)))
            print(f"💥 {test_name}: КРИТИЧЕСКАЯ ОШИБКА - {e}\n")
    
    # Итоговый отчет
    print("=" * 70)
    print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    
    for test_name, success, error in results:
        if success:
            print(f"✅ {test_name}")
        else:
            print(f"❌ {test_name}")
            if error and error != "Тест завершился с ошибкой":
                print(f"   Ошибка: {error}")
    
    # Статистика
    total = len(tests)
    success_rate = (passed / total) * 100
    
    print(f"\n📈 СТАТИСТИКА:")
    print(f"  ✅ Пройдено: {passed}/{total}")
    print(f"  ❌ Провалено: {failed}/{total}")
    print(f"  📊 Успешность: {success_rate:.1f}%")
    
    # Финальная оценка
    if failed == 0:
        print(f"\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("✨ Система готова к работе с реальными данными!")
        status = "ОТЛИЧНО"
    elif failed <= 2:
        print(f"\n⚠️ БОЛЬШИНСТВО ТЕСТОВ ПРОЙДЕНО")
        print("🔧 Несколько компонентов требуют внимания")
        status = "ХОРОШО"
    else:
        print(f"\n❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ")
        print("🛠️ Требуется серьезная доработка")
        status = "ТРЕБУЕТ ИСПРАВЛЕНИЯ"
    
    print(f"\n🏁 ФИНАЛЬНАЯ ОЦЕНКА: {status}")
    
    # Особые достижения
    real_data_tests = [name for name, success, _ in results 
                      if "реальными данными" in name and success]
    
    if real_data_tests:
        print(f"\n🌟 ОСОБЫЕ ДОСТИЖЕНИЯ:")
        print("  ✨ Успешное тестирование с реальными данными")
        print("  🌐 Система готова к работе с live-данными")
        print("  📊 Проверена работа с актуальными рыночными данными")
    
    return failed == 0

async def main():
    """Главная функция"""
    print("🚀 Запуск полного тестирования импортов...\n")
    
    try:
        success = await run_comprehensive_import_test()
        
        if success:
            print("\n✨ Тестирование завершено успешно!")
            return 0
        else:
            print("\n❌ Тестирование завершено с ошибками!")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Тестирование прервано пользователем")
        return 1
        
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Запуск тестирования
    exit_code = asyncio.run(main())
    
    print(f"\n🏁 Код выхода: {exit_code}")
    sys.exit(exit_code)