"""
Основной движок бэк-тестинга для стратегии "Охота за ликвидностью"
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import uuid
import asyncio
from pathlib import Path
import json

from .portfolio import Portfolio
from .performance_metrics import PerformanceMetrics
from .trade import Trade, TradeDirection

# Импорт основных компонентов стратегии
import sys
sys.path.append('..')

from data.data_provider import DataProvider
from analysis.market_structure import MarketStructureAnalyzer
from analysis.liquidity_detector import LiquidityDetector
from analysis.poi_identifier import POIIdentifier
from trading.signal_generator import SignalGenerator
from trading.risk_manager import RiskManager
from config import Config


class BacktestEngine:
    """
    Основной движок бэк-тестинга
    """
    
    def __init__(self, 
                 config: Config,
                 initial_balance: float = 10000.0,
                 leverage: float = 1.0,
                 commission_rate: float = 0.001,
                 slippage: float = 0.0001):
        """
        Инициализация движка бэк-тестинга
        
        Args:
            config: Конфигурация системы
            initial_balance: Начальный баланс
            leverage: Плечо
            commission_rate: Комиссия
            slippage: Проскальзывание
        """
        self.config = config
        
        # Инициализация портфеля
        self.portfolio = Portfolio(
            initial_balance=initial_balance,
            leverage=leverage,
            commission_rate=commission_rate,
            slippage=slippage
        )
        
        # Компоненты стратегии
        self.data_provider = DataProvider(config)
        self.market_structure = MarketStructureAnalyzer(config)
        self.liquidity_detector = LiquidityDetector(config)
        self.poi_identifier = POIIdentifier(config)
        self.signal_generator = SignalGenerator(config)
        self.risk_manager = RiskManager(config)
        
        # Параметры бэк-теста
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.symbol = "BTCUSDT"
        self.timeframes = ["1d", "4h", "1h", "15m", "5m", "1m"]
        
        # Результаты
        self.results: Optional[PerformanceMetrics] = None
        self.trades_log: List[Dict] = []
        
    def run_backtest(self, 
                    symbol: str,
                    start_date: datetime,
                    end_date: datetime,
                    timeframes: List[str] = None) -> PerformanceMetrics:
        """
        Запуск бэк-тестинга
        
        Args:
            symbol: Торговая пара
            start_date: Дата начала
            end_date: Дата окончания
            timeframes: Список таймфреймов
        
        Returns:
            Метрики производительности
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        
        if timeframes:
            self.timeframes = timeframes
        
        print(f"Запуск бэк-тестинга {symbol} с {start_date} по {end_date}")
        
        # Загрузка данных
        print("Загрузка исторических данных...")
        data = self._load_historical_data()
        
        if not data or not all(tf in data for tf in self.timeframes):
            raise ValueError("Не удалось загрузить необходимые данные")
        
        # Основной цикл бэк-тестинга
        print("Запуск симуляции...")
        self._run_simulation(data)
        
        # Анализ результатов
        print("Анализ результатов...")
        self.results = PerformanceMetrics(self.portfolio)
        
        print(f"Бэк-тестинг завершен. Всего сделок: {len(self.portfolio.trades)}")
        
        return self.results
    
    def _load_historical_data(self) -> Dict[str, pd.DataFrame]:
        """Загрузка исторических данных"""
        data = {}
        
        for timeframe in self.timeframes:
            try:
                # Здесь используется синхронная загрузка для упрощения
                # В реальном применении можно добавить асинхронную загрузку
                df = self.data_provider.get_historical_data(
                    symbol=self.symbol,
                    timeframe=timeframe,
                    start_time=self.start_date,
                    end_time=self.end_date
                )
                
                if df is not None and not df.empty:
                    data[timeframe] = df
                    print(f"Загружено {len(df)} свечей для {timeframe}")
                else:
                    print(f"Предупреждение: нет данных для {timeframe}")
                    
            except Exception as e:
                print(f"Ошибка загрузки данных для {timeframe}: {e}")
        
        return data
    
    def _run_simulation(self, data: Dict[str, pd.DataFrame]):
        """Основной цикл симуляции"""
        
        # Определяем основной таймфрейм для итерации (обычно самый младший)
        main_timeframe = self.timeframes[-1]  # Последний в списке
        main_data = data[main_timeframe]
        
        print(f"Основной таймфрейм для симуляции: {main_timeframe}")
        print(f"Период симуляции: {len(main_data)} свечей")
        
        # Итерация по каждой свече
        for idx, (timestamp, row) in enumerate(main_data.iterrows()):
            
            # Прогресс
            if idx % 1000 == 0:
                progress = (idx / len(main_data)) * 100
                print(f"Прогресс: {progress:.1f}% ({idx}/{len(main_data)})")
            
            current_time = timestamp
            current_prices = {
                self.symbol: {
                    'open': row['open'],
                    'high': row['high'], 
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume']
                }
            }
            
            # Обновление текущих цен для открытых позиций
            current_close_prices = {self.symbol: row['close']}
            
            # Проверка стоп-лоссов и тейк-профитов
            closed_trades = self.portfolio.check_stop_losses_and_take_profits(
                current_close_prices, current_time
            )
            
            # Логирование закрытых сделок
            for trade in closed_trades:
                self._log_trade_event(trade, "closed_by_sl_tp", current_time)
            
            # Получение срезов данных для анализа
            historical_data = self._get_historical_slice(data, current_time, idx)
            
            # Анализ рыночной структуры
            try:
                market_analysis = self._analyze_market_structure(historical_data)
                
                # Генерация сигналов
                signals = self._generate_signals(historical_data, market_analysis, current_time)
                
                # Обработка сигналов
                for signal in signals:
                    self._process_signal(signal, current_prices, current_time)
                    
            except Exception as e:
                # В продакшене лучше использовать логирование
                if idx % 5000 == 0:  # Показываем ошибки не слишком часто
                    print(f"Ошибка анализа на {current_time}: {e}")
            
            # Обновление эквити портфеля
            self.portfolio.update_equity(current_time)
    
    def _get_historical_slice(self, 
                            data: Dict[str, pd.DataFrame], 
                            current_time: datetime, 
                            current_idx: int) -> Dict[str, pd.DataFrame]:
        """Получение исторического среза данных до текущего момента"""
        
        historical_slice = {}
        
        for timeframe, df in data.items():
            # Получаем только данные до текущего времени (no look-ahead bias)
            mask = df.index <= current_time
            historical_df = df[mask].copy()
            
            # Ограничиваем количество свечей для анализа (для производительности)
            max_candles = 500  # Достаточно для большинства анализов
            if len(historical_df) > max_candles:
                historical_df = historical_df.tail(max_candles)
            
            historical_slice[timeframe] = historical_df
        
        return historical_slice
    
    def _analyze_market_structure(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """Анализ рыночной структуры"""
        
        analysis_results = {}
        
        for timeframe, df in data.items():
            if len(df) < 20:  # Минимум данных для анализа
                continue
            
            try:
                # Анализ свинг-точек
                swing_points = self.market_structure.find_swing_points(df)
                
                # Определение структуры рынка
                market_structure = self.market_structure.analyze_structure(df, swing_points)
                
                # Поиск ликвидности
                liquidity_zones = self.liquidity_detector.detect_liquidity_zones(df, swing_points)
                
                # Поиск зон интереса
                order_blocks = self.poi_identifier.find_order_blocks(df)
                imbalances = self.poi_identifier.find_imbalances(df)
                
                analysis_results[timeframe] = {
                    'swing_points': swing_points,
                    'market_structure': market_structure,
                    'liquidity_zones': liquidity_zones,
                    'order_blocks': order_blocks,
                    'imbalances': imbalances,
                    'latest_price': df['close'].iloc[-1] if not df.empty else None
                }
                
            except Exception as e:
                print(f"Ошибка анализа {timeframe}: {e}")
                analysis_results[timeframe] = {}
        
        return analysis_results
    
    def _generate_signals(self, 
                         data: Dict[str, pd.DataFrame], 
                         market_analysis: Dict,
                         current_time: datetime) -> List[Dict]:
        """Генерация торговых сигналов"""
        
        try:
            # Получение сигналов от генератора
            signals = self.signal_generator.generate_signals(
                symbol=self.symbol,
                timeframe_data=data,
                analysis_results=market_analysis,
                current_time=current_time
            )
            
            return signals if signals else []
            
        except Exception as e:
            print(f"Ошибка генерации сигналов: {e}")
            return []
    
    def _process_signal(self, 
                       signal: Dict, 
                       current_prices: Dict,
                       current_time: datetime):
        """Обработка торгового сигнала"""
        
        try:
            signal_type = signal.get('action')
            symbol = signal.get('symbol', self.symbol)
            
            if signal_type == 'BUY':
                self._process_buy_signal(signal, current_prices, current_time)
            elif signal_type == 'SELL': 
                self._process_sell_signal(signal, current_prices, current_time)
            elif signal_type == 'CLOSE':
                self._process_close_signal(signal, current_prices, current_time)
                
        except Exception as e:
            print(f"Ошибка обработки сигнала: {e}")
    
    def _process_buy_signal(self, signal: Dict, current_prices: Dict, current_time: datetime):
        """Обработка сигнала на покупку"""
        
        symbol = signal.get('symbol', self.symbol)
        price = current_prices[symbol]['close']
        
        # Расчет размера позиции с помощью риск-менеджера
        position_size = self.risk_manager.calculate_position_size(
            balance=self.portfolio.available_balance,
            entry_price=price,
            stop_loss=signal.get('stop_loss'),
            risk_percent=signal.get('risk_percent', 1.0)
        )
        
        if position_size <= 0:
            return
        
        # Создание сделки
        trade_id = str(uuid.uuid4())
        
        trade = self.portfolio.open_trade(
            trade_id=trade_id,
            symbol=symbol,
            direction=TradeDirection.LONG,
            quantity=position_size,
            price=price,
            timestamp=current_time,
            stop_loss=signal.get('stop_loss'),
            take_profit=signal.get('take_profit'),
            strategy_context={
                'poi_type': signal.get('poi_type'),
                'confidence': signal.get('confidence'),
                'timeframe': signal.get('timeframe'),
                'signal_reason': signal.get('reason')
            }
        )
        
        if trade:
            self._log_trade_event(trade, "opened", current_time)
    
    def _process_sell_signal(self, signal: Dict, current_prices: Dict, current_time: datetime):
        """Обработка сигнала на продажу"""
        
        symbol = signal.get('symbol', self.symbol)
        price = current_prices[symbol]['close']
        
        # Расчет размера позиции
        position_size = self.risk_manager.calculate_position_size(
            balance=self.portfolio.available_balance,
            entry_price=price,
            stop_loss=signal.get('stop_loss'),
            risk_percent=signal.get('risk_percent', 1.0)
        )
        
        if position_size <= 0:
            return
        
        # Создание сделки
        trade_id = str(uuid.uuid4())
        
        trade = self.portfolio.open_trade(
            trade_id=trade_id,
            symbol=symbol,
            direction=TradeDirection.SHORT,
            quantity=position_size,
            price=price,
            timestamp=current_time,
            stop_loss=signal.get('stop_loss'),
            take_profit=signal.get('take_profit'),
            strategy_context={
                'poi_type': signal.get('poi_type'),
                'confidence': signal.get('confidence'),
                'timeframe': signal.get('timeframe'),
                'signal_reason': signal.get('reason')
            }
        )
        
        if trade:
            self._log_trade_event(trade, "opened", current_time)
    
    def _process_close_signal(self, signal: Dict, current_prices: Dict, current_time: datetime):
        """Обработка сигнала на закрытие позиции"""
        
        symbol = signal.get('symbol', self.symbol)
        price = current_prices[symbol]['close']
        
        # Закрытие всех открытых позиций для символа
        trades_to_close = []
        for trade_id, trade in self.portfolio.open_trades.items():
            if trade.symbol == symbol:
                trades_to_close.append(trade_id)
        
        for trade_id in trades_to_close:
            closed_trade = self.portfolio.close_trade(
                trade_id=trade_id,
                price=price,
                timestamp=current_time,
                exit_reason="signal_close"
            )
            
            if closed_trade:
                self._log_trade_event(closed_trade, "closed_by_signal", current_time)
    
    def _log_trade_event(self, trade: Trade, event_type: str, timestamp: datetime):
        """Логирование торговых событий"""
        
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'event_type': event_type,
            'trade_id': trade.id,
            'symbol': trade.symbol,
            'direction': trade.direction.value,
            'entry_price': trade.entry_price,
            'exit_price': trade.exit_price,
            'quantity': trade.quantity,
            'pnl': trade.pnl,
            'pnl_percent': trade.pnl_percent,
            'poi_type': trade.poi_type,
            'confidence': trade.confidence,
            'duration_hours': trade.duration
        }
        
        self.trades_log.append(log_entry)
    
    def save_results(self, filename: str = None):
        """Сохранение результатов бэк-тестинга"""
        
        if not self.results:
            print("Нет результатов для сохранения")
            return
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_results_{self.symbol}_{timestamp}"
        
        # Создание папки результатов
        results_dir = Path("backtest_results")
        results_dir.mkdir(exist_ok=True)
        
        # Сохранение метрик
        metrics = self.results.get_comprehensive_metrics()
        with open(results_dir / f"{filename}_metrics.json", 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        
        # Сохранение отчета
        report = self.results.generate_report()
        with open(results_dir / f"{filename}_report.txt", 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Сохранение логов сделок
        with open(results_dir / f"{filename}_trades.json", 'w', encoding='utf-8') as f:
            json.dump(self.trades_log, f, ensure_ascii=False, indent=2)
        
        # Сохранение эквити кривой
        equity_df = self.portfolio.to_dataframe()
        if not equity_df.empty:
            equity_df.to_csv(results_dir / f"{filename}_equity.csv", index=False)
        
        print(f"Результаты сохранены в папку {results_dir}")
        print(f"Файлы: {filename}_metrics.json, {filename}_report.txt, {filename}_trades.json, {filename}_equity.csv")
    
    def get_summary(self) -> Dict:
        """Получение краткой сводки результатов"""
        
        if not self.results:
            return {"error": "Бэк-тестинг не запущен"}
        
        summary = self.portfolio.get_performance_summary()
        summary.update({
            'symbol': self.symbol,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'timeframes_used': self.timeframes
        })
        
        return summary