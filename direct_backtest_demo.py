#!/usr/bin/env python3
"""
Прямая демонстрация системы бэк-тестинга
Минимальные зависимости, прямой импорт модулей
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from pathlib import Path

# Прямой импорт без использования __init__.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Прямой импорт модулей
from backtesting.trade import Trade, TradeDirection, TradeStatus
from backtesting.portfolio import Portfolio, PortfolioState

# Создадим упрощенную версию PerformanceMetrics прямо здесь
class SimpleMetrics:
    """Упрощенные метрики производительности"""
    
    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.trades = portfolio.trades
        self.equity_curve = portfolio.equity_curve
        
    def generate_report(self) -> str:
        """Генерация простого отчета"""
        
        closed_trades = [t for t in self.trades if not t.is_open]
        
        if not closed_trades:
            return "Нет закрытых сделок для анализа"
        
        # Базовые метрики
        total_trades = len(closed_trades)
        winning_trades = len([t for t in closed_trades if t.is_profitable])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        profits = [t.pnl for t in closed_trades if t.is_profitable and t.pnl is not None]
        losses = [t.pnl for t in closed_trades if not t.is_profitable and t.pnl is not None]
        
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 0
        
        total_return = ((self.portfolio.equity - self.portfolio.initial_balance) / self.portfolio.initial_balance) * 100
        
        report = f"""
=== ОТЧЕТ ПО ПРОИЗВОДИТЕЛЬНОСТИ ===

ОСНОВНЫЕ ПОКАЗАТЕЛИ:
- Общая доходность: {total_return:.2f}%
- Начальный баланс: ${self.portfolio.initial_balance:,.2f}
- Финальный капитал: ${self.portfolio.equity:,.2f}

СТАТИСТИКА СДЕЛОК:
- Всего сделок: {total_trades}
- Прибыльных: {winning_trades}
- Убыточных: {losing_trades}
- Винрейт: {win_rate:.2f}%
- Средняя прибыль: ${avg_profit:.2f}
- Средний убыток: ${avg_loss:.2f}
- Общая комиссия: ${self.portfolio.total_commission:.2f}
"""
        return report


def generate_test_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Генерация тестовых данных"""
    
    time_range = pd.date_range(start=start_date, end=end_date, freq='1H')
    
    np.random.seed(42)
    initial_price = 50000.0
    current_price = initial_price
    
    data = []
    for timestamp in time_range:
        # Простое случайное движение цены
        change = np.random.normal(0, 0.01)  # 1% волатильность
        current_price *= (1 + change)
        
        # OHLC данные
        noise = np.random.normal(0, 0.005)
        open_price = current_price
        high_price = current_price * (1 + abs(noise))
        low_price = current_price * (1 - abs(noise))
        close_price = current_price
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data, index=time_range)
    return df


def simple_sma_signals(data: pd.DataFrame) -> list:
    """Простые сигналы на основе SMA"""
    
    data['sma_10'] = data['close'].rolling(10).mean()
    data['sma_30'] = data['close'].rolling(30).mean()
    
    signals = []
    
    for i in range(30, len(data)):
        if (data['sma_10'].iloc[i] > data['sma_30'].iloc[i] and 
            data['sma_10'].iloc[i-1] <= data['sma_30'].iloc[i-1]):
            
            signals.append({
                'time': data.index[i],
                'action': 'BUY',
                'price': data['close'].iloc[i],
                'stop': data['close'].iloc[i] * 0.95,
                'target': data['close'].iloc[i] * 1.08
            })
            
        elif (data['sma_10'].iloc[i] < data['sma_30'].iloc[i] and 
              data['sma_10'].iloc[i-1] >= data['sma_30'].iloc[i-1]):
            
            signals.append({
                'time': data.index[i],
                'action': 'SELL', 
                'price': data['close'].iloc[i],
                'stop': data['close'].iloc[i] * 1.05,
                'target': data['close'].iloc[i] * 0.92
            })
    
    return signals


