#!/usr/bin/env python3
"""
Упрощенная демонстрация системы бэк-тестинга
Работает независимо от других модулей системы
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from pathlib import Path

# Прямой импорт классов бэк-тестинга
from backtesting.trade import Trade, TradeDirection, TradeStatus
from backtesting.portfolio import Portfolio, PortfolioState
from backtesting.performance_metrics import PerformanceMetrics


def generate_sample_ohlc_data(start_date: datetime, end_date: datetime, interval_hours: int = 1) -> pd.DataFrame:
    """Генерация простых OHLC данных для тестирования"""
    
    # Создание временного ряда
    time_range = pd.date_range(start=start_date, end=end_date, freq=f'{interval_hours}H')
    
    # Симуляция цены с трендом и волатильностью
    np.random.seed(42)  # Для воспроизводимости
    
    initial_price = 50000.0  # Начальная цена
    volatility = 0.015  # 1.5% волатильность
    
    prices = []
    current_price = initial_price
    
    # Создание реалистичных движений цены
    for i in range(len(time_range)):
        # Добавление тренда (небольшой рост)
        trend = 0.0001  # 0.01% за час
        
        # Случайное изменение
        random_change = np.random.normal(0, volatility)
        
        # Применение изменений
        price_change = trend + random_change
        current_price *= (1 + price_change)
        
        prices.append(current_price)
    
    # Создание OHLC данных
    ohlc_data = []
    for i, (timestamp, close_price) in enumerate(zip(time_range, prices)):
        
        # Симуляция внутрисвечового движения
        noise = np.random.normal(0, 0.005)  # Меньшая волатильность для внутрисвечовых данных
        
        if i == 0:
            open_price = close_price
        else:
            open_price = prices[i-1]  # Открытие = закрытие предыдущей свечи
        
        # Высокая и низкая цены с небольшим шумом
        high_price = max(open_price, close_price) * (1 + abs(noise))
        low_price = min(open_price, close_price) * (1 - abs(noise))
        
        # Объем
        volume = np.random.uniform(500, 2000)
        
        ohlc_data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(ohlc_data)
    df.set_index('timestamp', inplace=True)
    
    return df


def simple_moving_average_strategy(data: pd.DataFrame, fast_period: int = 10, slow_period: int = 30) -> list:
    """Простая стратегия на основе скользящих средних"""
    
    # Расчет скользящих средних
    data[f'sma_{fast_period}'] = data['close'].rolling(window=fast_period).mean()
    data[f'sma_{slow_period}'] = data['close'].rolling(window=slow_period).mean()
    
    signals = []
    
    # Поиск пересечений
    for i in range(slow_period, len(data)):
        current_time = data.index[i]
        current_price = data['close'].iloc[i]
        
        fast_sma_current = data[f'sma_{fast_period}'].iloc[i]
        slow_sma_current = data[f'sma_{slow_period}'].iloc[i]
        fast_sma_prev = data[f'sma_{fast_period}'].iloc[i-1]
        slow_sma_prev = data[f'sma_{slow_period}'].iloc[i-1]
        
        # Проверка пересечений
        if (fast_sma_current > slow_sma_current and fast_sma_prev <= slow_sma_prev):
            # Бычье пересечение - сигнал на покупку
            signals.append({
                'timestamp': current_time,
                'action': 'BUY',
                'price': current_price,
                'stop_loss': current_price * 0.95,  # 5% стоп
                'take_profit': current_price * 1.08,  # 8% профит
                'reason': f'MA_bullish_cross_{fast_period}_{slow_period}',
                'confidence': 0.6
            })
            
        elif (fast_sma_current < slow_sma_current and fast_sma_prev >= slow_sma_prev):
            # Медвежье пересечение - сигнал на продажу
            signals.append({
                'timestamp': current_time,
                'action': 'SELL',
                'price': current_price,
                'stop_loss': current_price * 1.05,  # 5% стоп
                'take_profit': current_price * 0.92,  # 8% профит
                'reason': f'MA_bearish_cross_{fast_period}_{slow_period}',
                'confidence': 0.6
            })
    
    return signals


def run_simple_backtest():
    """Запуск упрощенного бэк-тестинга"""
    
    print("=== ДЕМОНСТРАЦИЯ СИСТЕМЫ БЭК-ТЕСТИНГА ===\n")
    
    # Параметры тестирования
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 6, 30)  # 6 месяцев данных
    symbol = "BTCUSDT"
    initial_balance = 10000.0
    
    print(f"Тестовый период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    print(f"Торговая пара: {symbol}")
    print(f"Начальный капитал: ${initial_balance:,.2f}")
    print(f"Стратегия: Скользящие средние (SMA 10/30)\n")
    
    # === ЭТАП 1: ПОДГОТОВКА ДАННЫХ ===
    print("ЭТАП 1: Генерация тестовых данных...")
    data = generate_sample_ohlc_data(start_date, end_date, interval_hours=1)
    print(f"✓ Сгенерировано {len(data)} часовых свечей")
    print(f"  Начальная цена: ${data['close'].iloc[0]:,.2f}")
    print(f"  Конечная цена: ${data['close'].iloc[-1]:,.2f}")
    print(f"  Изменение: {((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100:.2f}%\n")
    
    # === ЭТАП 2: СОЗДАНИЕ ПОРТФЕЛЯ ===
    print("ЭТАП 2: Инициализация портфеля...")
    portfolio = Portfolio(
        initial_balance=initial_balance,
        leverage=1.0,  # Без плеча
        commission_rate=0.001,  # 0.1% комиссия
        slippage=0.0005  # 0.05% проскальзывание
    )
    print(f"✓ Портфель создан с балансом ${portfolio.balance:,.2f}\n")
    
    # === ЭТАП 3: ГЕНЕРАЦИЯ СИГНАЛОВ ===
    print("ЭТАП 3: Генерация торговых сигналов...")
    signals = simple_moving_average_strategy(data, fast_period=10, slow_period=30)
    print(f"✓ Сгенерировано {len(signals)} торговых сигналов")
    
    # Показать первые несколько сигналов
    for i, signal in enumerate(signals[:3]):
        action = signal['action']
        price = signal['price']
        time = signal['timestamp'].strftime('%Y-%m-%d %H:%M')
        print(f"  Сигнал {i+1}: {action} по цене ${price:,.2f} в {time}")
    if len(signals) > 3:
        print(f"  ... и еще {len(signals) - 3} сигналов")
    print()
    
    # === ЭТАП 4: СИМУЛЯЦИЯ ТОРГОВЛИ ===
    print("ЭТАП 4: Запуск симуляции торговли...")
    
    trade_counter = 0
    total_processed = 0
    
    # Создание словаря сигналов по времени для быстрого поиска
    signals_by_time = {signal['timestamp']: signal for signal in signals}
    
    # Итерация по данным
    for timestamp, row in data.iterrows():
        current_price = row['close']
        total_processed += 1
        
        # Показ прогресса
        if total_processed % 500 == 0:
            progress = (total_processed / len(data)) * 100
            print(f"  Прогресс: {progress:.1f}% ({total_processed}/{len(data)})")
        
        # Обновление текущих цен для открытых позиций
        for trade in portfolio.open_trades.values():
            trade.current_price = current_price
        
        # Проверка стоп-лоссов и тейк-профитов
        closed_trades = portfolio.check_stop_losses_and_take_profits(
            {symbol: current_price}, timestamp
        )
        
        # Логирование закрытых сделок
        for trade in closed_trades:
            exit_reason = trade.exit_reason
            pnl = trade.pnl or 0
            pnl_pct = trade.pnl_percent or 0
            print(f"    Закрыта: {trade.direction.value} позиция, P&L: ${pnl:.2f} ({pnl_pct:.1f}%) - {exit_reason}")
        
        # Обработка новых сигналов
        if timestamp in signals_by_time:
            signal = signals_by_time[timestamp]
            
            # Расчет размера позиции (фиксированный размер 2% от баланса на сделку)
            risk_per_trade = 0.02  # 2% риска
            risk_amount = portfolio.available_balance * risk_per_trade
            
            if signal['action'] == 'BUY':
                stop_distance = signal['price'] - signal['stop_loss']
                if stop_distance > 0:
                    position_size = risk_amount / stop_distance
                    
                    # Ограничение размера позиции
                    max_position = (portfolio.available_balance * 0.95) / signal['price']
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
                            print(f"    Открыта LONG позиция {trade_id}: ${signal['price']:,.2f}")
            
            elif signal['action'] == 'SELL':
                stop_distance = signal['stop_loss'] - signal['price']
                if stop_distance > 0:
                    position_size = risk_amount / stop_distance
                    max_position = (portfolio.available_balance * 0.95) / signal['price']
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
                            print(f"    Открыта SHORT позиция {trade_id}: ${signal['price']:,.2f}")
        
        # Обновление эквити портфеля
        portfolio.update_equity(timestamp)
    
    # Закрытие всех открытых позиций в конце
    final_price = data['close'].iloc[-1]
    final_timestamp = data.index[-1]
    
    remaining_trades = list(portfolio.open_trades.keys())
    for trade_id in remaining_trades:
        trade = portfolio.close_trade(trade_id, final_price, final_timestamp, "end_of_test")
        if trade:
            pnl = trade.pnl or 0
            print(f"    Закрыта позиция {trade.id} (конец теста): P&L = ${pnl:.2f}")
    
    print(f"\n✓ Симуляция завершена! Всего сделок: {len(portfolio.trades)}\n")
    
    # === ЭТАП 5: АНАЛИЗ РЕЗУЛЬТАТОВ ===
    print("ЭТАП 5: Анализ результатов...")
    
    # Создание объекта метрик
    metrics = PerformanceMetrics(portfolio)
    
    # Получение базовой статистики
    summary = portfolio.get_performance_summary()
    
    print("=== ИТОГОВЫЕ РЕЗУЛЬТАТЫ ===")
    print(f"Начальный капитал:    ${summary['current_balance'] + summary['total_commission']:,.2f}")
    print(f"Финальный капитал:    ${summary['final_equity']:,.2f}")
    print(f"Чистая прибыль:       ${summary['final_equity'] - initial_balance:,.2f}")
    print(f"Общая доходность:     {summary['total_return_percent']:.2f}%")
    print(f"Общая комиссия:       ${summary['total_commission']:,.2f}")
    print()
    
    print("=== СТАТИСТИКА СДЕЛОК ===")
    print(f"Всего сделок:         {summary['total_trades']}")
    print(f"Прибыльных:           {summary['winning_trades']}")
    print(f"Убыточных:            {summary['losing_trades']}")
    print(f"Винрейт:              {summary['win_rate_percent']:.1f}%")
    print(f"Макс. просадка:       {summary['max_drawdown_percent']:.2f}%")
    print()
    
    # Детальные метрики
    try:
        detailed_metrics = metrics.get_comprehensive_metrics()
        if detailed_metrics:
            print("=== ДЕТАЛЬНЫЕ МЕТРИКИ ===")
            print(f"Коэф. Шарпа:          {detailed_metrics.get('sharpe_ratio', 'N/A')}")
            print(f"Средняя прибыль:      ${detailed_metrics.get('avg_profit', 0):.2f}")
            print(f"Средний убыток:       ${detailed_metrics.get('avg_loss', 0):.2f}")
            print(f"Profit Factor:        {detailed_metrics.get('profit_factor', 'N/A')}")
            print(f"Макс. прибыль:        ${detailed_metrics.get('largest_win', 0):.2f}")
            print(f"Макс. убыток:         ${detailed_metrics.get('largest_loss', 0):.2f}")
            
            if detailed_metrics.get('avg_duration_hours'):
                print(f"Средняя длительность: {detailed_metrics['avg_duration_hours']:.1f} часов")
    except Exception as e:
        print(f"Ошибка расчета детальных метрик: {e}")
    
    print()
    
    # === ЭТАП 6: СОХРАНЕНИЕ РЕЗУЛЬТАТОВ ===
    print("ЭТАП 6: Сохранение результатов...")
    
    try:
        results_dir = Path("backtest_results")
        results_dir.mkdir(exist_ok=True)
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"simple_backtest_{timestamp_str}"
        
        # Отчет
        report = metrics.generate_report()
        with open(results_dir / f"{base_filename}_report.txt", 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Краткая сводка
        with open(results_dir / f"{base_filename}_summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # Детальные метрики
        try:
            detailed_metrics = metrics.get_comprehensive_metrics()
            if detailed_metrics:
                with open(results_dir / f"{base_filename}_metrics.json", 'w', encoding='utf-8') as f:
                    json.dump(detailed_metrics, f, ensure_ascii=False, indent=2)
        except:
            pass
        
        # Сделки
        trades_data = [trade.to_dict() for trade in portfolio.trades]
        with open(results_dir / f"{base_filename}_trades.json", 'w', encoding='utf-8') as f:
            json.dump(trades_data, f, ensure_ascii=False, indent=2)
        
        # Эквити кривая
        try:
            equity_df = portfolio.to_dataframe()
            if not equity_df.empty:
                equity_df.to_csv(results_dir / f"{base_filename}_equity.csv", index=False)
        except:
            pass
        
        print(f"✓ Результаты сохранены в папку: {results_dir}")
        print(f"  Базовое имя файлов: {base_filename}")
        
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
    
    print("\n=== ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА ===")
    
    return portfolio, metrics


if __name__ == "__main__":
    try:
        print("Запуск демонстрации системы бэк-тестинга...\n")
        portfolio, metrics = run_simple_backtest()
        
        # Финальная проверка
        print(f"\n✅ Демонстрация прошла успешно!")
        print(f"📊 Всего сделок: {len(portfolio.trades)}")
        print(f"💰 Финальный результат: {((portfolio.equity / portfolio.initial_balance) - 1) * 100:.2f}%")
        
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении демонстрации: {e}")
        import traceback
        traceback.print_exc()