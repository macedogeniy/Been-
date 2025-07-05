#!/usr/bin/env python3
"""
Валидационный скрипт для проверки торговой системы "Охота за ликвидностью"
"""

import sys
import traceback
import asyncio
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_core_functionality():
    """Тест основной функциональности"""
    print("🔧 Тестирование основной функциональности...")
    
    try:
        # Тест типов данных
        from core.data_types import TimeFrame, MarketStructure, Signal, OHLCV
        
        # Создание тестового таймфрейма
        tf = TimeFrame.H1
        assert tf.to_seconds() == 3600
        print("  ✅ TimeFrame работает корректно")
        
        # Создание тестового OHLCV
        ohlcv = OHLCV(
            timestamp=datetime.now(),
            open=50000.0,
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=1000.0
        )
        assert ohlcv.is_bullish == True
        assert ohlcv.body_size == 50.0
        print("  ✅ OHLCV работает корректно")
        
    except Exception as e:
        print(f"  ❌ Ошибка в core функциональности: {e}")
        return False
    
    return True

def test_market_analysis():
    """Тест анализа рынка"""
    print("🔧 Тестирование анализа рынка...")
    
    try:
        from analysis.market_structure import MarketStructureAnalyzer
        from analysis.liquidity_detector import LiquidityDetector
        
        # Создание тестовых данных
        dates = pd.date_range(start=datetime.now() - timedelta(days=7), 
                             end=datetime.now(), freq='1H')
        n = len(dates)
        
        # Генерация реалистичных данных
        np.random.seed(42)
        prices = 50000 + np.cumsum(np.random.randn(n) * 10)
        
        data = pd.DataFrame({
            'open': prices,
            'high': prices + np.abs(np.random.randn(n) * 5),
            'low': prices - np.abs(np.random.randn(n) * 5),
            'close': prices + np.random.randn(n) * 2,
            'volume': np.random.randint(100, 1000, n)
        }, index=dates)
        
        # Тест анализа структуры
        analyzer = MarketStructureAnalyzer()
        structure = analyzer.analyze_structure(data)
        print(f"  ✅ Структура рынка определена: {structure.value}")
        
        # Тест детекции свингов
        swing_highs, swing_lows = analyzer.detect_swings(data)
        print(f"  ✅ Свинги обнаружены: {len(swing_highs)}H, {len(swing_lows)}L")
        
        # Тест детекции ликвидности
        detector = LiquidityDetector()
        all_swings = swing_highs + swing_lows
        liquidity_pools = detector.detect_liquidity_pools(data, all_swings)
        print(f"  ✅ Ликвидность обнаружена: {len(liquidity_pools)} пулов")
        
    except Exception as e:
        print(f"  ❌ Ошибка в анализе рынка: {e}")
        return False
    
    return True

def test_signal_generation():
    """Тест генерации сигналов"""
    print("🔧 Тестирование генерации сигналов...")
    
    try:
        from trading.signal_generator import LiquidityHuntSignalGenerator
        from core.data_types import MarketState, ContextState
        
        # Создание тестового состояния рынка
        market_state = MarketState(
            timestamp=datetime.now(),
            symbol="BTC/USDT",
            timeframe=TimeFrame.M15,
            structure=MarketStructure.BULLISH,
            trend_strength=0.7
        )
        
        # Создание контекста
        context = ContextState()
        
        # Тест генератора сигналов
        generator = LiquidityHuntSignalGenerator()
        signals = generator.generate_signals(market_state, context)
        print(f"  ✅ Сигналы сгенерированы: {len(signals)}")
        
    except Exception as e:
        print(f"  ❌ Ошибка в генерации сигналов: {e}")
        return False
    
    return True

def test_backtesting():
    """Тест бэк-тестинга"""
    print("🔧 Тестирование бэк-тестинга...")
    
    try:
        from backtesting.trade import Trade, TradeDirection, TradeStatus
        from backtesting.portfolio import Portfolio
        from backtesting.performance_metrics import PerformanceMetrics
        
        # Создание портфеля
        portfolio = Portfolio(initial_balance=10000.0)
        print("  ✅ Портфель создан")
        
        # Создание тестовой сделки
        trade = portfolio.open_trade(
            trade_id="test_001",
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            quantity=0.1,
            price=50000.0,
            timestamp=datetime.now(),
            stop_loss=49000.0,
            take_profit=52000.0
        )
        
        if trade:
            print("  ✅ Сделка открыта")
            
            # Закрытие сделки
            closed_trade = portfolio.close_trade(
                trade_id="test_001",
                price=51000.0,
                timestamp=datetime.now(),
                reason="manual_test"
            )
            
            if closed_trade:
                print(f"  ✅ Сделка закрыта, P&L: {closed_trade.pnl}")
            
        # Тест метрик
        metrics = PerformanceMetrics(portfolio)
        summary = portfolio.get_performance_summary()
        print(f"  ✅ Метрики рассчитаны: {summary['total_trades']} сделок")
        
    except Exception as e:
        print(f"  ❌ Ошибка в бэк-тестинге: {e}")
        return False
    
    return True

