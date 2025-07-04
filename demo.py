"""
Демонстрация работы торговой системы "Охота за ликвидностью"
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

from analysis.market_structure import MarketStructureAnalyzer
from analysis.liquidity_detector import LiquidityDetector
from core.data_types import TimeFrame, SwingPoint
from config import get_config


def generate_sample_data(bars: int = 1000) -> pd.DataFrame:
    """Генерация примера рыночных данных"""
    
    # Создаем реалистичные данные BTC/USDT
    np.random.seed(42)
    
    start_time = datetime.now() - timedelta(hours=bars)
    timestamps = [start_time + timedelta(hours=i) for i in range(bars)]
    
    # Начальная цена
    initial_price = 45000.0
    
    # Генерируем цены с трендом и волатильностью
    returns = np.random.normal(0.001, 0.02, bars)  # Средний рост 0.1% с волатильностью 2%
    
    # Добавляем тренд
    trend = np.linspace(0, 0.3, bars)  # 30% роста за период
    returns += trend / bars
    
    # Генерируем цены
    prices = [initial_price]
    for i in range(1, bars):
        new_price = prices[-1] * (1 + returns[i])
        prices.append(new_price)
    
    # Создаем OHLCV данные
    data = []
    for i in range(bars):
        price = prices[i]
        
        # Генерируем OHLC с реалистичным спредом
        spread = price * 0.002  # 0.2% спред
        
        open_price = price + np.random.uniform(-spread/2, spread/2)
        close_price = price + np.random.uniform(-spread/2, spread/2)
        
        high_price = max(open_price, close_price) + abs(np.random.normal(0, spread/4))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, spread/4))
        
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': timestamps[i],
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    return df


def demo_market_structure_analysis():
    """Демонстрация анализа структуры рынка"""
    print("\n🏗️ АНАЛИЗ СТРУКТУРЫ РЫНКА")
    print("=" * 50)
    
    # Генерируем данные
    data = generate_sample_data(500)
    print(f"📊 Сгенерировано {len(data)} свечей")
    
    # Инициализируем анализатор
    analyzer = MarketStructureAnalyzer()
    
    # Анализируем структуру
    structure = analyzer.analyze_structure(data)
    print(f"📈 Структура рынка: {structure.value}")
    
    # Рассчитываем силу тренда
    trend_strength = analyzer.calculate_trend_strength(data)
    print(f"💪 Сила тренда: {trend_strength:.2f}")
    
    # Находим свинг-точки
    swing_highs, swing_lows = analyzer.detect_swings(data)
    print(f"🔄 Свинг-точки: {len(swing_highs)} максимумов, {len(swing_lows)} минимумов")
    
    # Показываем последние свинги
    if swing_highs:
        latest_high = max(swing_highs, key=lambda x: x.timestamp)
        print(f"   📈 Последний максимум: {latest_high.price:.2f} (сила: {latest_high.strength:.2f})")
    
    if swing_lows:
        latest_low = max(swing_lows, key=lambda x: x.timestamp)
        print(f"   📉 Последний минимум: {latest_low.price:.2f} (сила: {latest_low.strength:.2f})")
    
    return data, swing_highs, swing_lows


def demo_liquidity_detection(data, swing_highs, swing_lows):
    """Демонстрация детекции ликвидности"""
    print("\n💧 ДЕТЕКЦИЯ ЛИКВИДНОСТИ")
    print("=" * 50)
    
    # Инициализируем детектор
    detector = LiquidityDetector()
    
    # Объединяем все свинг-точки
    all_swings = swing_highs + swing_lows
    print(f"🎯 Анализируем {len(all_swings)} свинг-точек")
    
    # Детектируем пулы ликвидности
    liquidity_pools = detector.detect_liquidity_pools(data, all_swings)
    print(f"💰 Найдено {len(liquidity_pools)} пулов ликвидности")
    
    # Группируем по типам
    bsl_pools = [p for p in liquidity_pools if p.liquidity_type.value == "buy_side_liquidity"]
    ssl_pools = [p for p in liquidity_pools if p.liquidity_type.value == "sell_side_liquidity"]
    
    print(f"   🔴 BSL пулы: {len(bsl_pools)}")
    print(f"   🟢 SSL пулы: {len(ssl_pools)}")
    
    # Показываем топ-5 самых сильных пулов
    top_pools = sorted(liquidity_pools, key=lambda p: p.strength, reverse=True)[:5]
    
    print("\n🏆 ТОП-5 ПУЛОВ ЛИКВИДНОСТИ:")
    for i, pool in enumerate(top_pools, 1):
        pool_type = "BSL" if pool.liquidity_type.value == "buy_side_liquidity" else "SSL"
        print(f"   {i}. {pool_type} @ {pool.price:.2f} "
              f"(сила: {pool.strength:.2f}, объем: {pool.volume:.0f})")
    
    # Проверяем снятие ликвидности
    current_price = data['close'].iloc[-1]
    swept_pools = detector.check_liquidity_sweep(current_price, liquidity_pools)
    
    if swept_pools:
        print(f"\n⚡ СНЯТО ЛИКВИДНОСТИ: {len(swept_pools)} пулов")
        for pool in swept_pools:
            pool_type = "BSL" if pool.liquidity_type.value == "buy_side_liquidity" else "SSL"
            print(f"   💥 {pool_type} @ {pool.price:.2f}")
    else:
        print(f"\n✅ Текущая цена {current_price:.2f} - ликвидность не снята")
    
    return liquidity_pools


def demo_human_like_thinking():
    """Демонстрация человекоподобного мышления"""
    print("\n🧠 ЧЕЛОВЕКОПОДОБНОЕ МЫШЛЕНИЕ")
    print("=" * 50)
    
    # Симулируем контекст торговли
    recent_trades = [
        {"result": "win", "pnl": 150, "duration": 2.5},
        {"result": "loss", "pnl": -80, "duration": 1.2},
        {"result": "win", "pnl": 200, "duration": 4.1},
        {"result": "loss", "pnl": -120, "duration": 0.8},
        {"result": "win", "pnl": 300, "duration": 6.2},
    ]
    
    # Рассчитываем статистику
    total_pnl = sum(t["pnl"] for t in recent_trades)
    win_rate = len([t for t in recent_trades if t["result"] == "win"]) / len(recent_trades)
    avg_win = np.mean([t["pnl"] for t in recent_trades if t["result"] == "win"])
    avg_loss = abs(np.mean([t["pnl"] for t in recent_trades if t["result"] == "loss"]))
    
    print(f"📊 Последние {len(recent_trades)} сделок:")
    print(f"   💰 Общий P&L: ${total_pnl}")
    print(f"   🎯 Винрейт: {win_rate:.1%}")
    print(f"   📈 Средняя прибыль: ${avg_win:.0f}")
    print(f"   📉 Средний убыток: ${avg_loss:.0f}")
    
    # Эмоциональные факторы
    if total_pnl > 0:
        greed_factor = min(total_pnl / 1000, 0.2)  # Максимум 20% жадности
        fear_factor = 0.0
        mood = "Оптимистичное"
    else:
        fear_factor = min(abs(total_pnl) / 1000, 0.3)  # Максимум 30% страха
        greed_factor = 0.0
        mood = "Осторожное"
    
    print(f"\n🎭 ЭМОЦИОНАЛЬНОЕ СОСТОЯНИЕ:")
    print(f"   😊 Настроение: {mood}")
    print(f"   😰 Фактор страха: {fear_factor:.2f}")
    print(f"   🤑 Фактор жадности: {greed_factor:.2f}")
    
    # Адаптация параметров
    base_confluence = 0.7
    base_position_size = 0.02
    
    if win_rate < 0.4:
        # Плохая серия - становимся консервативнее
        adapted_confluence = base_confluence * 1.3
        adapted_position_size = base_position_size * 0.7
        adaptation = "Консервативная (плохая серия)"
    elif win_rate > 0.8:
        # Хорошая серия - можем быть агрессивнее
        adapted_confluence = base_confluence * 0.9
        adapted_position_size = base_position_size * 1.2
        adaptation = "Агрессивная (хорошая серия)"
    else:
        adapted_confluence = base_confluence
        adapted_position_size = base_position_size
        adaptation = "Стандартная"
    
    print(f"\n⚙️ АДАПТАЦИЯ ПАРАМЕТРОВ:")
    print(f"   🎛️ Режим: {adaptation}")
    print(f"   🎯 Конфлюенция: {base_confluence:.2f} → {adapted_confluence:.2f}")
    print(f"   💼 Размер позиции: {base_position_size:.1%} → {adapted_position_size:.1%}")


def main():
    """Главная функция демонстрации"""
    print("🎯 ДЕМОНСТРАЦИЯ ТОРГОВОЙ СИСТЕМЫ 'ОХОТА ЗА ЛИКВИДНОСТЬЮ'")
    print("=" * 70)
    
    try:
        # Демонстрация анализа структуры рынка
        data, swing_highs, swing_lows = demo_market_structure_analysis()
        
        # Демонстрация детекции ликвидности
        liquidity_pools = demo_liquidity_detection(data, swing_highs, swing_lows)
        
        # Демонстрация человекоподобного мышления
        demo_human_like_thinking()
        
        print("\n✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
        print("=" * 70)
        print("🚀 Для полного функционала запустите: python main.py")
        print("📖 Документация: README.md")
        
    except Exception as e:
        logger.error(f"Ошибка в демонстрации: {e}")
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    main()