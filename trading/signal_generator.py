"""
Генератор торговых сигналов для стратегии "Охота за ликвидностью"
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from loguru import logger

from core.interfaces import ISignalGenerator
from core.data_types import (
    Signal, SignalType, MarketState, MarketStructure, ContextState,
    TimeFrame, LiquidityPool, LiquidityType, POI, POIType, SwingPoint, OHLCV
)
from core.exceptions import SignalGenerationError
from config import get_config


class LiquidityHuntSignalGenerator(ISignalGenerator):
    """Генератор сигналов по стратегии "Охота за ликвидностью" """
    
    def __init__(self):
        self.config = get_config()
        self._signal_history: List[Signal] = []
        self._last_analysis_time: Optional[datetime] = None
        
    def generate_signals(
        self, 
        market_state: MarketState, 
        context: ContextState
    ) -> List[Signal]:
        """Генерация торговых сигналов на основе анализа рынка"""
        try:
            signals = []
            
            # Проверяем базовые условия для генерации сигналов
            if not self._validate_market_conditions(market_state, context):
                return signals
            
            # Ищем установки (setups) для входа
            bullish_setups = self._find_bullish_setups(market_state, context)
            bearish_setups = self._find_bearish_setups(market_state, context)
            
            # Генерируем сигналы для найденных установок
            for setup in bullish_setups:
                signal = self._create_bullish_signal(setup, market_state, context)
                if signal and self._validate_signal(signal, context):
                    signals.append(signal)
            
            for setup in bearish_setups:
                signal = self._create_bearish_signal(setup, market_state, context)
                if signal and self._validate_signal(signal, context):
                    signals.append(signal)
            
            # Фильтруем сигналы по качеству
            filtered_signals = self.filter_signals(signals, context)
            
            # Обновляем историю
            self._signal_history.extend(filtered_signals)
            self._last_analysis_time = market_state.timestamp
            
            if filtered_signals:
                logger.info(f"Сгенерировано {len(filtered_signals)} сигналов на {market_state.timeframe}")
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Ошибка генерации сигналов: {e}")
            raise SignalGenerationError(f"Не удалось сгенерировать сигналы: {e}")
    
    def calculate_confluence_score(
        self, 
        market_state: MarketState, 
        entry_price: float
    ) -> float:
        """Расчет скора конфлюенции (совпадения факторов)"""
        try:
            score = 0.0
            max_score = 0.0
            
            # 1. Структура рынка (20%)
            max_score += 0.20
            if market_state.structure in [MarketStructure.BULLISH, MarketStructure.BEARISH]:
                if market_state.trend_strength > 0.6:
                    score += 0.20
                elif market_state.trend_strength > 0.3:
                    score += 0.10
            
            # 2. Ликвидность (25%)
            max_score += 0.25
            liquidity_score = self._calculate_liquidity_confluence(
                market_state.liquidity_pools, entry_price
            )
            score += liquidity_score * 0.25
            
            # 3. Зоны интереса (25%)
            max_score += 0.25
            poi_score = self._calculate_poi_confluence(
                market_state.active_pois, entry_price
            )
            score += poi_score * 0.25
            
            # 4. Свинг-структура (15%)
            max_score += 0.15
            swing_score = self._calculate_swing_confluence(
                market_state.swing_highs, market_state.swing_lows, entry_price
            )
            score += swing_score * 0.15
            
            # 5. Фибоначчи уровни (10%)
            max_score += 0.10
            fib_score = self._calculate_fibonacci_confluence(
                market_state.fibonacci_levels, entry_price
            )
            score += fib_score * 0.10
            
            # 6. Время (5%) - лондонская/нью-йоркская сессии
            max_score += 0.05
            time_score = self._calculate_time_confluence(market_state.timestamp)
            score += time_score * 0.05
            
            # Нормализуем к диапазону 0-1
            confluence_score = score / max_score if max_score > 0 else 0
            
            return min(confluence_score, 1.0)
            
        except Exception as e:
            logger.error(f"Ошибка расчета конфлюенции: {e}")
            return 0.5
    
    def determine_entry_levels(
        self, 
        market_state: MarketState, 
        signal_direction: str
    ) -> Tuple[float, float, float]:
        """Определение уровней входа, стопа и тейка"""
        try:
            # Текущая цена (симуляция)
            current_price = self._get_current_price(market_state)
            
            if signal_direction == "bullish":
                return self._calculate_bullish_levels(market_state, current_price)
            else:
                return self._calculate_bearish_levels(market_state, current_price)
                
        except Exception as e:
            logger.error(f"Ошибка определения уровней: {e}")
            # Возвращаем базовые уровни
            current_price = self._get_current_price(market_state)
            if signal_direction == "bullish":
                return (
                    current_price, 
                    current_price * 0.98,  # 2% стоп
                    current_price * 1.04   # 4% тейк
                )
            else:
                return (
                    current_price,
                    current_price * 1.02,  # 2% стоп
                    current_price * 0.96   # 4% тейк
                )
    
    def filter_signals(
        self, 
        signals: List[Signal], 
        context: ContextState
    ) -> List[Signal]:
        """Фильтрация сигналов по качеству"""
        try:
            if not signals:
                return []
            
            filtered = []
            
            for signal in signals:
                # Проверяем минимальный скор конфлюенции
                if signal.confluence_score < self.config.strategy.min_confluence_score:
                    logger.debug(f"Сигнал отфильтрован: низкий скор конфлюенции ({signal.confluence_score:.2f})")
                    continue
                
                # Проверяем R:R соотношение
                if signal.risk_reward_ratio < self.config.strategy.min_risk_reward:
                    logger.debug(f"Сигнал отфильтрован: плохое R:R ({signal.risk_reward_ratio:.2f})")
                    continue
                
                # Проверяем соответствие глобальному bias
                if not self._check_bias_alignment(signal, context):
                    logger.debug(f"Сигнал отфильтрован: не соответствует bias")
                    continue
                
                # Проверяем отсутствие недавних сигналов в той же зоне
                if self._has_recent_signal_nearby(signal):
                    logger.debug(f"Сигнал отфильтрован: недавний сигнал поблизости")
                    continue
                
                # Проверяем эмоциональные факторы
                if not self._check_emotional_filters(signal, context):
                    logger.debug(f"Сигнал отфильтрован: эмоциональные факторы")
                    continue
                
                filtered.append(signal)
            
            # Ранжируем по качеству и берем лучшие
            filtered.sort(key=lambda s: s.confluence_score, reverse=True)
            max_signals = self.config.strategy.max_signals_per_timeframe
            
            return filtered[:max_signals]
            
        except Exception as e:
            logger.error(f"Ошибка фильтрации сигналов: {e}")
            return signals
    
    def _validate_market_conditions(
        self, 
        market_state: MarketState, 
        context: ContextState
    ) -> bool:
        """Валидация условий рынка для генерации сигналов"""
        try:
            # Проверяем наличие данных
            if not market_state.liquidity_pools and not market_state.active_pois:
                return False
            
            # Проверяем волатильность
            if market_state.volatility < self.config.strategy.min_volatility:
                return False
            
            if market_state.volatility > self.config.strategy.max_volatility:
                return False
            
            # Проверяем рыночный режим
            if context.market_regime == "high_volatility" and context.confidence_level < 0.7:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка валидации рыночных условий: {e}")
            return False
    
    def _find_bullish_setups(
        self, 
        market_state: MarketState, 
        context: ContextState
    ) -> List[Dict[str, Any]]:
        """Поиск бычьих установок (Liquidity Hunt)"""
        setups = []
        
        try:
            # Ищем снятие SSL (Sell Side Liquidity) + структурный break
            for pool in market_state.liquidity_pools:
                if (pool.liquidity_type == LiquidityType.SSL and 
                    pool.swept and 
                    pool.swept_at and 
                    self._is_recent_sweep(pool.swept_at)):
                    
                    # Проверяем структурный break
                    if self._has_bullish_structure_break(market_state):
                        
                        # Ищем подходящие POI для входа
                        entry_pois = self._find_bullish_entry_pois(market_state, pool.price)
                        
                        for poi in entry_pois:
                            setup = {
                                'type': 'liquidity_hunt_bullish',
                                'swept_liquidity': pool,
                                'entry_poi': poi,
                                'direction': 'bullish',
                                'confluence_factors': self._analyze_bullish_confluence(
                                    market_state, pool, poi
                                )
                            }
                            setups.append(setup)
            
            return setups
            
        except Exception as e:
            logger.error(f"Ошибка поиска бычьих установок: {e}")
            return []
    
    def _find_bearish_setups(
        self, 
        market_state: MarketState, 
        context: ContextState
    ) -> List[Dict[str, Any]]:
        """Поиск медвежьих установок (Liquidity Hunt)"""
        setups = []
        
        try:
            # Ищем снятие BSL (Buy Side Liquidity) + структурный break
            for pool in market_state.liquidity_pools:
                if (pool.liquidity_type == LiquidityType.BSL and 
                    pool.swept and 
                    pool.swept_at and 
                    self._is_recent_sweep(pool.swept_at)):
                    
                    # Проверяем структурный break
                    if self._has_bearish_structure_break(market_state):
                        
                        # Ищем подходящие POI для входа
                        entry_pois = self._find_bearish_entry_pois(market_state, pool.price)
                        
                        for poi in entry_pois:
                            setup = {
                                'type': 'liquidity_hunt_bearish',
                                'swept_liquidity': pool,
                                'entry_poi': poi,
                                'direction': 'bearish',
                                'confluence_factors': self._analyze_bearish_confluence(
                                    market_state, pool, poi
                                )
                            }
                            setups.append(setup)
            
            return setups
            
        except Exception as e:
            logger.error(f"Ошибка поиска медвежьих установок: {e}")
            return []
    
    def _create_bullish_signal(
        self, 
        setup: Dict[str, Any], 
        market_state: MarketState, 
        context: ContextState
    ) -> Optional[Signal]:
        """Создание бычьего сигнала"""
        try:
            poi: POI = setup['entry_poi']
            
            # Определяем уровни
            entry_price = poi.low_price + (poi.price_range * 0.2)  # Вход в нижней части POI
            stop_loss = poi.low_price - (poi.price_range * 0.5)    # Стоп ниже POI
            
            # Рассчитываем тейк-профит на основе структуры
            take_profit = self._calculate_bullish_target(market_state, entry_price)
            
            # Рассчитываем конфлюенцию
            confluence_score = self.calculate_confluence_score(market_state, entry_price)
            
            # Создаем сигнал
            signal = Signal(
                timestamp=market_state.timestamp,
                signal_type=SignalType.BUY,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confluence_score=confluence_score,
                timeframe=market_state.timeframe,
                market_structure=market_state.structure,
                liquidity_context=[setup['swept_liquidity']],
                poi_context=[poi],
                strategy_version=self.config.strategy.version,
                notes=f"Liquidity Hunt: SSL swept at {setup['swept_liquidity'].price:.2f}, entry at {poi.poi_type.value}"
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Ошибка создания бычьего сигнала: {e}")
            return None
    
    def _create_bearish_signal(
        self, 
        setup: Dict[str, Any], 
        market_state: MarketState, 
        context: ContextState
    ) -> Optional[Signal]:
        """Создание медвежьего сигнала"""
        try:
            poi: POI = setup['entry_poi']
            
            # Определяем уровни
            entry_price = poi.high_price - (poi.price_range * 0.2)  # Вход в верхней части POI
            stop_loss = poi.high_price + (poi.price_range * 0.5)    # Стоп выше POI
            
            # Рассчитываем тейк-профит
            take_profit = self._calculate_bearish_target(market_state, entry_price)
            
            # Рассчитываем конфлюенцию
            confluence_score = self.calculate_confluence_score(market_state, entry_price)
            
            # Создаем сигнал
            signal = Signal(
                timestamp=market_state.timestamp,
                signal_type=SignalType.SELL,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confluence_score=confluence_score,
                timeframe=market_state.timeframe,
                market_structure=market_state.structure,
                liquidity_context=[setup['swept_liquidity']],
                poi_context=[poi],
                strategy_version=self.config.strategy.version,
                notes=f"Liquidity Hunt: BSL swept at {setup['swept_liquidity'].price:.2f}, entry at {poi.poi_type.value}"
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Ошибка создания медвежьего сигнала: {e}")
            return None
    
    def _validate_signal(self, signal: Signal, context: ContextState) -> bool:
        """Валидация сигнала"""
        try:
            # Проверяем базовые требования
            if signal.risk_reward_ratio < 1.0:
                return False
            
            if signal.confluence_score < 0.3:
                return False
            
            # Проверяем разумность цен
            price_diff = abs(signal.entry_price - signal.stop_loss) / signal.entry_price
            if price_diff > 0.05:  # Максимум 5% риск
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка валидации сигнала: {e}")
            return False
    
    # Вспомогательные методы
    def _get_current_price(self, market_state: MarketState) -> float:
        """Получение текущей цены (симуляция последней свечи)"""
        # В реальной системе это будет последняя цена из данных
        if market_state.swing_highs and market_state.swing_lows:
            recent_high = max(market_state.swing_highs, key=lambda x: x.timestamp).price
            recent_low = max(market_state.swing_lows, key=lambda x: x.timestamp).price
            return (recent_high + recent_low) / 2
        return 50000.0  # Базовая цена для BTC
    
    def _is_recent_sweep(self, sweep_time: datetime, hours: int = 24) -> bool:
        """Проверка, было ли снятие ликвидности недавно"""
        now = datetime.now()
        return (now - sweep_time).total_seconds() / 3600 <= hours
    
    def _has_bullish_structure_break(self, market_state: MarketState) -> bool:
        """Проверка наличия бычьего структурного break"""
        return (market_state.structure == MarketStructure.BULLISH or 
                market_state.trend_strength > 0.4)
    
    def _has_bearish_structure_break(self, market_state: MarketState) -> bool:
        """Проверка наличия медвежьего структурного break"""
        return (market_state.structure == MarketStructure.BEARISH or 
                market_state.trend_strength > 0.4)
    
    def _find_bullish_entry_pois(
        self, 
        market_state: MarketState, 
        liquidity_price: float
    ) -> List[POI]:
        """Поиск POI для бычьего входа"""
        suitable_pois = []
        
        for poi in market_state.active_pois:
            # Ищем POI ниже уровня снятой ликвидности
            if (poi.high_price < liquidity_price and 
                poi.poi_type in [POIType.ORDER_BLOCK, POIType.IMBALANCE, POIType.SUPPORT] and
                poi.strength > 0.5):
                suitable_pois.append(poi)
        
        # Сортируем по близости к уровню ликвидности и силе
        suitable_pois.sort(
            key=lambda p: (abs(p.mid_price - liquidity_price), -p.strength)
        )
        
        return suitable_pois[:3]  # Топ-3 POI
    
    def _find_bearish_entry_pois(
        self, 
        market_state: MarketState, 
        liquidity_price: float
    ) -> List[POI]:
        """Поиск POI для медвежьего входа"""
        suitable_pois = []
        
        for poi in market_state.active_pois:
            # Ищем POI выше уровня снятой ликвидности
            if (poi.low_price > liquidity_price and 
                poi.poi_type in [POIType.ORDER_BLOCK, POIType.IMBALANCE, POIType.RESISTANCE] and
                poi.strength > 0.5):
                suitable_pois.append(poi)
        
        # Сортируем по близости к уровню ликвидности и силе
        suitable_pois.sort(
            key=lambda p: (abs(p.mid_price - liquidity_price), -p.strength)
        )
        
        return suitable_pois[:3]  # Топ-3 POI
    
    def _calculate_bullish_target(self, market_state: MarketState, entry_price: float) -> float:
        """Расчет цели для бычьего сигнала"""
        # Ищем ближайшее сопротивление или BSL
        target = entry_price * 1.02  # Минимальная цель 2%
        
        # Ищем в пулах ликвидности
        for pool in market_state.liquidity_pools:
            if (pool.liquidity_type == LiquidityType.BSL and 
                pool.price > entry_price and 
                not pool.swept):
                target = max(target, pool.price * 0.99)  # Чуть не доходим до пула
        
        # Ищем в зонах сопротивления
        for poi in market_state.active_pois:
            if (poi.poi_type == POIType.RESISTANCE and 
                poi.low_price > entry_price):
                target = max(target, poi.low_price * 0.999)
        
        return min(target, entry_price * 1.08)  # Максимум 8% цель
    
    def _calculate_bearish_target(self, market_state: MarketState, entry_price: float) -> float:
        """Расчет цели для медвежьего сигнала"""
        # Ищем ближайшую поддержку или SSL
        target = entry_price * 0.98  # Минимальная цель -2%
        
        # Ищем в пулах ликвидности
        for pool in market_state.liquidity_pools:
            if (pool.liquidity_type == LiquidityType.SSL and 
                pool.price < entry_price and 
                not pool.swept):
                target = min(target, pool.price * 1.01)  # Чуть не доходим до пула
        
        # Ищем в зонах поддержки
        for poi in market_state.active_pois:
            if (poi.poi_type == POIType.SUPPORT and 
                poi.high_price < entry_price):
                target = min(target, poi.high_price * 1.001)
        
        return max(target, entry_price * 0.92)  # Максимум -8% цель
    
    def _calculate_liquidity_confluence(
        self, 
        liquidity_pools: List[LiquidityPool], 
        entry_price: float
    ) -> float:
        """Расчет конфлюенции ликвидности"""
        if not liquidity_pools:
            return 0.0
        
        score = 0.0
        for pool in liquidity_pools:
            distance = abs(pool.price - entry_price) / entry_price
            if distance < 0.05:  # В пределах 5%
                strength_factor = pool.strength
                distance_factor = 1.0 - (distance / 0.05)
                score += strength_factor * distance_factor
        
        return min(score, 1.0)
    
    def _calculate_poi_confluence(
        self, 
        active_pois: List[POI], 
        entry_price: float
    ) -> float:
        """Расчет конфлюенции зон интереса"""
        if not active_pois:
            return 0.0
        
        score = 0.0
        for poi in active_pois:
            if poi.contains_price(entry_price):
                score += poi.strength
            else:
                # Проверяем близость
                distance = min(
                    abs(poi.high_price - entry_price),
                    abs(poi.low_price - entry_price)
                ) / entry_price
                
                if distance < 0.02:  # В пределах 2%
                    distance_factor = 1.0 - (distance / 0.02)
                    score += poi.strength * distance_factor * 0.5
        
        return min(score, 1.0)
    
    def _calculate_swing_confluence(
        self, 
        swing_highs: List[SwingPoint], 
        swing_lows: List[SwingPoint], 
        entry_price: float
    ) -> float:
        """Расчет конфлюенции свинг-точек"""
        score = 0.0
        all_swings = swing_highs + swing_lows
        
        for swing in all_swings:
            distance = abs(swing.price - entry_price) / entry_price
            if distance < 0.01:  # В пределах 1%
                strength_factor = swing.strength
                distance_factor = 1.0 - (distance / 0.01)
                score += strength_factor * distance_factor * 0.3
        
        return min(score, 1.0)
    
    def _calculate_fibonacci_confluence(
        self, 
        fib_levels: Dict[float, float], 
        entry_price: float
    ) -> float:
        """Расчет конфлюенции уровней Фибоначчи"""
        if not fib_levels:
            return 0.0
        
        score = 0.0
        important_levels = [0.382, 0.5, 0.618, 0.786]  # Важные уровни
        
        for ratio, price in fib_levels.items():
            distance = abs(price - entry_price) / entry_price
            if distance < 0.005:  # В пределах 0.5%
                if ratio in important_levels:
                    score += 0.4
                else:
                    score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_time_confluence(self, timestamp: datetime) -> float:
        """Расчет временной конфлюенции (сессии)"""
        hour_utc = timestamp.hour
        
        # Лондонская сессия: 8-16 UTC
        # Нью-Йоркская сессия: 13-21 UTC
        # Перекрытие: 13-16 UTC
        
        if 13 <= hour_utc <= 16:  # Перекрытие сессий
            return 1.0
        elif 8 <= hour_utc <= 16 or 13 <= hour_utc <= 21:  # Активные сессии
            return 0.7
        else:  # Азиатская сессия
            return 0.3
    
    def _analyze_bullish_confluence(
        self, 
        market_state: MarketState, 
        liquidity_pool: LiquidityPool, 
        poi: POI
    ) -> Dict[str, float]:
        """Анализ конфлюенции факторов для бычьего setup"""
        return {
            'liquidity_strength': liquidity_pool.strength,
            'poi_strength': poi.strength,
            'structure_alignment': 1.0 if market_state.structure == MarketStructure.BULLISH else 0.5,
            'trend_strength': market_state.trend_strength,
            'time_factor': self._calculate_time_confluence(market_state.timestamp)
        }
    
    def _analyze_bearish_confluence(
        self, 
        market_state: MarketState, 
        liquidity_pool: LiquidityPool, 
        poi: POI
    ) -> Dict[str, float]:
        """Анализ конфлюенции факторов для медвежьего setup"""
        return {
            'liquidity_strength': liquidity_pool.strength,
            'poi_strength': poi.strength,
            'structure_alignment': 1.0 if market_state.structure == MarketStructure.BEARISH else 0.5,
            'trend_strength': market_state.trend_strength,
            'time_factor': self._calculate_time_confluence(market_state.timestamp)
        }
    
    def _check_bias_alignment(self, signal: Signal, context: ContextState) -> bool:
        """Проверка соответствия глобальному bias"""
        if context.confidence_level < 0.3:  # Низкая уверенность - пропускаем проверку
            return True
        
        global_bias = getattr(context, 'bias', 'neutral')
        
        if global_bias == 'neutral':
            return True
        elif global_bias == 'bullish' and signal.is_long:
            return True
        elif global_bias == 'bearish' and signal.is_short:
            return True
        else:
            return False
    
    def _has_recent_signal_nearby(self, signal: Signal, hours: int = 4) -> bool:
        """Проверка наличия недавних сигналов поблизости"""
        cutoff_time = signal.timestamp - timedelta(hours=hours)
        
        for recent_signal in self._signal_history:
            if recent_signal.timestamp < cutoff_time:
                continue
            
            # Проверяем близость по цене
            price_distance = abs(recent_signal.entry_price - signal.entry_price) / signal.entry_price
            if price_distance < 0.01:  # В пределах 1%
                return True
        
        return False
    
    def _check_emotional_filters(self, signal: Signal, context: ContextState) -> bool:
        """Проверка эмоциональных факторов"""
        # Фактор страха - снижает агрессивность
        if context.fear_factor > 0.7 and signal.confluence_score < 0.8:
            return False
        
        # Фактор жадности - может блокировать хорошие сигналы
        if context.greed_factor > 0.7 and signal.risk_reward_ratio > 3.0:
            return False
        
        return True
    
    def _calculate_bullish_levels(self, market_state: MarketState, current_price: float) -> Tuple[float, float, float]:
        """Расчет уровней для бычьего сигнала"""
        try:
            # Ищем ближайший POI для входа
            entry_poi = None
            for poi in market_state.active_pois:
                if (poi.poi_type in [POIType.ORDER_BLOCK, POIType.SUPPORT, POIType.IMBALANCE] and
                    poi.low_price <= current_price <= poi.high_price + poi.price_range * 0.1):
                    entry_poi = poi
                    break
            
            if entry_poi:
                entry_price = entry_poi.low_price + (entry_poi.price_range * 0.2)
                stop_loss = entry_poi.low_price - (entry_poi.price_range * 0.5)
                take_profit = self._calculate_bullish_target(market_state, entry_price)
            else:
                # Базовые уровни
                entry_price = current_price
                stop_loss = current_price * 0.98
                take_profit = current_price * 1.04
            
            return (entry_price, stop_loss, take_profit)
            
        except Exception as e:
            logger.error(f"Ошибка расчета бычьих уровней: {e}")
            return (current_price, current_price * 0.98, current_price * 1.04)
    
    def _calculate_bearish_levels(self, market_state: MarketState, current_price: float) -> Tuple[float, float, float]:
        """Расчет уровней для медвежьего сигнала"""
        try:
            # Ищем ближайший POI для входа
            entry_poi = None
            for poi in market_state.active_pois:
                if (poi.poi_type in [POIType.ORDER_BLOCK, POIType.RESISTANCE, POIType.IMBALANCE] and
                    poi.low_price - poi.price_range * 0.1 <= current_price <= poi.high_price):
                    entry_poi = poi
                    break
            
            if entry_poi:
                entry_price = entry_poi.high_price - (entry_poi.price_range * 0.2)
                stop_loss = entry_poi.high_price + (entry_poi.price_range * 0.5)
                take_profit = self._calculate_bearish_target(market_state, entry_price)
            else:
                # Базовые уровни
                entry_price = current_price
                stop_loss = current_price * 1.02
                take_profit = current_price * 0.96
            
            return (entry_price, stop_loss, take_profit)
            
        except Exception as e:
            logger.error(f"Ошибка расчета медвежьих уровней: {e}")
            return (current_price, current_price * 1.02, current_price * 0.96)


# Alias for compatibility
SignalGenerator = LiquidityHuntSignalGenerator