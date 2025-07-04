"""
Главный класс торгового бота "Охота за ликвидностью"
"""

import asyncio
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger

from config import get_config
from core.data_types import (
    TimeFrame, MarketState, Signal, Trade, ContextState, BacktestResult
)
from core.exceptions import TradingBotError

# Импорты компонентов
from data.data_provider import ExchangeDataProvider
from analysis.market_structure import MarketStructureAnalyzer
from analysis.liquidity_detector import LiquidityDetector
from analysis.poi_identifier import POIIdentifier
from analysis.timeframe_synchronizer import TimeframeSynchronizer
from trading.signal_generator import LiquidityHuntSignalGenerator
from trading.risk_manager import LiquidityHuntRiskManager


class LiquidityHuntBot:
    """Торговый бот стратегии "Охота за ликвидностью" """
    
    def __init__(self, symbol: str = "BTC/USDT"):
        """Инициализация бота"""
        self.config = get_config()
        self.symbol = symbol
        self.is_running = False
        
        # Компоненты системы
        self.data_provider = ExchangeDataProvider()
        self.market_analyzer = MarketStructureAnalyzer()
        self.liquidity_detector = LiquidityDetector()
        self.poi_identifier = POIIdentifier()
        self.timeframe_sync = TimeframeSynchronizer()
        self.signal_generator = LiquidityHuntSignalGenerator()
        self.risk_manager = LiquidityHuntRiskManager()
        
        # Состояние бота
        self.current_context = ContextState()
        self.active_trades: List[Trade] = []
        self.signal_history: List[Signal] = []
        self.performance_metrics: Dict[str, float] = {}
        
        # Данные по таймфреймам
        self.timeframes = [
            TimeFrame.D1, TimeFrame.H4, TimeFrame.H1,
            TimeFrame.M30, TimeFrame.M15, TimeFrame.M5, TimeFrame.M1
        ]
        self.market_data: Dict[TimeFrame, pd.DataFrame] = {}
        self.market_states: Dict[TimeFrame, MarketState] = {}
        
        logger.info(f"Инициализирован бот для {symbol}")
    
    async def start(self) -> None:
        """Запуск торгового бота"""
        try:
            logger.info("Запуск торгового бота...")
            self.is_running = True
            
            # Инициализация компонентов
            await self._initialize_components()
            
            # Загрузка исторических данных
            await self._load_historical_data()
            
            # Главный цикл
            await self._main_loop()
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise TradingBotError(f"Не удалось запустить бота: {e}")
    
    async def stop(self) -> None:
        """Остановка торгового бота"""
        try:
            logger.info("Остановка торгового бота...")
            self.is_running = False
            
            # Закрытие открытых позиций (опционально)
            if self.config.trading.close_on_shutdown:
                await self._close_all_positions()
            
            # Сохранение состояния
            await self._save_state()
            
            logger.info("Бот остановлен")
            
        except Exception as e:
            logger.error(f"Ошибка остановки бота: {e}")
    
    async def analyze_market(self, current_time: datetime) -> Dict[TimeFrame, MarketState]:
        """Комплексный анализ рынка по всем таймфреймам"""
        try:
            # Синхронизируем данные по таймфреймам
            synchronized_data = self.timeframe_sync.synchronize_timeframes(
                self.market_data, current_time
            )
            
            market_states = {}
            
            # Анализируем каждый таймфрейм
            for timeframe in self.timeframes:
                if timeframe not in synchronized_data:
                    continue
                
                data = synchronized_data[timeframe]
                if len(data) < 20:  # Минимум данных для анализа
                    continue
                
                try:
                    # Анализ структуры рынка
                    market_structure = self.market_analyzer.analyze_structure(data)
                    swing_highs, swing_lows = self.market_analyzer.detect_swings(data)
                    trend_strength = self.market_analyzer.calculate_trend_strength(data)
                    
                    # Детекция ликвидности
                    all_swings = swing_highs + swing_lows
                    liquidity_pools = self.liquidity_detector.detect_liquidity_pools(data, all_swings)
                    
                    # Идентификация зон интереса
                    active_pois = self.poi_identifier.get_all_active_pois(data, current_time)
                    all_pois = []
                    for poi_type, pois in active_pois.items():
                        all_pois.extend(pois)
                    
                    # Создаем состояние рынка
                    market_state = MarketState(
                        timestamp=current_time,
                        symbol=self.symbol,
                        timeframe=timeframe,
                        structure=market_structure,
                        trend_strength=trend_strength,
                        swing_highs=swing_highs,
                        swing_lows=swing_lows,
                        liquidity_pools=liquidity_pools,
                        active_pois=all_pois,
                        volatility=self._calculate_volatility(data)
                    )
                    
                    market_states[timeframe] = market_state
                    
                except Exception as e:
                    logger.error(f"Ошибка анализа {timeframe}: {e}")
                    continue
            
            self.market_states = market_states
            logger.debug(f"Проанализированы {len(market_states)} таймфреймов")
            
            return market_states
            
        except Exception as e:
            logger.error(f"Ошибка анализа рынка: {e}")
            return {}
    
    async def generate_signals(self, market_states: Dict[TimeFrame, MarketState]) -> List[Signal]:
        """Генерация торговых сигналов"""
        try:
            all_signals = []
            
            # Генерируем сигналы для каждого таймфрейма
            for timeframe in [TimeFrame.M15, TimeFrame.M5, TimeFrame.M1]:  # Исполнительные таймфреймы
                if timeframe not in market_states:
                    continue
                
                market_state = market_states[timeframe]
                
                # Получаем контекст от высших таймфреймов
                htf_analysis = {tf: {'market_state': ms} for tf, ms in market_states.items()}
                context_data = self.timeframe_sync.propagate_context(htf_analysis, timeframe)
                
                # Обновляем контекст
                self.current_context.market_regime = self._determine_market_regime(market_states)
                self.current_context.confidence_level = self._calculate_confidence_level(market_state)
                
                # Генерируем сигналы
                timeframe_signals = self.signal_generator.generate_signals(
                    market_state, self.current_context
                )
                
                all_signals.extend(timeframe_signals)
            
            # Валидируем временную согласованность
            if all_signals:
                signals_by_tf = {}
                for signal in all_signals:
                    tf = signal.timeframe
                    if tf not in signals_by_tf:
                        signals_by_tf[tf] = []
                    signals_by_tf[tf].append(signal)
                
                validated_signals = self.timeframe_sync.validate_temporal_consistency(
                    signals_by_tf, datetime.now()
                )
                
                final_signals = []
                for tf_signals in validated_signals.values():
                    final_signals.extend(tf_signals)
                
                logger.info(f"Сгенерировано {len(final_signals)} валидных сигналов")
                return final_signals
            
            return []
            
        except Exception as e:
            logger.error(f"Ошибка генерации сигналов: {e}")
            return []
    
    async def execute_signals(self, signals: List[Signal]) -> List[Trade]:
        """Исполнение торговых сигналов"""
        try:
            executed_trades = []
            current_balance = 100000.0  # Базовый баланс для демо
            
            for signal in signals:
                try:
                    # Валидация риск-параметров
                    if not self.risk_manager.validate_risk_parameters(signal):
                        logger.debug(f"Сигнал не прошел валидацию рисков: {signal.signal_type}")
                        continue
                    
                    # Проверка корреляционных рисков
                    if not self.risk_manager.check_correlation_risk(signal, self.active_trades):
                        logger.debug(f"Сигнал отклонен из-за корреляции: {signal.signal_type}")
                        continue
                    
                    # Расчет размера позиции
                    position_size = self.risk_manager.calculate_position_size(signal, current_balance)
                    
                    if position_size <= 0:
                        logger.debug(f"Нулевой размер позиции для сигнала: {signal.signal_type}")
                        continue
                    
                    # Создание сделки (симуляция)
                    trade = Trade(
                        trade_id=f"trade_{len(self.active_trades) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        signal=signal,
                        entry_time=signal.timestamp,
                        entry_price=signal.entry_price,
                        quantity=position_size
                    )
                    
                    # В реальной торговле здесь был бы API-вызов к бирже
                    logger.info(f"Исполнена сделка {trade.trade_id}: {signal.signal_type} "
                              f"по цене {signal.entry_price:.2f}, размер {position_size:.6f}")
                    
                    self.active_trades.append(trade)
                    executed_trades.append(trade)
                    
                except Exception as e:
                    logger.error(f"Ошибка исполнения сигнала: {e}")
                    continue
            
            return executed_trades
            
        except Exception as e:
            logger.error(f"Ошибка исполнения сигналов: {e}")
            return []
    
    async def manage_positions(self, current_price: float) -> None:
        """Управление открытыми позициями"""
        try:
            for trade in self.active_trades.copy():
                if trade.status.value != "open":
                    continue
                
                # Проверяем стоп-лосс и тейк-профит
                signal = trade.signal
                
                if signal.is_long:
                    # Проверка стоп-лосса
                    if current_price <= signal.stop_loss:
                        await self._close_position(trade, current_price, "stop_loss")
                        continue
                    
                    # Проверка тейк-профита
                    if current_price >= signal.take_profit:
                        await self._close_position(trade, current_price, "take_profit")
                        continue
                        
                else:  # Шорт
                    # Проверка стоп-лосса
                    if current_price >= signal.stop_loss:
                        await self._close_position(trade, current_price, "stop_loss")
                        continue
                    
                    # Проверка тейк-профита
                    if current_price <= signal.take_profit:
                        await self._close_position(trade, current_price, "take_profit")
                        continue
                
                # Обновление трейлинг стопа
                if signal.timeframe in self.market_states:
                    market_state = self.market_states[signal.timeframe]
                    new_stop = self.risk_manager.update_stop_loss(trade, current_price, market_state)
                    
                    if new_stop:
                        logger.info(f"Обновлен стоп для сделки {trade.trade_id}: {new_stop:.2f}")
                        # В реальной торговле здесь был бы обновление ордера
                        
        except Exception as e:
            logger.error(f"Ошибка управления позициями: {e}")
    
    async def _main_loop(self) -> None:
        """Главный цикл бота"""
        try:
            while self.is_running:
                start_time = datetime.now()
                
                try:
                    # Обновление данных
                    await self._update_market_data()
                    
                    # Анализ рынка
                    market_states = await self.analyze_market(start_time)
                    
                    if market_states:
                        # Генерация сигналов
                        signals = await self.generate_signals(market_states)
                        
                        # Исполнение сигналов
                        if signals:
                            executed_trades = await self.execute_signals(signals)
                            self.signal_history.extend(signals)
                        
                        # Управление позициями
                        current_price = self._get_current_price()
                        await self.manage_positions(current_price)
                    
                    # Обновление метрик
                    self._update_performance_metrics()
                    
                    # Логирование состояния
                    self._log_status()
                    
                except Exception as e:
                    logger.error(f"Ошибка в главном цикле: {e}")
                
                # Пауза до следующей итерации
                await asyncio.sleep(self.config.trading.update_interval)
                
        except Exception as e:
            logger.error(f"Критическая ошибка в главном цикле: {e}")
            self.is_running = False
    
    # Приватные методы
    async def _initialize_components(self) -> None:
        """Инициализация компонентов"""
        try:
            logger.info("Инициализация компонентов...")
            # Здесь можно добавить дополнительную инициализацию
            
        except Exception as e:
            logger.error(f"Ошибка инициализации компонентов: {e}")
            raise
    
    async def _load_historical_data(self) -> None:
        """Загрузка исторических данных"""
        try:
            logger.info("Загрузка исторических данных...")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)  # 30 дней истории
            
            for timeframe in self.timeframes:
                try:
                    data = await self.data_provider.get_historical_data(
                        self.symbol, timeframe, start_date, end_date
                    )
                    
                    if not data.empty:
                        self.market_data[timeframe] = data
                        logger.debug(f"Загружено {len(data)} свечей для {timeframe}")
                    
                except Exception as e:
                    logger.error(f"Ошибка загрузки данных {timeframe}: {e}")
                    continue
            
            logger.info(f"Загружены данные для {len(self.market_data)} таймфреймов")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки исторических данных: {e}")
            raise
    
    async def _update_market_data(self) -> None:
        """Обновление рыночных данных"""
        try:
            for timeframe in self.timeframes:
                try:
                    # Получаем последние свечи
                    latest_data = await self.data_provider.get_latest_candles(
                        self.symbol, timeframe, limit=100
                    )
                    
                    if not latest_data.empty:
                        # Обновляем данные
                        if timeframe in self.market_data:
                            # Объединяем с существующими данными
                            combined_data = pd.concat([self.market_data[timeframe], latest_data])
                            combined_data = combined_data[~combined_data.index.duplicated(keep='last')]
                            self.market_data[timeframe] = combined_data.tail(1000)  # Ограничиваем размер
                        else:
                            self.market_data[timeframe] = latest_data
                            
                except Exception as e:
                    logger.error(f"Ошибка обновления данных {timeframe}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Ошибка обновления рыночных данных: {e}")
    
    async def _close_position(self, trade: Trade, exit_price: float, reason: str) -> None:
        """Закрытие позиции"""
        try:
            trade.exit_time = datetime.now()
            trade.exit_price = exit_price
            trade.status = trade.status.CLOSED
            
            # Расчет P&L
            if trade.signal.is_long:
                trade.pnl = (exit_price - trade.entry_price) * trade.quantity
            else:
                trade.pnl = (trade.entry_price - exit_price) * trade.quantity
            
            trade.pnl_percentage = trade.pnl / (trade.entry_price * trade.quantity)
            
            logger.info(f"Закрыта позиция {trade.trade_id}: {reason}, "
                       f"P&L: {trade.pnl:.2f} ({trade.pnl_percentage:.2%})")
            
            # Удаляем из активных сделок
            if trade in self.active_trades:
                self.active_trades.remove(trade)
                
        except Exception as e:
            logger.error(f"Ошибка закрытия позиции: {e}")
    
    async def _close_all_positions(self) -> None:
        """Закрытие всех позиций"""
        try:
            current_price = self._get_current_price()
            
            for trade in self.active_trades.copy():
                await self._close_position(trade, current_price, "shutdown")
                
        except Exception as e:
            logger.error(f"Ошибка закрытия всех позиций: {e}")
    
    async def _save_state(self) -> None:
        """Сохранение состояния бота"""
        try:
            # Здесь можно сохранить состояние в файл или базу данных
            logger.info("Состояние бота сохранено")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния: {e}")
    
    def _get_current_price(self) -> float:
        """Получение текущей цены"""
        try:
            if TimeFrame.M1 in self.market_data and not self.market_data[TimeFrame.M1].empty:
                return float(self.market_data[TimeFrame.M1]['close'].iloc[-1])
            elif TimeFrame.M5 in self.market_data and not self.market_data[TimeFrame.M5].empty:
                return float(self.market_data[TimeFrame.M5]['close'].iloc[-1])
            else:
                return 50000.0  # Базовая цена для демо
                
        except Exception as e:
            logger.error(f"Ошибка получения текущей цены: {e}")
            return 50000.0
    
    def _calculate_volatility(self, data: pd.DataFrame) -> float:
        """Расчет волатильности"""
        try:
            if len(data) < 20:
                return 0.0
            
            returns = data['close'].pct_change().dropna()
            volatility = returns.std() * (252 ** 0.5)  # Аннуализированная волатильность
            
            return float(volatility)
            
        except Exception as e:
            logger.error(f"Ошибка расчета волатильности: {e}")
            return 0.0
    
    def _determine_market_regime(self, market_states: Dict[TimeFrame, MarketState]) -> str:
        """Определение рыночного режима"""
        try:
            if not market_states:
                return "normal"
            
            # Анализируем волатильность на разных таймфреймах
            avg_volatility = sum(ms.volatility for ms in market_states.values()) / len(market_states)
            
            if avg_volatility > 0.5:
                return "high_volatility"
            elif avg_volatility < 0.1:
                return "low_volatility"
            else:
                return "normal"
                
        except Exception as e:
            logger.error(f"Ошибка определения рыночного режима: {e}")
            return "normal"
    
    def _calculate_confidence_level(self, market_state: MarketState) -> float:
        """Расчет уровня уверенности"""
        try:
            confidence = 0.5  # Базовый уровень
            
            # Увеличиваем уверенность при сильном тренде
            if market_state.trend_strength > 0.7:
                confidence += 0.2
            
            # Увеличиваем при наличии качественных зон интереса
            strong_pois = [poi for poi in market_state.active_pois if poi.strength > 0.7]
            if len(strong_pois) > 2:
                confidence += 0.1
            
            # Увеличиваем при наличии непробитой ликвидности
            unswept_pools = [pool for pool in market_state.liquidity_pools if not pool.swept]
            if len(unswept_pools) > 1:
                confidence += 0.1
            
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Ошибка расчета уверенности: {e}")
            return 0.5
    
                def _update_performance_metrics(self) -> None:
        """Обновление метрик производительности"""
        try:
            # Базовые метрики
            self.performance_metrics['active_positions'] = len(self.active_trades)
            self.performance_metrics['total_signals'] = len(self.signal_history)
            risk_metrics = self.risk_manager.get_risk_metrics()
            for key, value in risk_metrics.items():
                self.performance_metrics[f'risk_{key}'] = value
            
        except Exception as e:
            logger.error(f"Ошибка обновления метрик: {e}")
    
    def _log_status(self) -> None:
        """Логирование текущего состояния"""
        try:
            status = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'active_trades': len(self.active_trades),
                'market_states': len(self.market_states),
                'current_price': self._get_current_price()
            }
            
            logger.info(f"Состояние бота: {status}")
            
        except Exception as e:
            logger.error(f"Ошибка логирования состояния: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получение текущего статуса бота"""
        return {
            'is_running': self.is_running,
            'symbol': self.symbol,
            'active_trades': len(self.active_trades),
            'total_signals': len(self.signal_history),
            'market_states': len(self.market_states),
            'performance_metrics': self.performance_metrics,
            'current_price': self._get_current_price()
        }