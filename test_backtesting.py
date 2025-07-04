#!/usr/bin/env python3
"""
Тестовый скрипт для демонстрации системы бэк-тестинга
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Добавление путей для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtesting.portfolio import Portfolio
from backtesting.trade import Trade, TradeDirection
from backtesting.performance_metrics import PerformanceMetrics
from config import Config


def generate_sample_data(start_date: datetime, end_date: datetime, symbol: str = "BTCUSDT") -> pd.DataFrame:
    """Генерация тестовых данных для демонстрации"""
    
    # Создание временного ряда
    time_range = pd.date_range(start=start_date, end=end_date, freq='1H')
    
    # Симуляция цены с трендом и волатильностью
    np.random.seed(42)  # Для воспроизводимости
    
    initial_price = 50000.0  # Начальная цена BTC
    price_changes = np.random.normal(0, 0.01, len(time_range))  # 1% волатильность
    
    # Добавление трендовой составляющей
    trend = np.linspace(0, 0.2, len(time_range))  # 20% рост за период
    
    prices = []
    current_price = initial_price
    
    for i, change in enumerate(price_changes):
        # Применение тренда и случайного изменения
        trend_factor = 1 + trend[i] / len(time_range)
        random_factor = 1 + change
        current_price *= trend_factor * random_factor
        prices.append(current_price)
    
    # Создание OHLCV данных
    data = []
    for i, (timestamp, price) in enumerate(zip(time_range, prices)):
        # Симуляция OHLC на основе цены закрытия
        noise = np.random.normal(0, 0.005)  # Меньший шум для внутрисвечовых движений
        
        open_price = price * (1 + noise)
        high_price = max(open_price, price) * (1 + abs(noise))
        low_price = min(open_price, price) * (1 - abs(noise))
        close_price = price
        volume = np.random.uniform(100, 1000)
        
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
    
    return df


def simulate_trading_signals(data: pd.DataFrame) -> list:
    """Генерация простых торговых сигналов для тестирования"""
    
    signals = []
    
    # Простая стратегия на основе скользящих средних
    data['sma_20'] = data['close'].rolling(window=20).mean()
    data['sma_50'] = data['close'].rolling(window=50).mean()
    
    # Поиск пересечений скользящих средних
    for i in range(50, len(data)):
        current_time = data.index[i]
        
        # Сигнал на покупку: быстрая SMA пересекает медленную снизу вверх
        if (data['sma_20'].iloc[i] > data['sma_50'].iloc[i] and 
            data['sma_20'].iloc[i-1] <= data['sma_50'].iloc[i-1]):
            
            signals.append({
                'timestamp': current_time,
                'action': 'BUY',
                'price': data['close'].iloc[i],
                'stop_loss': data['close'].iloc[i] * 0.95,  # 5% стоп-лосс
                'take_profit': data['close'].iloc[i] * 1.10,  # 10% тейк-профит
                'reason': 'SMA_bullish_crossover',
                'confidence': 0.7
            })
        
        # Сигнал на продажу: быстрая SMA пересекает медленную сверху вниз
        elif (data['sma_20'].iloc[i] < data['sma_50'].iloc[i] and 
              data['sma_20'].iloc[i-1] >= data['sma_50'].iloc[i-1]):
            
            signals.append({
                'timestamp': current_time,
                'action': 'SELL',
                'price': data['close'].iloc[i],
                'stop_loss': data['close'].iloc[i] * 1.05,  # 5% стоп-лосс
                'take_profit': data['close'].iloc[i] * 0.90,  # 10% тейк-профит
                'reason': 'SMA_bearish_crossover',
                'confidence': 0.7
            })
    
    return signals


def run_backtest_simulation():
    """Запуск симуляции бэк-тестинга"""
    
    print("=== ЗАПУСК ТЕСТИРОВАНИЯ СИСТЕМЫ БЭК-ТЕСТИНГА ===\n")
    
    # Параметры тестирования
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 3, 31)  # 3 месяца данных
    symbol = "BTCUSDT"
    initial_balance = 10000.0
    
    print(f"Период тестирования: {start_date} - {end_date}")
    print(f"Торговая пара: {symbol}")
    print(f"Начальный баланс: ${initial_balance:,.2f}\n")
    
    # Создание портфеля
    portfolio = Portfolio(
        initial_balance=initial_balance,
        leverage=1.0,
        commission_rate=0.001,  # 0.1% комиссия
        slippage=0.0005  # 0.05% проскальзывание
    )
    
    # Генерация тестовых данных
    print("Генерация тестовых данных...")
    data = generate_sample_data(start_date, end_date, symbol)
    print(f"Сгенерировано {len(data)} свечей\n")
    
    # Генерация торговых сигналов
    print("Генерация торговых сигналов...")
    signals = simulate_trading_signals(data)
    print(f"Сгенерировано {len(signals)} сигналов\n")
    
    # Симуляция торговли
    print("Запуск симуляции торговли...")
    
    active_trades = {}
    trade_counter = 0
    
    for timestamp, row in data.iterrows():
        current_price = row['close']
        
        # Обновление текущих цен для расчета нереализованной прибыли
        for trade in portfolio.open_trades.values():
            trade.current_price = current_price
        
        # Проверка стоп-лоссов и тейк-профитов
        closed_trades = portfolio.check_stop_losses_and_take_profits(
            {symbol: current_price}, timestamp
        )
        
        for trade in closed_trades:
            print(f"Закрыта сделка {trade.id}: P&L = ${trade.pnl:.2f} ({trade.pnl_percent:.2f}%)")
        
        # Обработка новых сигналов
        for signal in signals:
            if signal['timestamp'] == timestamp:
                
                if signal['action'] == 'BUY':
                    # Расчет размера позиции (1% риска от баланса)
                    risk_amount = portfolio.available_balance * 0.01
                    stop_distance = signal['price'] - signal['stop_loss']
                    
                    if stop_distance > 0:
                        position_size = risk_amount / stop_distance
                        
                        # Ограничение размера позиции доступным балансом
                        max_position = portfolio.available_balance / signal['price'] * 0.95
                        position_size = min(position_size, max_position)
                        
                        if position_size > 0:
                            trade_counter += 1
                            trade_id = f"trade_{trade_counter:04d}"
                            
                            trade = portfolio.open_trade(
                                trade_id=trade_id,
                                symbol=symbol,
                                direction=TradeDirection.LONG,
                                quantity=position_size,
                                price=signal['price'],
                                timestamp=timestamp,
                                stop_loss=signal['stop_loss'],
                                take_profit=signal['take_profit'],
                                strategy_context={
                                    'reason': signal['reason'],
                                    'confidence': signal['confidence']
                                }
                            )
                            
                            if trade:
                                print(f"Открыта позиция LONG {trade_id}: ${signal['price']:.2f}, размер: {position_size:.6f}")
                
                elif signal['action'] == 'SELL':
                    # Аналогично для коротких позиций
                    risk_amount = portfolio.available_balance * 0.01
                    stop_distance = signal['stop_loss'] - signal['price']
                    
                    if stop_distance > 0:
                        position_size = risk_amount / stop_distance
                        max_position = portfolio.available_balance / signal['price'] * 0.95
                        position_size = min(position_size, max_position)
                        
                        if position_size > 0:
                            trade_counter += 1
                            trade_id = f"trade_{trade_counter:04d}"
                            
                            trade = portfolio.open_trade(
                                trade_id=trade_id,
                                symbol=symbol,
                                direction=TradeDirection.SHORT,
                                quantity=position_size,
                                price=signal['price'],
                                timestamp=timestamp,
                                stop_loss=signal['stop_loss'],
                                take_profit=signal['take_profit'],
                                strategy_context={
                                    'reason': signal['reason'],
                                    'confidence': signal['confidence']
                                }
                            )
                            
                            if trade:
                                print(f"Открыта позиция SHORT {trade_id}: ${signal['price']:.2f}, размер: {position_size:.6f}")
        
        # Обновление эквити портфеля
        portfolio.update_equity(timestamp)
    
    # Закрытие всех открытых позиций в конце периода
    final_price = data['close'].iloc[-1]
    final_timestamp = data.index[-1]
    
    remaining_trades = list(portfolio.open_trades.keys())
    for trade_id in remaining_trades:
        trade = portfolio.close_trade(trade_id, final_price, final_timestamp, "end_of_period")
        if trade:
            print(f"Закрыта сделка {trade.id} (конец периода): P&L = ${trade.pnl:.2f}")
    
    print(f"\nСимуляция завершена! Всего сделок: {len(portfolio.trades)}\n")
    
    # Анализ результатов
    print("=== АНАЛИЗ РЕЗУЛЬТАТОВ ===\n")
    
    metrics = PerformanceMetrics(portfolio)
    performance_data = metrics.get_comprehensive_metrics()
    
    # Краткая сводка
    summary = portfolio.get_performance_summary()
    
    print(f"Начальный баланс: ${summary['current_balance'] + summary['total_commission']:,.2f}")
    print(f"Финальный капитал: ${summary['final_equity']:,.2f}")
    print(f"Общая доходность: {summary['total_return_percent']:.2f}%")
    print(f"Всего сделок: {summary['total_trades']}")
    print(f"Прибыльных: {summary['winning_trades']}")
    print(f"Убыточных: {summary['losing_trades']}")
    print(f"Винрейт: {summary['win_rate_percent']:.2f}%")
    print(f"Максимальная просадка: {summary['max_drawdown_percent']:.2f}%")
    print(f"Общая комиссия: ${summary['total_commission']:.2f}")
    
    # Детальный отчет
    if performance_data:
        print(f"\n=== ДЕТАЛЬНЫЕ МЕТРИКИ ===")
        print(f"Коэффициент Шарпа: {performance_data.get('sharpe_ratio', 'N/A')}")
        print(f"Коэффициент Калмара: {performance_data.get('calmar_ratio', 'N/A')}")
        print(f"Средняя прибыль: ${performance_data.get('avg_profit', 0):.2f}")
        print(f"Средний убыток: ${performance_data.get('avg_loss', 0):.2f}")
        print(f"Profit Factor: {performance_data.get('profit_factor', 'N/A')}")
        print(f"Максимальная прибыль: ${performance_data.get('largest_win', 0):.2f}")
        print(f"Максимальный убыток: ${performance_data.get('largest_loss', 0):.2f}")
    
    # Генерация полного отчета
    full_report = metrics.generate_report()
    
    # Сохранение результатов
    print(f"\n=== СОХРАНЕНИЕ РЕЗУЛЬТАТОВ ===")
    
    try:
        from pathlib import Path
        import json
        
        results_dir = Path("backtest_results")
        results_dir.mkdir(exist_ok=True)
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Сохранение отчета
        with open(results_dir / f"test_backtest_report_{timestamp_str}.txt", 'w', encoding='utf-8') as f:
            f.write(full_report)
        
        # Сохранение метрик
        if performance_data:
            with open(results_dir / f"test_backtest_metrics_{timestamp_str}.json", 'w', encoding='utf-8') as f:
                json.dump(performance_data, f, ensure_ascii=False, indent=2)
        
        # Сохранение эквити кривой
        equity_df = portfolio.to_dataframe()
        if not equity_df.empty:
            equity_df.to_csv(results_dir / f"test_backtest_equity_{timestamp_str}.csv", index=False)
        
        # Сохранение логов сделок
        trades_data = [trade.to_dict() for trade in portfolio.trades]
        with open(results_dir / f"test_backtest_trades_{timestamp_str}.json", 'w', encoding='utf-8') as f:
            json.dump(trades_data, f, ensure_ascii=False, indent=2)
        
        print(f"Результаты сохранены в папку: {results_dir}")
        print(f"Файлы:")
        print(f"  - test_backtest_report_{timestamp_str}.txt")
        print(f"  - test_backtest_metrics_{timestamp_str}.json") 
        print(f"  - test_backtest_equity_{timestamp_str}.csv")
        print(f"  - test_backtest_trades_{timestamp_str}.json")
        
    except Exception as e:
        print(f"Ошибка сохранения результатов: {e}")
    
    print(f"\n=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")
    
    return portfolio, metrics


if __name__ == "__main__":
    try:
        portfolio, metrics = run_backtest_simulation()
        print("\nТестирование системы бэк-тестинга прошло успешно!")
        
    except Exception as e:
        print(f"Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()