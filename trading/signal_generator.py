"""
Генератор торговых сигналов для стратегии "Охота за ликвидностью"
СТРОГО СЛЕДУЕТ ОПИСАННОЙ СТРАТЕГИИ
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
    """
    Генератор сигналов по стратегии "Охота за ликвидностью"
    СТРОГО СЛЕДУЕТ ИЕРАРХИИ ТАЙМФРЕЙМОВ И АЛГОРИТМУ СТРАТЕГИИ
    """
    
    def __init__(self):
        self.config = get_config()
        self._signal_history: List[Signal] = []
        self._htf_analysis: Dict[str, Any] = {}  # Анализ высших таймфреймов
        self._manipulation_detected: Dict[str, Any] = {}  # Детекция манипуляции
        
    def generate_signals(
        self, 
        market_state: MarketState, 
        context: ContextState
    ) -> List[Signal]:
        """
        ПОШАГОВАЯ ГЕНЕРАЦИЯ СИГНАЛОВ СОГЛАСНО СТРАТЕГИИ:
        1. HTF Analysis (D1/H4) - Определение bias и целей
        2. Manipulation Detection - Поиск снятия ликвидности
        3. LTF Confirmation (M15/M5) - ChoCh и POI
        4. Sniper Entry (M1) - Точный вход
        """
        try:
            signals = []
            
            # ЭТАП 1: СТРАТЕГИЧЕСКИЙ АНАЛИЗ (HTF)
            if not self._perform_htf_analysis(market_state):
                logger.debug("HTF анализ не пройден - нет сигналов")
                return signals
            
            # ЭТАП 2: ПОИСК МАНИПУЛЯЦИИ
            manipulation_setups = self._detect_manipulation(market_state)
            if not manipulation_setups:
                logger.debug("Манипуляция не обнаружена - нет сигналов")
                return signals
            
            # ЭТАП 3: LTF ПОДТВЕРЖДЕНИЕ
            for setup in manipulation_setups:
                confirmed_setups = self._confirm_ltf_structure_break(setup, market_state)
                
                # ЭТАП 4: ГЕНЕРАЦИЯ СИГНАЛОВ
                for confirmed_setup in confirmed_setups:
                    signal = self._create_liquidity_hunt_signal(confirmed_setup, market_state, context)
                    if signal and self._validate_signal(signal, context):
                        signals.append(signal)
            
            # Фильтруем сигналы по качеству
            filtered_signals = self.filter_signals(signals, context)
            
            if filtered_signals:
                logger.info(f"Сгенерировано {len(filtered_signals)} сигналов 'Охота за ликвидностью'")
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Ошибка генерации сигналов: {e}")
            raise SignalGenerationError(f"Не удалось сгенерировать сигналы: {e}")
    
    def _perform_htf_analysis(self, market_state: MarketState) -> bool:
        """
        ЭТАП 1: СТРАТЕГИЧЕСКИЙ АНАЛИЗ (D1/H4)
        Определяем глобальный bias и ключевые цели
        """
        try:
            # Проверяем, что анализируем HTF
            if market_state.timeframe.value not in self.config.trading.strategic_timeframes:
                return True  # Если не HTF, пропускаем анализ
            
            # Определяем глобальную структуру
            if market_state.structure == MarketStructure.UNDEFINED:
                return False
            
            # Находим ключевые пулы ликвидности для целей
            target_pools = self._identify_target_liquidity_pools(market_state)
            if not target_pools:
                return False
            
            # Находим зоны-ловушки для манипуляции
            trap_zones = self._identify_trap_zones(market_state)
            
            # Сохраняем HTF анализ
            self._htf_analysis = {
                'bias': market_state.structure,
                'target_pools': target_pools,
                'trap_zones': trap_zones,
                'trend_strength': market_state.trend_strength,
                'timestamp': market_state.timestamp
            }
            
            logger.info(f"HTF анализ: bias={market_state.structure.value}, "
                       f"цели={len(target_pools)}, ловушки={len(trap_zones)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка HTF анализа: {e}")
            return False
    
    def _detect_manipulation(self, market_state: MarketState) -> List[Dict[str, Any]]:
        """
        ЭТАП 2: ДЕТЕКЦИЯ МАНИПУЛЯЦИИ
        Поиск снятия ликвидности и формирования ловушек
        """
        try:
            manipulation_setups = []
            
            if not self._htf_analysis:
                return manipulation_setups
            
            bias = self._htf_analysis['bias']
            trap_zones = self._htf_analysis.get('trap_zones', [])
            
            # Ищем снятие ликвидности в trap зонах
            for trap_zone in trap_zones:
                swept_pools = self._check_liquidity_sweep_in_zone(market_state, trap_zone)
                
                if swept_pools:
                    # Проверяем формирование новой ловушки
                    new_trap = self._check_trap_formation(market_state, trap_zone, swept_pools)
                    
                    if new_trap:
                        setup = {
                            'type': 'liquidity_manipulation',
                            'bias': bias,
                            'swept_pools': swept_pools,
                            'trap_zone': trap_zone,
                            'new_trap': new_trap,
                            'manipulation_time': market_state.timestamp
                        }
                        manipulation_setups.append(setup)
                        
                        logger.info(f"Обнаружена манипуляция: {setup['type']}, "
                                   f"снято пулов: {len(swept_pools)}")
            
            return manipulation_setups
            
        except Exception as e:
            logger.error(f"Ошибка детекции манипуляции: {e}")
            return []
    
    def _confirm_ltf_structure_break(
        self, 
        manipulation_setup: Dict[str, Any], 
        market_state: MarketState
    ) -> List[Dict[str, Any]]:
        """
        ЭТАП 3: LTF ПОДТВЕРЖДЕНИЕ
        Ищем Change of Character (ChoCh) на тактических таймфреймах
        """
        try:
            confirmed_setups = []
            
            # Проверяем, что мы на тактическом таймфрейме
            if market_state.timeframe.value not in self.config.trading.tactical_timeframes:
                return confirmed_setups
            
            bias = manipulation_setup['bias']
            
            # Ищем структурный break (ChoCh)
            choch_detected = self._detect_change_of_character(market_state, bias)
            
            if choch_detected:
                # Ищем POI для входа
                entry_pois = self._find_entry_pois_after_choch(market_state, manipulation_setup)
                
                for poi in entry_pois:
                    # Проверяем Premium/Discount зону
                    if self._validate_premium_discount_zone(poi, market_state, bias):
                        setup = {
                            **manipulation_setup,
                            'choch_confirmed': True,
                            'choch_details': choch_detected,
                            'entry_poi': poi,
                            'ltf_timeframe': market_state.timeframe
                        }
                        confirmed_setups.append(setup)
                        
                        logger.info(f"ChoCh подтвержден на {market_state.timeframe.value}, "
                                   f"POI: {poi.poi_type.value}")
            
            return confirmed_setups
            
        except Exception as e:
            logger.error(f"Ошибка LTF подтверждения: {e}")
            return []
    
    def _create_liquidity_hunt_signal(
        self, 
        setup: Dict[str, Any], 
        market_state: MarketState, 
        context: ContextState
    ) -> Optional[Signal]:
        """Создание сигнала на основе подтвержденной установки"""
        try:
            bias = setup['bias']
            poi = setup['entry_poi']
            
            # Определяем направление сигнала
            if bias == MarketStructure.BULLISH:
                signal_type = SignalType.BUY
                entry_price = poi.low_price + (poi.price_range * 0.2)  # В нижней части POI
                stop_loss = poi.low_price - (poi.price_range * 0.5)    # Под POI
                take_profit = self._calculate_bullish_target(setup, entry_price)
            else:  # BEARISH
                signal_type = SignalType.SELL
                entry_price = poi.high_price - (poi.price_range * 0.2)  # В верхней части POI
                stop_loss = poi.high_price + (poi.price_range * 0.5)    # Над POI
                take_profit = self._calculate_bearish_target(setup, entry_price)
            
            # Рассчитываем конфлюенцию
            confluence_score = self.calculate_confluence_score(market_state, entry_price, setup)
            
            # Создаем сигнал
            signal = Signal(
                timestamp=market_state.timestamp,
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confluence_score=confluence_score,
                timeframe=market_state.timeframe,
                market_structure=bias,
                liquidity_context=setup.get('swept_pools', []),
                poi_context=[poi],
                strategy_version="1.0",
                notes=f"Liquidity Hunt: {bias.value} bias, ChoCh confirmed, POI: {poi.poi_type.value}"
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Ошибка создания сигнала: {e}")
            return None
    
    def calculate_confluence_score(
        self, 
        market_state: MarketState, 
        entry_price: float,
        setup: Dict[str, Any] = None
    ) -> float:
        """Расчет скора конфлюенции согласно весам стратегии"""
        try:
            score = 0.0
            weights = self.config.strategy.confluence_weights
            
            # 1. Market Structure (20%) - Соответствие глобальному тренду
            if setup and setup.get('bias') == market_state.structure:
                if market_state.trend_strength > 0.7:
                    score += weights['market_structure']
                elif market_state.trend_strength > 0.4:
                    score += weights['market_structure'] * 0.5
            
            # 2. Liquidity (25%) - Близость к пулам ликвидности
            liquidity_score = self._calculate_liquidity_confluence(
                market_state.liquidity_pools, entry_price
            )
            score += liquidity_score * weights['liquidity']
            
            # 3. POI (25%) - Совпадение с зонами интереса
            poi_score = self._calculate_poi_confluence(
                market_state.active_pois, entry_price
            )
            score += poi_score * weights['poi']
            
            # 4. Swing Structure (15%) - Уважение ключевых уровней
            swing_score = self._calculate_swing_confluence(
                market_state.swing_highs, market_state.swing_lows, entry_price
            )
            score += swing_score * weights['swing_structure']
            
            # 5. Fibonacci (10%) - Совпадение с Фибо уровнями
            fib_score = self._calculate_fibonacci_confluence(
                market_state.fibonacci_levels, entry_price
            )
            score += fib_score * weights['fibonacci']
            
            # 6. Time (5%) - Активные торговые сессии
            time_score = self._calculate_time_confluence(market_state.timestamp)
            score += time_score * weights['time']
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Ошибка расчета конфлюенции: {e}")
            return 0.5
    
    def filter_signals(
        self, 
        signals: List[Signal], 
        context: ContextState
    ) -> List[Signal]:
        """Фильтрация сигналов по критериям стратегии"""
        try:
            if not signals:
                return []
            
            filtered = []
            
            for signal in signals:
                # 1. Минимальный скор конфлюенции
                if signal.confluence_score < self.config.trading.min_confluence_score:
                    continue
                
                # 2. Минимальное R:R
                if signal.risk_reward_ratio < self.config.trading.min_rr_ratio:
                    continue
                
                # 3. Соответствие HTF bias
                if not self._check_htf_bias_alignment(signal):
                    continue
                
                # 4. Нет недавних сигналов поблизости
                if self._has_recent_signal_nearby(signal):
                    continue
                
                filtered.append(signal)
            
            # Сортируем по качеству и берем лучшие
            filtered.sort(key=lambda s: s.confluence_score, reverse=True)
            
            return filtered[:3]  # Максимум 3 сигнала
            
        except Exception as e:
            logger.error(f"Ошибка фильтрации сигналов: {e}")
            return signals
    
    # Вспомогательные методы для детекции элементов стратегии
    
    def _identify_target_liquidity_pools(self, market_state: MarketState) -> List[LiquidityPool]:
        """Поиск ключевых пулов ликвидности для целей"""
        target_pools = []
        
        for pool in market_state.liquidity_pools:
            # Фильтруем по силе и возрасту
            if (pool.strength >= 0.7 and 
                pool.age >= self.config.strategy.min_liquidity_age):
                target_pools.append(pool)
        
        # Сортируем по силе
        target_pools.sort(key=lambda p: p.strength, reverse=True)
        return target_pools[:5]  # Топ-5 целей
    
    def _identify_trap_zones(self, market_state: MarketState) -> List[Dict[str, Any]]:
        """Поиск зон-ловушек для манипуляции"""
        trap_zones = []
        
        # Ищем S/R уровни, которые могут стать ловушками
        for poi in market_state.active_pois:
            if poi.poi_type in [POIType.SUPPORT, POIType.RESISTANCE]:
                if poi.test_count >= 2:  # Уже тестировался
                    trap_zone = {
                        'poi': poi,
                        'type': 'support_resistance_trap',
                        'strength': poi.strength,
                        'test_count': poi.test_count
                    }
                    trap_zones.append(trap_zone)
        
        return trap_zones
    
    def _check_liquidity_sweep_in_zone(
        self, 
        market_state: MarketState, 
        trap_zone: Dict[str, Any]
    ) -> List[LiquidityPool]:
        """Проверка снятия ликвидности в зоне ловушки"""
        swept_pools = []
        
        for pool in market_state.liquidity_pools:
            if pool.swept:
                # Проверяем, что снятие произошло недавно
                if pool.swept_at:
                    hours_since_sweep = (datetime.now() - pool.swept_at).total_seconds() / 3600
                    if hours_since_sweep <= self.config.strategy.manipulation_detection_hours:
                        swept_pools.append(pool)
        
        return swept_pools
    
    def _check_trap_formation(
        self, 
        market_state: MarketState, 
        trap_zone: Dict[str, Any], 
        swept_pools: List[LiquidityPool]
    ) -> Optional[Dict[str, Any]]:
        """Проверка формирования новой ловушки после снятия ликвидности"""
        if not swept_pools:
            return None
        
        # Симуляция: новая ловушка формируется, если снято SSL/BSL
        # и цена вернулась к уровню, создавая новые стопы
        
        return {
            'type': 'new_trap_formed',
            'original_zone': trap_zone,
            'swept_liquidity': swept_pools,
            'new_stops_expected': True
        }
    
    def _detect_change_of_character(
        self, 
        market_state: MarketState, 
        bias: MarketStructure
    ) -> Optional[Dict[str, Any]]:
        """Детекция Change of Character (слом структуры)"""
        if not market_state.swing_highs or not market_state.swing_lows:
            return None
        
        # Для бычьего bias ищем пробой последнего значимого максимума
        if bias == MarketStructure.BULLISH:
            last_high = max(market_state.swing_highs, key=lambda x: x.timestamp)
            # Симуляция: ChoCh происходит при пробое свинг-хая
            return {
                'type': 'bullish_choch',
                'broken_level': last_high.price,
                'strength': last_high.strength
            }
        
        # Для медвежьего bias ищем пробой последнего значимого минимума
        elif bias == MarketStructure.BEARISH:
            last_low = max(market_state.swing_lows, key=lambda x: x.timestamp)
            return {
                'type': 'bearish_choch',
                'broken_level': last_low.price,
                'strength': last_low.strength
            }
        
        return None
    
    def _find_entry_pois_after_choch(
        self, 
        market_state: MarketState, 
        manipulation_setup: Dict[str, Any]
    ) -> List[POI]:
        """Поиск POI для входа после ChoCh"""
        entry_pois = []
        bias = manipulation_setup['bias']
        
        for poi in market_state.active_pois:
            # Для бычьего bias ищем POI ниже уровня манипуляции
            if bias == MarketStructure.BULLISH:
                if poi.poi_type in [POIType.ORDER_BLOCK, POIType.IMBALANCE, POIType.SUPPORT]:
                    if poi.strength > 0.6:
                        entry_pois.append(poi)
            
            # Для медвежьего bias ищем POI выше уровня манипуляции
            elif bias == MarketStructure.BEARISH:
                if poi.poi_type in [POIType.ORDER_BLOCK, POIType.IMBALANCE, POIType.RESISTANCE]:
                    if poi.strength > 0.6:
                        entry_pois.append(poi)
        
        # Сортируем по силе
        entry_pois.sort(key=lambda p: p.strength, reverse=True)
        return entry_pois[:3]  # Топ-3 POI
    
    def _validate_premium_discount_zone(
        self, 
        poi: POI, 
        market_state: MarketState, 
        bias: MarketStructure
    ) -> bool:
        """Проверка нахождения в правильной Premium/Discount зоне"""
        # Для бычьего bias входим в discount зоне (ниже 0.5 Фибо)
        # Для медвежьего bias входим в premium зоне (выше 0.5 Фибо)
        
        # Упрощенная проверка через цену POI относительно недавнего диапазона
        if not market_state.swing_highs or not market_state.swing_lows:
            return True
        
        recent_high = max(s.price for s in market_state.swing_highs[-3:])
        recent_low = min(s.price for s in market_state.swing_lows[-3:])
        range_size = recent_high - recent_low
        fib_50 = recent_low + (range_size * 0.5)
        
        if bias == MarketStructure.BULLISH:
            # Для лонга POI должен быть в discount (ниже 50% Фибо)
            return poi.mid_price < fib_50
        else:
            # Для шорта POI должен быть в premium (выше 50% Фибо)
            return poi.mid_price > fib_50
    
    def _calculate_bullish_target(self, setup: Dict[str, Any], entry_price: float) -> float:
        """Расчет цели для бычьего сигнала - ближайший BSL"""
        target_pools = setup.get('target_pools', self._htf_analysis.get('target_pools', []))
        
        # Ищем ближайший BSL выше входа
        bullish_targets = [p for p in target_pools 
                          if p.liquidity_type == LiquidityType.BSL and p.price > entry_price]
        
        if bullish_targets:
            nearest_target = min(bullish_targets, key=lambda p: abs(p.price - entry_price))
            return nearest_target.price
        
        # Если нет BSL, используем минимальный R:R
        return entry_price * 1.04  # 4% цель
    
    def _calculate_bearish_target(self, setup: Dict[str, Any], entry_price: float) -> float:
        """Расчет цели для медвежьего сигнала - ближайший SSL"""
        target_pools = setup.get('target_pools', self._htf_analysis.get('target_pools', []))
        
        # Ищем ближайший SSL ниже входа
        bearish_targets = [p for p in target_pools 
                          if p.liquidity_type == LiquidityType.SSL and p.price < entry_price]
        
        if bearish_targets:
            nearest_target = min(bearish_targets, key=lambda p: abs(p.price - entry_price))
            return nearest_target.price
        
        # Если нет SSL, используем минимальный R:R
        return entry_price * 0.96  # 4% цель
    
    def _validate_signal(self, signal: Signal, context: ContextState) -> bool:
        """Валидация сигнала"""
        try:
            # Проверяем R:R
            if signal.risk_reward_ratio < self.config.trading.min_rr_ratio:
                return False
            
            # Проверяем конфлюенцию
            if signal.confluence_score < self.config.trading.min_confluence_score:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка валидации сигнала: {e}")
            return False
    
    def _check_htf_bias_alignment(self, signal: Signal) -> bool:
        """Проверка соответствия HTF bias"""
        if not self._htf_analysis:
            return True
        
        htf_bias = self._htf_analysis.get('bias')
        return signal.market_structure == htf_bias
    
    def _has_recent_signal_nearby(self, signal: Signal, hours: int = 4) -> bool:
        """Проверка наличия недавних сигналов поблизости"""
        for recent_signal in self._signal_history[-10:]:  # Последние 10 сигналов
            # Проверяем время
            time_diff = (signal.timestamp - recent_signal.timestamp).total_seconds() / 3600
            if time_diff <= hours:
                # Проверяем близость по цене
                price_diff = abs(signal.entry_price - recent_signal.entry_price) / recent_signal.entry_price
                if price_diff <= 0.01:  # 1% близость
                    return True
        
        return False
    
    # Методы расчета конфлюенции (сокращенные версии)
    
    def _calculate_liquidity_confluence(self, pools: List[LiquidityPool], price: float) -> float:
        """Конфлюенция с пулами ликвидности"""
        if not pools:
            return 0.0
        
        closest_pool = min(pools, key=lambda p: abs(p.price - price))
        distance = abs(closest_pool.price - price) / price
        
        if distance <= 0.005:  # Очень близко
            return closest_pool.strength
        elif distance <= 0.01:  # Близко
            return closest_pool.strength * 0.7
        else:
            return 0.0
    
    def _calculate_poi_confluence(self, pois: List[POI], price: float) -> float:
        """Конфлюенция с зонами интереса"""
        for poi in pois:
            if poi.contains_price(price):
                return poi.strength
        
        return 0.0
    
    def _calculate_swing_confluence(self, highs: List[SwingPoint], lows: List[SwingPoint], price: float) -> float:
        """Конфлюенция со свинг-уровнями"""
        all_swings = highs + lows
        if not all_swings:
            return 0.0
        
        closest_swing = min(all_swings, key=lambda s: abs(s.price - price))
        distance = abs(closest_swing.price - price) / price
        
        if distance <= 0.002:  # 0.2%
            return closest_swing.strength
        else:
            return 0.0
    
    def _calculate_fibonacci_confluence(self, fib_levels: Dict[float, float], price: float) -> float:
        """Конфлюенция с уровнями Фибоначчи"""
        if not fib_levels:
            return 0.0
        
        for level, fib_price in fib_levels.items():
            distance = abs(fib_price - price) / price
            if distance <= 0.003:  # 0.3%
                # Важные уровни: 0.618, 0.5, 0.382
                if level in [0.618, 0.5, 0.382]:
                    return 0.8
                else:
                    return 0.5
        
        return 0.0
    
    def _calculate_time_confluence(self, timestamp: datetime) -> float:
        """Конфлюенция по времени (торговые сессии)"""
        hour = timestamp.hour
        
        # Лондонская сессия (8-16 UTC)
        if 8 <= hour <= 16:
            return 1.0
        # Нью-Йоркская сессия (13-21 UTC)
        elif 13 <= hour <= 21:
            return 1.0
        # Пересечение сессий (13-16 UTC)
        elif 13 <= hour <= 16:
            return 1.0
        else:
            return 0.3
    
    def determine_entry_levels(
        self, 
        market_state: MarketState, 
        signal_direction: str
    ) -> Tuple[float, float, float]:
        """Определение уровней входа, стопа и тейка согласно стратегии"""
        try:
            # Получаем текущую цену
            current_price = self._get_current_price_from_market_state(market_state)
            
            if signal_direction == "bullish" or signal_direction == "buy":
                return self._calculate_bullish_levels_from_market_state(market_state, current_price)
            else:
                return self._calculate_bearish_levels_from_market_state(market_state, current_price)
                
        except Exception as e:
            logger.error(f"Ошибка определения уровней: {e}")
            # Возвращаем базовые уровни
            current_price = self._get_current_price_from_market_state(market_state)
            if signal_direction in ["bullish", "buy"]:
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
    
    def _get_current_price_from_market_state(self, market_state: MarketState) -> float:
        """Получение текущей цены из состояния рынка"""
        # Используем среднюю цену последних свингов как приближение
        if market_state.swing_highs and market_state.swing_lows:
            recent_high = max(market_state.swing_highs, key=lambda x: x.timestamp).price
            recent_low = max(market_state.swing_lows, key=lambda x: x.timestamp).price
            return (recent_high + recent_low) / 2
        return 50000.0  # Базовая цена для BTC
    
    def _calculate_bullish_levels_from_market_state(self, market_state: MarketState, current_price: float) -> Tuple[float, float, float]:
        """Расчет уровней для бычьего сигнала"""
        try:
            # Ищем ближайший POI для входа
            entry_poi = None
            for poi in market_state.active_pois:
                if (poi.low_price <= current_price <= poi.high_price + poi.price_range * 0.1):
                    entry_poi = poi
                    break
            
            if entry_poi:
                entry_price = entry_poi.low_price + (entry_poi.price_range * 0.2)
                stop_loss = entry_poi.low_price - (entry_poi.price_range * 0.5)
                take_profit = self._calculate_bullish_target({}, entry_price)
            else:
                # Базовые уровни
                entry_price = current_price
                stop_loss = current_price * 0.98
                take_profit = current_price * 1.04
            
            return (entry_price, stop_loss, take_profit)
            
        except Exception as e:
            logger.error(f"Ошибка расчета бычьих уровней: {e}")
            return (current_price, current_price * 0.98, current_price * 1.04)
    
    def _calculate_bearish_levels_from_market_state(self, market_state: MarketState, current_price: float) -> Tuple[float, float, float]:
        """Расчет уровней для медвежьего сигнала"""
        try:
            # Ищем ближайший POI для входа
            entry_poi = None
            for poi in market_state.active_pois:
                if (poi.low_price - poi.price_range * 0.1 <= current_price <= poi.high_price):
                    entry_poi = poi
                    break
            
            if entry_poi:
                entry_price = entry_poi.high_price - (entry_poi.price_range * 0.2)
                stop_loss = entry_poi.high_price + (entry_poi.price_range * 0.5)
                take_profit = self._calculate_bearish_target({}, entry_price)
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