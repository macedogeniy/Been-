"""
Демонстрация системы визуализации для торговой стратегии "Охота за ликвидностью"
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json

# Импорт компонентов визуализации
from visualization.chart_visualizer import ChartVisualizer
from visualization.alerts import AlertManager, AlertType, AlertPriority


def generate_sample_data():
    """Генерация демонстрационных данных"""
    
    print("🔄 Генерация демонстрационных данных...")
    
    # Генерация OHLCV данных
    np.random.seed(42)
    dates = pd.date_range(start=datetime.now() - timedelta(days=7), 
                         end=datetime.now(), freq='15T')
    
    n_periods = len(dates)
    
    # Симуляция цены с трендом
    price_base = 45000
    price_trend = np.cumsum(np.random.randn(n_periods) * 50) + price_base
    
    # OHLC данные
    data = []
    for i, timestamp in enumerate(dates):
        if i == 0:
            open_price = price_base
        else:
            open_price = data[i-1]['close']
        
        close_price = price_trend[i]
        high_price = max(open_price, close_price) + abs(np.random.randn() * 20)
        low_price = min(open_price, close_price) - abs(np.random.randn() * 20)
        volume = np.random.randint(100, 1000)
        
        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    # Генерация анализа
    analysis_results = generate_analysis_results(df)
    
    # Генерация сигналов
    signals = generate_sample_signals(df)
    
    return df, analysis_results, signals


def generate_analysis_results(df):
    """Генерация результатов анализа"""
    
    # Свинг-точки
    swing_points = []
    for i in range(5, len(df) - 5, 20):  # Каждые 20 свечей
        if np.random.random() > 0.5:
            swing_points.append({
                'timestamp': df.index[i],
                'price': df.iloc[i]['high'] if np.random.random() > 0.5 else df.iloc[i]['low'],
                'type': 'high' if np.random.random() > 0.5 else 'low',
                'strength': np.random.uniform(0.3, 1.0)
            })
    
    # Зоны ликвидности
    liquidity_zones = []
    for _ in range(5):
        idx = np.random.randint(0, len(df))
        price = df.iloc[idx]['high'] + np.random.uniform(10, 100)
        liquidity_zones.append({
            'type': 'BSL' if np.random.random() > 0.5 else 'SSL',
            'price': price,
            'strength': np.random.uniform(0.4, 1.0),
            'range': np.random.uniform(5, 20),
            'start_time': df.index[0],
            'end_time': df.index[-1]
        })
    
    # Order Blocks
    order_blocks = []
    for _ in range(8):
        idx = np.random.randint(10, len(df) - 10)
        start_idx = max(0, idx - 5)
        end_idx = min(len(df) - 1, idx + 5)
        
        order_blocks.append({
            'direction': 'bullish' if np.random.random() > 0.5 else 'bearish',
            'start_time': df.index[start_idx],
            'end_time': df.index[end_idx],
            'high': df.iloc[start_idx:end_idx]['high'].max(),
            'low': df.iloc[start_idx:end_idx]['low'].min(),
            'strength': np.random.uniform(0.3, 0.9)
        })
    
    # Imbalances (FVG)
    imbalances = []
    for _ in range(6):
        idx = np.random.randint(5, len(df) - 5)
        start_time = df.index[idx]
        end_time = df.index[min(len(df) - 1, idx + 10)]
        
        base_price = df.iloc[idx]['close']
        gap_size = np.random.uniform(20, 80)
        
        imbalances.append({
            'type': 'bullish' if np.random.random() > 0.5 else 'bearish',
            'start_time': start_time,
            'end_time': end_time,
            'high': base_price + gap_size,
            'low': base_price,
            'filled': np.random.random() < 0.3
        })
    
    # Уровни поддержки/сопротивления
    support_resistance = []
    unique_prices = np.random.choice(df['close'].values, 4, replace=False)
    for price in unique_prices:
        support_resistance.append({
            'price': price,
            'type': 'support' if np.random.random() > 0.5 else 'resistance',
            'touches': np.random.randint(2, 6),
            'strength': np.random.uniform(0.4, 0.9)
        })
    
    return {
        'swing_points': swing_points,
        'liquidity_zones': liquidity_zones,
        'order_blocks': order_blocks,
        'imbalances': imbalances,
        'support_resistance': support_resistance
    }


def generate_sample_signals(df):
    """Генерация демонстрационных сигналов"""
    
    signals = []
    
    # Генерируем несколько сигналов
    for _ in range(4):
        idx = np.random.randint(50, len(df) - 50)
        timestamp = df.index[idx]
        price = df.iloc[idx]['close']
        
        signal = {
            'timestamp': timestamp,
            'action': 'BUY' if np.random.random() > 0.5 else 'SELL',
            'price': price,
            'symbol': 'BTCUSDT',
            'confidence': np.random.uniform(0.6, 0.95),
            'confluence_score': np.random.uniform(0.5, 0.9),
            'poi_type': np.random.choice(['Order Block', 'Imbalance', 'Support/Resistance']),
            'reason': 'Liquidity Hunt + Structure Break'
        }
        
        signals.append(signal)
    
    return signals


def demo_chart_visualizer():
    """Демонстрация ChartVisualizer"""
    
    print("\n📊 Демонстрация ChartVisualizer")
    print("=" * 50)
    
    # Создание визуализатора
    visualizer = ChartVisualizer(theme="dark")
    
    # Генерация данных
    ohlcv_data, analysis_results, signals = generate_sample_data()
    
    # Создание комплексного графика
    print("🎨 Создание комплексного графика...")
    fig = visualizer.create_comprehensive_chart(
        data=ohlcv_data,
        analysis_results=analysis_results,
        signals=signals,
        title="BTCUSDT - Liquidity Hunt Analysis Demo"
    )
    
    # Сохранение графика
    output_dir = Path("visualization_output")
    output_dir.mkdir(exist_ok=True)
    
    chart_file = output_dir / "liquidity_hunt_chart_demo.html"
    visualizer.save_chart(fig, str(chart_file), format="html")
    
    print(f"✅ График сохранен: {chart_file}")
    
    # Создание графика сравнения стратегий
    print("📈 Создание графика сравнения стратегий...")
    
    strategies_data = {
        'Liquidity Hunt': {
            'equity_curve': {
                'timestamp': pd.date_range(start=datetime.now() - timedelta(days=30),
                                         end=datetime.now(), freq='D'),
                'equity': np.cumsum(np.random.randn(31) * 100) + 10000
            }
        },
        'Moving Average': {
            'equity_curve': {
                'timestamp': pd.date_range(start=datetime.now() - timedelta(days=30),
                                         end=datetime.now(), freq='D'),
                'equity': np.cumsum(np.random.randn(31) * 80) + 10000
            }
        }
    }
    
    comparison_fig = visualizer.create_comparison_chart(
        strategies_data=strategies_data,
        title="Strategy Performance Comparison"
    )
    
    comparison_file = output_dir / "strategy_comparison_demo.html"
    visualizer.save_chart(comparison_fig, str(comparison_file), format="html")
    
    print(f"✅ График сравнения сохранен: {comparison_file}")


async def demo_alert_manager():
    """Демонстрация AlertManager"""
    
    print("\n🚨 Демонстрация AlertManager")
    print("=" * 50)
    
    # Конфигурация (для демо используем только file и console)
    config = {
        'telegram': {
            'bot_token': 'demo_token',
            'chat_id': 'demo_chat'
        },
        'email': {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': 'demo@gmail.com',
            'password': 'demo_password',
            'from': 'demo@gmail.com',
            'to': 'trader@gmail.com'
        }
    }
    
    # Создание менеджера алертов
    alert_manager = AlertManager(config)
    
    # 1. Демонстрация алерта о сигнале
    print("🎯 Создание алерта о сигнале...")
    signal_data = {
        'action': 'BUY',
        'symbol': 'BTCUSDT',
        'price': 45250.75,
        'confidence': 0.85,
        'confluence_score': 0.78,
        'poi_type': 'Order Block',
        'reason': 'SSL sweep + OB retest + bullish CHoCH'
    }
    
    signal_alert = alert_manager.create_signal_alert(signal_data)
    signal_alert.channels = ['file', 'console']  # Только безопасные каналы для демо
    await alert_manager.send_alert(signal_alert)
    
    # 2. Демонстрация алерта о сделке
    print("💼 Создание алерта о сделке...")
    trade_data = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'size': 0.1,
        'entry_price': 45250.75,
        'current_price': 45680.25,
        'pnl': 42.95
    }
    
    trade_alert = alert_manager.create_trade_alert(trade_data, 'closed')
    trade_alert.channels = ['file', 'console']
    await alert_manager.send_alert(trade_alert)
    
    # 3. Демонстрация алерта о производительности
    print("📊 Создание алерта о производительности...")
    performance_data = {
        'total_return': 15.6,
        'win_rate': 68.4,
        'profit_factor': 1.85,
        'max_drawdown': 7.2,
        'sharpe_ratio': 1.42,
        'total_trades': 156
    }
    
    performance_alert = alert_manager.create_performance_alert(performance_data)
    performance_alert.channels = ['file', 'console']
    await alert_manager.send_alert(performance_alert)
    
    # 4. Демонстрация системного алерта
    print("🚨 Создание системного алерта...")
    system_alert = alert_manager.create_system_alert(
        "Превышен лимит API запросов", 
        {'api_calls': 1200, 'limit': 1000}
    )
    system_alert.channels = ['file', 'console']
    await alert_manager.send_alert(system_alert)
    
    # 5. Статистика алертов
    print("\n📈 Статистика алертов:")
    stats = alert_manager.get_alerts_stats(days=1)
    print(f"  Всего алертов: {stats['total_alerts']}")
    print(f"  По типам: {stats['by_type']}")
    print(f"  По приоритетам: {stats['by_priority']}")
    print(f"  Успешность отправки: {stats['success_rate']:.1f}%")


def create_sample_dashboard_data():
    """Создание демонстрационных данных для дашборда"""
    
    print("\n🖥️ Создание данных для дашборда...")
    
    # Создание директории для результатов
    results_dir = Path("backtest_results")
    results_dir.mkdir(exist_ok=True)
    
    # Генерация метрик
    metrics = {
        'total_pnl': 2450.75,
        'pnl_change_24h': 125.50,
        'win_rate': 68.4,
        'win_rate_change': 2.1,
        'total_trades': 156,
        'trades_today': 3,
        'current_drawdown': 4.2,
        'drawdown_change': -0.8,
        'active_signals': 2,
        'new_signals': 1,
        'total_return': 15.6,
        'profit_factor': 1.85,
        'max_drawdown': 7.2,
        'sharpe_ratio': 1.42,
        'avg_profit': 125.30,
        'avg_loss': -68.20
    }
    
    # Сохранение метрик
    with open(results_dir / "demo_metrics.json", 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    
    # Генерация сделок
    trades = []
    for i in range(20):
        pnl = np.random.choice([1, -1]) * abs(np.random.normal(100, 50))
        trade = {
            'id': f"trade_{i+1:03d}",
            'symbol': 'BTCUSDT',
            'direction': np.random.choice(['LONG', 'SHORT']),
            'size': round(np.random.uniform(0.01, 0.5), 3),
            'entry_price': round(np.random.uniform(44000, 46000), 2),
            'exit_price': round(np.random.uniform(44000, 46000), 2) if pnl != 0 else None,
            'pnl': round(pnl, 2) if pnl != 0 else None,
            'entry_time': (datetime.now() - timedelta(days=np.random.randint(0, 30))).isoformat(),
            'exit_time': (datetime.now() - timedelta(days=np.random.randint(0, 29))).isoformat() if pnl != 0 else None,
            'status': 'closed' if pnl != 0 else 'open'
        }
        trades.append(trade)
    
    # Сохранение сделок
    with open(results_dir / "demo_trades.json", 'w', encoding='utf-8') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Демонстрационные данные созданы в {results_dir}")


def create_launch_script():
    """Создание скрипта запуска дашборда"""
    
    script_content = '''#!/usr/bin/env python3
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
'''
    
    with open("run_dashboard.py", 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Делаем файл исполняемым (если на Unix-системе)
    try:
        import os
        os.chmod("run_dashboard.py", 0o755)
    except:
        pass
    
    print("✅ Скрипт запуска дашборда создан: run_dashboard.py")


async def main():
    """Основная демонстрационная функция"""
    
    print("🎯 ДЕМОНСТРАЦИЯ СИСТЕМЫ ВИЗУАЛИЗАЦИИ")
    print("=" * 60)
    print("Торговая стратегия: Охота за ликвидностью")
    print("Этап 5: Визуализация и UI")
    print("=" * 60)
    
    # 1. Демонстрация интерактивных графиков
    demo_chart_visualizer()
    
    # 2. Демонстрация системы алертов
    await demo_alert_manager()
    
    # 3. Подготовка данных для дашборда
    create_sample_dashboard_data()
    
    # 4. Создание скрипта запуска дашборда
    create_launch_script()
    
    print("\n" + "=" * 60)
    print("✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 60)
    print("\n📁 Созданные файлы:")
    print("  📊 visualization_output/liquidity_hunt_chart_demo.html")
    print("  📈 visualization_output/strategy_comparison_demo.html")
    print("  🚨 alerts/alerts_*.jsonl")
    print("  📋 backtest_results/demo_*.json")
    print("  🚀 run_dashboard.py")
    
    print("\n🎨 Интерактивные графики:")
    print("  - Откройте .html файлы в браузере для просмотра")
    print("  - Поддерживается масштабирование, навигация")
    print("  - Полная разметка POI и зон ликвидности")
    
    print("\n🚨 Система алертов:")
    print("  - Поддержка Telegram, Email, Webhook")
    print("  - Умная приоритизация алертов")
    print("  - История и статистика")
    
    print("\n🖥️ Веб-дашборд:")
    print("  - Запустите: python run_dashboard.py")
    print("  - Откроется по адресу: http://localhost:8501")
    print("  - Реальное время + исторические данные")
    
    print("\n🎯 Этап 5 (Визуализация и UI) - ЗАВЕРШЕН!")
    print("✨ Готово к переходу к Этапу 6 (Production)")


if __name__ == "__main__":
    asyncio.run(main())