def run_demo():
    """Запуск демонстрации"""
    
    print("=== ДЕМОНСТРАЦИЯ БЭК-ТЕСТИНГА ===\n")
    
    # Параметры
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 3, 31)
    initial_balance = 10000.0
    symbol = "BTCUSDT"
    
    print(f"Период: {start_date.date()} - {end_date.date()}")
    print(f"Начальный капитал: ${initial_balance:,}")
    print(f"Символ: {symbol}\n")
    
    # Данные
    print("Генерация данных...")
    data = generate_test_data(start_date, end_date)
    print(f"✓ Создано {len(data)} свечей")
    print(f"  Цена в начале: ${data['close'].iloc[0]:,.0f}")
    print(f"  Цена в конце: ${data['close'].iloc[-1]:,.0f}\n")
    
    # Портфель
    print("Создание портфеля...")
    portfolio = Portfolio(
        initial_balance=initial_balance,
        leverage=1.0,
        commission_rate=0.001,
        slippage=0.0005
    )
    print(f"✓ Портфель создан\n")
    
    # Сигналы
    print("Генерация сигналов...")
    signals = simple_sma_signals(data)
    print(f"✓ Создано {len(signals)} сигналов\n")
    
    # Симуляция
    print("Запуск симуляции...")
    trade_count = 0
    
    # Создание индекса сигналов для быстрого поиска
    signals_dict = {sig['time']: sig for sig in signals}
    
    for i, (timestamp, row) in enumerate(data.iterrows()):
        current_price = float(row['close'])
        
        # Прогресс
        if i % 500 == 0:
            print(f"  Обработано {i}/{len(data)} свечей")
        
        # Обновление цен для открытых позиций
        for trade in portfolio.open_trades.values():
            trade.current_price = current_price
        
        # Проверка стопов и целей
        closed = portfolio.check_stop_losses_and_take_profits(
            {symbol: current_price}, timestamp
        )
        
        for trade in closed:
            pnl = trade.pnl or 0
            print(f"    Закрыта {trade.direction.value}: P&L ${pnl:.0f}")
        
        # Новые сигналы
        if timestamp in signals_dict:
            signal = signals_dict[timestamp]
            
            risk_amount = portfolio.available_balance * 0.02  # 2% риска
            
            if signal['action'] == 'BUY':
                stop_distance = signal['price'] - signal['stop']
                if stop_distance > 0:
                    size = risk_amount / stop_distance
                    max_size = portfolio.available_balance * 0.9 / signal['price']
                    size = min(size, max_size)
                    
                    if size > 0:
                        trade_count += 1
                        trade = portfolio.open_trade(
                            trade_id=f"T{trade_count:03d}",
                            symbol=symbol,
                            direction=TradeDirection.LONG,
                            quantity=size,
                            price=signal['price'],
                            timestamp=timestamp,
                            stop_loss=signal['stop'],
                            take_profit=signal['target']
                        )
                        if trade:
                            print(f"    Открыта LONG: ${signal['price']:,.0f}")
            
            elif signal['action'] == 'SELL':
                stop_distance = signal['stop'] - signal['price']
                if stop_distance > 0:
                    size = risk_amount / stop_distance
                    max_size = portfolio.available_balance * 0.9 / signal['price']
                    size = min(size, max_size)
                    
                    if size > 0:
                        trade_count += 1
                        trade = portfolio.open_trade(
                            trade_id=f"T{trade_count:03d}",
                            symbol=symbol,
                            direction=TradeDirection.SHORT,
                            quantity=size,
                            price=signal['price'],
                            timestamp=timestamp,
                            stop_loss=signal['stop'],
                            take_profit=signal['target']
                        )
                        if trade:
                            print(f"    Открыта SHORT: ${signal['price']:,.0f}")
        
        # Обновление эквити
        portfolio.update_equity(timestamp)
    
    # Закрытие открытых позиций
    final_price = float(data['close'].iloc[-1])
    for trade_id in list(portfolio.open_trades.keys()):
        trade = portfolio.close_trade(trade_id, final_price, data.index[-1], "конец теста")
        if trade:
            pnl = trade.pnl or 0
            print(f"    Закрыта финальная: P&L ${pnl:.0f}")
    
    print(f"\n✓ Симуляция завершена!\n")
    
    # Результаты
    print("РЕЗУЛЬТАТЫ:")
    summary = portfolio.get_performance_summary()
    
    print(f"  Начальный капитал: ${summary['current_balance'] + summary['total_commission']:,.0f}")
    print(f"  Финальный капитал: ${summary['final_equity']:,.0f}")
    print(f"  Прибыль/убыток:    ${summary['final_equity'] - initial_balance:,.0f}")
    print(f"  Доходность:        {summary['total_return_percent']:.1f}%")
    print(f"  Всего сделок:      {summary['total_trades']}")
    print(f"  Винрейт:           {summary['win_rate_percent']:.1f}%")
    print(f"  Макс. просадка:    {summary['max_drawdown_percent']:.1f}%")
    print(f"  Комиссии:          ${summary['total_commission']:.0f}")
    
    # Сохранение
    print("\nСохранение результатов...")
    try:
        results_dir = Path("backtest_results")
        results_dir.mkdir(exist_ok=True)
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Простой отчет
        metrics = SimpleMetrics(portfolio)
        report = metrics.generate_report()
        
        with open(results_dir / f"demo_report_{timestamp_str}.txt", 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Сводка
        with open(results_dir / f"demo_summary_{timestamp_str}.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # Сделки
        trades_data = [trade.to_dict() for trade in portfolio.trades]
        with open(results_dir / f"demo_trades_{timestamp_str}.json", 'w', encoding='utf-8') as f:
            json.dump(trades_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Файлы сохранены в {results_dir}/")
        print(f"  Базовое имя: demo_*_{timestamp_str}.*")
        
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
    
    print("\n=== ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА ===")
    
    return portfolio


if __name__ == "__main__":
    try:
        print("Запуск прямой демонстрации бэк-тестинга...\n")
        portfolio = run_demo()
        
        print(f"\n✅ Успешно! Финальный результат:")
        profit_pct = ((portfolio.equity / portfolio.initial_balance) - 1) * 100
        print(f"   Доходность: {profit_pct:.1f}%")
        print(f"   Сделок: {len(portfolio.trades)}")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()