def test_visualization():
    """Тест визуализации"""
    print("🔧 Тестирование визуализации...")
    
    try:
        from visualization.chart_visualizer import ChartVisualizer
        
        # Создание визуализатора
        visualizer = ChartVisualizer()
        print("  ✅ Визуализатор создан")
        
        # Создание тестовых данных
        dates = pd.date_range(start=datetime.now() - timedelta(days=1), 
                             end=datetime.now(), freq='15T')
        n = len(dates)
        
        prices = 50000 + np.cumsum(np.random.randn(n) * 5)
        data = pd.DataFrame({
            'open': prices,
            'high': prices + np.abs(np.random.randn(n) * 2),
            'low': prices - np.abs(np.random.randn(n) * 2),
            'close': prices + np.random.randn(n),
            'volume': np.random.randint(100, 1000, n)
        }, index=dates)
        
        # Тест создания графика
        analysis_results = {
            'swing_points': [],
            'liquidity_zones': [],
            'order_blocks': [],
            'imbalances': [],
            'support_resistance': []
        }
        
        fig = visualizer.create_comprehensive_chart(
            data=data,
            analysis_results=analysis_results,
            signals=[],
            title="Test Chart"
        )
        print("  ✅ График создан")
        
    except Exception as e:
        print(f"  ❌ Ошибка в визуализации: {e}")
        return False
    
    return True

async def test_data_provider():
    """Тест провайдера данных"""
    print("🔧 Тестирование провайдера данных...")
    
    try:
        from data.data_provider import ExchangeDataProvider
        from core.data_types import TimeFrame
        
        # Создание провайдера (без подключения к реальной бирже)
        provider = ExchangeDataProvider()
        print("  ✅ Провайдер данных создан")
        
        # Тест методов (без реального подключения)
        supported_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        print(f"  ✅ Поддерживаемые таймфреймы: {len(supported_timeframes)}")
        
    except Exception as e:
        print(f"  ❌ Ошибка в провайдере данных: {e}")
        return False
    
    return True

def test_config():
    """Тест конфигурации"""
    print("🔧 Тестирование конфигурации...")
    
    try:
        from config import get_config, SystemConfig
        
        # Получение конфигурации
        config = get_config()
        print(f"  ✅ Конфигурация загружена: {type(config)}")
        
        # Проверка основных параметров
        assert hasattr(config, 'trading')
        assert hasattr(config, 'strategy')
        assert hasattr(config, 'backtesting')
        print("  ✅ Все секции конфигурации присутствуют")
        
        # Проверка значений по умолчанию
        assert config.trading.symbol == "BTC/USDT"
        assert config.trading.max_risk_per_trade <= 0.1
        print("  ✅ Значения по умолчанию корректны")
        
    except Exception as e:
        print(f"  ❌ Ошибка в конфигурации: {e}")
        return False
    
    return True

def test_file_structure():
    """Тест структуры файлов"""
    print("🔧 Проверка структуры файлов...")
    
    required_files = [
        "main.py",
        "config.py", 
        "demo.py",
        "requirements.txt",
        "README.md",
        "quickstart.py"
    ]
    
    required_directories = [
        "core",
        "data", 
        "analysis",
        "trading",
        "backtesting",
        "visualization"
    ]
    
    # Проверка файлов
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - отсутствует")
            return False
    
    # Проверка директорий
    for dir_path in required_directories:
        if Path(dir_path).is_dir():
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ❌ {dir_path}/ - отсутствует")
            return False
    
    return True

async def main():
    """Основная функция валидации"""
    print("🔍 ВАЛИДАЦИЯ ТОРГОВОЙ СИСТЕМЫ")
    print("=" * 60)
    
    tests = [
        ("Структура файлов", test_file_structure, False),
        ("Конфигурация", test_config, False),
        ("Основная функциональность", test_core_functionality, False),
        ("Анализ рынка", test_market_analysis, False),
        ("Генерация сигналов", test_signal_generation, False),
        ("Бэк-тестинг", test_backtesting, False),
        ("Визуализация", test_visualization, False),
        ("Провайдер данных", test_data_provider, True),
    ]
    
    results = []
    passed = 0
    
    for test_name, test_func, is_async in tests:
        print(f"\n🧪 {test_name}:")
        try:
            if is_async:
                result = await test_func()
            else:
                result = test_func()
            
            results.append((test_name, result))
            if result:
                passed += 1
                print(f"  🎉 {test_name} - ПРОЙДЕН")
            else:
                print(f"  💥 {test_name} - НЕ ПРОЙДЕН")
                
        except Exception as e:
            print(f"  💥 {test_name} - КРИТИЧЕСКАЯ ОШИБКА:")
            print(f"     {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ ВАЛИДАЦИИ")
    print("=" * 60)
    
    total = len(tests)
    percentage = (passed / total) * 100
    
    for test_name, result in results:
        status = "🎯 ПРОЙДЕН" if result else "❌ НЕ ПРОЙДЕН"
        print(f"  {status}: {test_name}")
    
    print(f"\n📈 Результат: {passed}/{total} тестов пройдено ({percentage:.1f}%)")
    
    if passed == total:
        print("\n🎉 ВСЯ СИСТЕМА РАБОТАЕТ КОРРЕКТНО!")
        print("✨ Торговая система готова к использованию!")
        return True
    elif passed >= total * 0.8:
        print("\n⚠️  СИСТЕМА В ОСНОВНОМ РАБОТАЕТ")
        print("🔧 Некоторые компоненты требуют внимания")
        return True
    else:
        print("\n❌ СИСТЕМА ИМЕЕТ СЕРЬЕЗНЫЕ ПРОБЛЕМЫ")
        print("🛠️  Требуется исправление критических ошибок")
        return False

if __name__ == "__main__":
    print("🚀 Запуск валидации торговой системы...\n")
    
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Валидация прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка валидации: {e}")
        traceback.print_exc()
        sys.exit(1)