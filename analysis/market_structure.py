"""
Анализатор структуры рынка для стратегии "Охота за ликвидностью"
СТРОГО СООТВЕТСТВУЕТ ОПИСАННОЙ СТРАТЕГИИ
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger

from core.interfaces import IMarketStructureAnalyzer
from core.data_types import (
    MarketStructure, SwingPoint, TimeFrame, OHLCV
)
from core.exceptions import StructureAnalysisError
from config import get_config


class MarketStructureAnalyzer(IMarketStructureAnalyzer):
    """
    Анализатор структуры рынка
    СТРОГО СООТВЕТСТВУЕТ ПРИНЦИПАМ СТРАТЕГИИ "ОХОТА ЗА ЛИКВИДНОСТЬЮ"
    """
    
    def __init__(self):
        self.config = get_config()
        self._swing_cache: Dict[str, List[SwingPoint]] = {}
        
    def analyze_structure(self, data: pd.DataFrame) -> MarketStructure:
        """
        Анализ структуры рынка согласно стратегии:
        - Бычья: Higher Highs + Higher Lows
        - Медвежья: Lower Lows + Lower Highs  
        - Боковик: нет четкого тренда
        """
        try:
            if len(data) < self.config.strategy.trend_min_swings * 2:
                return MarketStructure.UNDEFINED
            
            # Определяем свинги
            swing_highs, swing_lows = self.detect_swings(data)
            
            if len(swing_highs) < 2 or len(swing_lows) < 2:
                return MarketStructure.UNDEFINED
            
            # Анализируем тренд на основе последних свингов
            recent_highs = swing_highs[-3:] if len(swing_highs) >= 3 else swing_highs
            recent_lows = swing_lows[-3:] if len(swing_lows) >= 3 else swing_lows
            
            # Проверяем бычью структуру (Higher Highs и Higher Lows)
            bullish_hh = self._check_higher_highs(recent_highs)
            bullish_hl = self._check_higher_lows(recent_lows)
            
            # Проверяем медвежью структуру (Lower Lows и Lower Highs)
            bearish_ll = self._check_lower_lows(recent_lows)
            bearish_lh = self._check_lower_highs(recent_highs)
            
            # Определяем структуру строго по стратегии
            if bullish_hh and bullish_hl:
                structure = MarketStructure.BULLISH
            elif bearish_ll and bearish_lh:
                structure = MarketStructure.BEARISH
            else:
                # Проверяем боковое движение
                if self._is_ranging(recent_highs, recent_lows):
                    structure = MarketStructure.RANGING
                else:
                    structure = MarketStructure.UNDEFINED
            
            logger.debug(f"Анализ структуры: {structure.value}")
            return structure
            
        except Exception as e:
            logger.error(f"Ошибка анализа структуры рынка: {e}")
            raise StructureAnalysisError(f"Не удалось проанализировать структуру: {e}")
    
    def detect_swings(self, data: pd.DataFrame) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """
        Детекция свинг-точек по методу N-bar lookback
        Именно так описано в стратегии
        """
        try:
            lookback = self.config.trading.swing_detection_lookback
            
            if len(data) < lookback * 2 + 1:
                return [], []
            
            swing_highs = []
            swing_lows = []
            
            # Используем N-bar lookback метод
            for i in range(lookback, len(data) - lookback):
                current_bar = data.iloc[i]
                timestamp = current_bar.name if hasattr(current_bar, 'name') else datetime.now()
                
                # Проверка свинг-хая (N баров слева и справа должны быть ниже)
                is_swing_high = True
                for j in range(i - lookback, i + lookback + 1):
                    if j != i and data.iloc[j]['high'] >= current_bar['high']:
                        is_swing_high = False
                        break
                
                if is_swing_high:
                    strength = self._calculate_swing_strength(data, i, True, lookback)
                    swing_high = SwingPoint(
                        timestamp=timestamp,
                        price=current_bar['high'],
                        is_high=True,
                        strength=strength,
                        confirmed=True
                    )
                    swing_highs.append(swing_high)
                
                # Проверка свинг-лоу (N баров слева и справа должны быть выше)
                is_swing_low = True
                for j in range(i - lookback, i + lookback + 1):
                    if j != i and data.iloc[j]['low'] <= current_bar['low']:
                        is_swing_low = False
                        break
                
                if is_swing_low:
                    strength = self._calculate_swing_strength(data, i, False, lookback)
                    swing_low = SwingPoint(
                        timestamp=timestamp,
                        price=current_bar['low'],
                        is_high=False,
                        strength=strength,
                        confirmed=True
                    )
                    swing_lows.append(swing_low)
            
            # Фильтруем слишком близкие свинги
            swing_highs = self._filter_close_swings(swing_highs)
            swing_lows = self._filter_close_swings(swing_lows)
            
            logger.debug(f"Обнаружено {len(swing_highs)} свинг-хаев и {len(swing_lows)} свинг-лоу")
            return swing_highs, swing_lows
            
        except Exception as e:
            logger.error(f"Ошибка детекции свингов: {e}")
            raise StructureAnalysisError(f"Не удалось детектировать свинги: {e}")
    
    def confirm_structure_break(
        self, 
        data: pd.DataFrame, 
        current_structure: MarketStructure
    ) -> bool:
        """
        Подтверждение Change of Character (ChoCh)
        Ключевой элемент стратегии
        """
        try:
            if current_structure == MarketStructure.UNDEFINED:
                return False
            
            # Получаем последние свинги
            swing_highs, swing_lows = self.detect_swings(data)
            
            if not swing_highs or not swing_lows:
                return False
            
            # Для подтверждения нужно закрытие тела свечи за уровнем
            confirmation_bars = self.config.strategy.structure_confirmation_bars
            
            if len(data) < confirmation_bars:
                return False
            
            latest_closes = data['close'].iloc[-confirmation_bars:]
            
            if current_structure == MarketStructure.BULLISH:
                # Для бычьего тренда ищем пробой последнего значимого лоу
                last_significant_low = self._get_last_significant_swing(swing_lows, False)
                if last_significant_low:
                    # ChoCh = закрытие тела ниже свинг-лоу
                    if any(close < last_significant_low.price for close in latest_closes):
                        logger.info(f"Подтвержден ChoCh бычьей структуры на {last_significant_low.price}")
                        return True
                    
            elif current_structure == MarketStructure.BEARISH:
                # Для медвежьего тренда ищем пробой последнего значимого хая
                last_significant_high = self._get_last_significant_swing(swing_highs, True)
                if last_significant_high:
                    # ChoCh = закрытие тела выше свинг-хая
                    if any(close > last_significant_high.price for close in latest_closes):
                        logger.info(f"Подтвержден ChoCh медвежьей структуры на {last_significant_high.price}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка подтверждения ChoCh: {e}")
            return False
    
    def calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Простой расчет силы тренда"""
        try:
            if len(data) < 20:
                return 0.0
            
            # Используем наклон EMA для простоты
            ema_period = 20
            ema = data['close'].ewm(span=ema_period).mean()
            
            if len(ema) < 5:
                return 0.0
                
            ema_slope = (ema.iloc[-1] - ema.iloc[-5]) / ema.iloc[-5]
            ema_strength = min(abs(ema_slope) * 1000, 1.0)  # Нормализуем
            
            return ema_strength
            
        except Exception as e:
            logger.error(f"Ошибка расчета силы тренда: {e}")
            return 0.0
    
    def get_current_swing_points(self, data: pd.DataFrame) -> Dict[str, List[SwingPoint]]:
        """Получение текущих свинг-точек"""
        try:
            swing_highs, swing_lows = self.detect_swings(data)
            return {
                'highs': swing_highs,
                'lows': swing_lows
            }
        except Exception as e:
            logger.error(f"Ошибка получения свинг-точек: {e}")
            return {'highs': [], 'lows': []}
    
    # Вспомогательные методы
    
    def _check_higher_highs(self, highs: List[SwingPoint]) -> bool:
        """Проверка Higher Highs"""
        if len(highs) < 2:
            return False
        
        for i in range(1, len(highs)):
            if highs[i].price <= highs[i-1].price:
                return False
        return True
    
    def _check_higher_lows(self, lows: List[SwingPoint]) -> bool:
        """Проверка Higher Lows"""
        if len(lows) < 2:
            return False
        
        for i in range(1, len(lows)):
            if lows[i].price <= lows[i-1].price:
                return False
        return True
    
    def _check_lower_lows(self, lows: List[SwingPoint]) -> bool:
        """Проверка Lower Lows"""
        if len(lows) < 2:
            return False
        
        for i in range(1, len(lows)):
            if lows[i].price >= lows[i-1].price:
                return False
        return True
    
    def _check_lower_highs(self, highs: List[SwingPoint]) -> bool:
        """Проверка Lower Highs"""
        if len(highs) < 2:
            return False
        
        for i in range(1, len(highs)):
            if highs[i].price >= highs[i-1].price:
                return False
        return True
    
    def _is_ranging(self, highs: List[SwingPoint], lows: List[SwingPoint]) -> bool:
        """Проверка боковых движений"""
        if not highs or not lows:
            return False
        
        # Проверяем, находятся ли свинги в узком диапазоне
        high_prices = [h.price for h in highs]
        low_prices = [l.price for l in lows]
        
        high_range = max(high_prices) - min(high_prices)
        low_range = max(low_prices) - min(low_prices)
        avg_price = (max(high_prices) + min(low_prices)) / 2
        
        # Если диапазон свингов меньше 2% от средней цены, считаем боковиком
        range_threshold = avg_price * 0.02
        
        return high_range < range_threshold and low_range < range_threshold
    
    def _calculate_swing_strength(
        self, 
        data: pd.DataFrame, 
        index: int, 
        is_high: bool, 
        lookback: int
    ) -> float:
        """Простой расчет силы свинга"""
        try:
            # Базовая сила на основе размера движения
            if is_high:
                prev_low = data.iloc[max(0, index-lookback*2):index]['low'].min()
                current_high = data.iloc[index]['high']
                move_size = (current_high - prev_low) / prev_low if prev_low > 0 else 0
            else:
                prev_high = data.iloc[max(0, index-lookback*2):index]['high'].max()
                current_low = data.iloc[index]['low']
                move_size = (prev_high - current_low) / prev_high if prev_high > 0 else 0
            
            strength = min(abs(move_size) * 10, 1.0)
            
            # Добавляем объемный фактор если есть
            if 'volume' in data.columns:
                current_volume = data.iloc[index]['volume']
                avg_volume = data.iloc[max(0, index-20):index]['volume'].mean()
                if avg_volume > 0:
                    volume_factor = min(current_volume / avg_volume, 2.0)
                    strength = min(strength * volume_factor * 0.5 + strength * 0.5, 1.0)
            
            return max(strength, 0.1)  # Минимальная сила
            
        except Exception as e:
            logger.error(f"Ошибка расчета силы свинга: {e}")
            return 0.5
    
    def _filter_close_swings(self, swings: List[SwingPoint]) -> List[SwingPoint]:
        """Фильтрация слишком близких свингов"""
        if len(swings) <= 1:
            return swings
        
        filtered_swings = []
        min_distance_percent = 0.005  # Минимум 0.5% между свингами
        
        for swing in swings:
            is_too_close = False
            
            for existing_swing in filtered_swings:
                if existing_swing.price > 0:
                    price_distance = abs(swing.price - existing_swing.price) / existing_swing.price
                    if price_distance < min_distance_percent:
                        # Оставляем свинг с большей силой
                        if swing.strength > existing_swing.strength:
                            filtered_swings.remove(existing_swing)
                        else:
                            is_too_close = True
                        break
            
            if not is_too_close:
                filtered_swings.append(swing)
        
        # Сортируем по времени
        filtered_swings.sort(key=lambda x: x.timestamp)
        
        return filtered_swings
    
    def _get_last_significant_swing(
        self, 
        swings: List[SwingPoint], 
        is_high: bool
    ) -> Optional[SwingPoint]:
        """Получение последнего значимого свинга"""
        if not swings:
            return None
        
        # Сортируем по времени и берем последние
        sorted_swings = sorted(swings, key=lambda x: x.timestamp, reverse=True)
        
        # Ищем последний свинг с высокой силой
        for swing in sorted_swings[:3]:  # Проверяем последние 3
            if swing.strength >= 0.6:  # Средняя сила
                return swing
        
        # Если нет сильных свингов, возвращаем последний
        return sorted_swings[0]