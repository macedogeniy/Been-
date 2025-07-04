"""
Анализатор структуры рынка для стратегии "Охота за ликвидностью"
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
    """Анализатор структуры рынка"""
    
    def __init__(self):
        self.config = get_config()
        self._swing_cache: Dict[str, List[SwingPoint]] = {}
        
    def analyze_structure(self, data: pd.DataFrame) -> MarketStructure:
        """Анализ структуры рынка"""
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
            
            # Определяем структуру
            if bullish_hh and bullish_hl:
                structure = MarketStructure.BULLISH
            elif bearish_ll and bearish_lh:
                structure = MarketStructure.BEARISH
            else:
                # Проверяем боковое движение
                if self._is_ranging(data, swing_highs, swing_lows):
                    structure = MarketStructure.RANGING
                else:
                    structure = MarketStructure.UNDEFINED
            
            logger.debug(f"Анализ структуры завершен: {structure.value}")
            return structure
            
        except Exception as e:
            logger.error(f"Ошибка анализа структуры рынка: {e}")
            raise StructureAnalysisError(f"Не удалось проанализировать структуру: {e}")
    
    def detect_swings(self, data: pd.DataFrame) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """Детекция свинг-точек"""
        try:
            lookback = self.config.trading.swing_detection_period
            
            if len(data) < lookback * 2 + 1:
                return [], []
            
            swing_highs = []
            swing_lows = []
            
            # Используем метод сравнения с соседними барами
            for i in range(lookback, len(data) - lookback):
                current_bar = data.iloc[i]
                timestamp = current_bar.name
                
                # Проверка свинг-хая
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
                
                # Проверка свинг-лоу
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
            swing_highs = self._filter_close_swings(swing_highs, data)
            swing_lows = self._filter_close_swings(swing_lows, data)
            
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
        """Подтверждение слома структуры"""
        try:
            if current_structure == MarketStructure.UNDEFINED:
                return False
            
            # Получаем последние свинги
            swing_highs, swing_lows = self.detect_swings(data)
            
            if not swing_highs or not swing_lows:
                return False
            
            # Для подтверждения нужно минимум bars подряд
            confirmation_bars = self.config.strategy.structure_confirmation_bars
            
            if len(data) < confirmation_bars:
                return False
            
            latest_price = data.iloc[-1]['close']
            latest_high = data.iloc[-confirmation_bars:]['high'].max()
            latest_low = data.iloc[-confirmation_bars:]['low'].min()
            
            if current_structure == MarketStructure.BULLISH:
                # Для бычьего тренда ищем пробой последнего значимого лоу
                last_significant_low = self._get_last_significant_swing(swing_lows, False)
                if last_significant_low and latest_low < last_significant_low.price:
                    logger.info(f"Подтвержден слом бычьей структуры на уровне {last_significant_low.price}")
                    return True
                    
            elif current_structure == MarketStructure.BEARISH:
                # Для медвежьего тренда ищем пробой последнего значимого хая
                last_significant_high = self._get_last_significant_swing(swing_highs, True)
                if last_significant_high and latest_high > last_significant_high.price:
                    logger.info(f"Подтвержден слом медвежьей структуры на уровне {last_significant_high.price}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка подтверждения слома структуры: {e}")
            return False
    
    def calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Расчет силы тренда"""
        try:
            if len(data) < 20:
                return 0.0
            
            # Используем несколько индикаторов для определения силы тренда
            
            # 1. Наклон EMA
            ema_period = 20
            ema = data['close'].ewm(span=ema_period).mean()
            ema_slope = (ema.iloc[-1] - ema.iloc[-5]) / ema.iloc[-5] if len(ema) >= 5 else 0
            ema_strength = min(abs(ema_slope) * 1000, 1.0)  # Нормализуем
            
            # 2. ADX-подобный расчет
            adx_strength = self._calculate_adx_like(data)
            
            # 3. Консистентность движения
            price_changes = data['close'].pct_change().dropna()
            if len(price_changes) > 0:
                consistency = abs(price_changes.mean()) / (price_changes.std() + 1e-8)
                consistency_strength = min(consistency, 1.0)
            else:
                consistency_strength = 0.0
            
            # 4. Объемный анализ
            volume_strength = self._calculate_volume_trend_strength(data)
            
            # Комбинируем все факторы
            total_strength = (
                ema_strength * 0.3 +
                adx_strength * 0.3 +
                consistency_strength * 0.2 +
                volume_strength * 0.2
            )
            
            return min(max(total_strength, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Ошибка расчета силы тренда: {e}")
            return 0.0
    
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
    
    def _is_ranging(
        self, 
        data: pd.DataFrame, 
        highs: List[SwingPoint], 
        lows: List[SwingPoint]
    ) -> bool:
        """Проверка боковых движений"""
        if not highs or not lows:
            return False
        
        # Берем последние несколько свингов
        recent_highs = highs[-3:] if len(highs) >= 3 else highs
        recent_lows = lows[-3:] if len(lows) >= 3 else lows
        
        # Проверяем, находятся ли свинги в узком диапазоне
        high_prices = [h.price for h in recent_highs]
        low_prices = [l.price for l in recent_lows]
        
        high_range = max(high_prices) - min(high_prices)
        low_range = max(low_prices) - min(low_prices)
        avg_price = (max(high_prices) + min(low_prices)) / 2
        
        # Если диапазон свингов меньше 3% от средней цены, считаем боковиком
        range_threshold = avg_price * 0.03
        
        return high_range < range_threshold and low_range < range_threshold
    
    def _calculate_swing_strength(
        self, 
        data: pd.DataFrame, 
        index: int, 
        is_high: bool, 
        lookback: int
    ) -> float:
        """Расчет силы свинга"""
        try:
            # Факторы силы свинга:
            # 1. Размер движения до свинга
            # 2. Объем на свинге
            # 3. Время формирования
            
            strength = 0.0
            
            # 1. Размер движения
            if is_high:
                prev_low = data.iloc[max(0, index-lookback*2):index]['low'].min()
                current_high = data.iloc[index]['high']
                move_size = (current_high - prev_low) / prev_low if prev_low > 0 else 0
            else:
                prev_high = data.iloc[max(0, index-lookback*2):index]['high'].max()
                current_low = data.iloc[index]['low']
                move_size = (prev_high - current_low) / prev_high if prev_high > 0 else 0
            
            strength += min(abs(move_size) * 10, 0.5)  # Максимум 0.5 за размер движения
            
            # 2. Объемный фактор
            if 'volume' in data.columns:
                current_volume = data.iloc[index]['volume']
                avg_volume = data.iloc[max(0, index-20):index]['volume'].mean()
                volume_factor = current_volume / avg_volume if avg_volume > 0 else 1
                strength += min(volume_factor * 0.2, 0.3)  # Максимум 0.3 за объем
            
            # 3. Временной фактор (чем дольше формировался, тем сильнее)
            time_factor = min(lookback / 10, 0.2)  # Максимум 0.2 за время
            strength += time_factor
            
            return min(strength, 1.0)
            
        except Exception as e:
            logger.error(f"Ошибка расчета силы свинга: {e}")
            return 0.5  # Возвращаем среднее значение при ошибке
    
    def _filter_close_swings(
        self, 
        swings: List[SwingPoint], 
        data: pd.DataFrame
    ) -> List[SwingPoint]:
        """Фильтрация слишком близких свингов"""
        if len(swings) <= 1:
            return swings
        
        filtered_swings = []
        min_distance_percent = 0.005  # Минимум 0.5% между свингами
        
        for swing in swings:
            is_too_close = False
            
            for existing_swing in filtered_swings:
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
            if swing.strength >= 0.7:  # Высокая сила
                return swing
        
        # Если нет сильных свингов, возвращаем последний
        return sorted_swings[0]
    
    def _calculate_adx_like(self, data: pd.DataFrame, period: int = 14) -> float:
        """ADX-подобный расчет силы тренда"""
        try:
            if len(data) < period + 1:
                return 0.0
            
            # Расчет True Range
            high_low = data['high'] - data['low']
            high_close_prev = abs(data['high'] - data['close'].shift(1))
            low_close_prev = abs(data['low'] - data['close'].shift(1))
            
            true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
            
            # Расчет направленного движения
            plus_dm = ((data['high'] - data['high'].shift(1)) * 
                      (data['high'] - data['high'].shift(1) > data['low'].shift(1) - data['low'])).clip(lower=0)
            minus_dm = ((data['low'].shift(1) - data['low']) * 
                       (data['low'].shift(1) - data['low'] > data['high'] - data['high'].shift(1))).clip(lower=0)
            
            # Сглаживание
            atr = true_range.rolling(period).mean()
            plus_di = (plus_dm.rolling(period).mean() / atr) * 100
            minus_di = (minus_dm.rolling(period).mean() / atr) * 100
            
            # ADX
            dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
            adx = dx.rolling(period).mean()
            
            latest_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0
            return min(latest_adx / 100, 1.0)  # Нормализуем к 0-1
            
        except Exception as e:
            logger.error(f"Ошибка расчета ADX: {e}")
            return 0.0
    
    def _calculate_volume_trend_strength(self, data: pd.DataFrame) -> float:
        """Расчет силы тренда на основе объема"""
        try:
            if 'volume' not in data.columns or len(data) < 20:
                return 0.5  # Нейтральное значение при отсутствии объемов
            
            # Сравниваем объемы на восходящих и нисходящих барах
            up_bars = data['close'] > data['open']
            down_bars = data['close'] < data['open']
            
            if len(data[up_bars]) == 0 or len(data[down_bars]) == 0:
                return 0.5
            
            avg_volume_up = data[up_bars]['volume'].mean()
            avg_volume_down = data[down_bars]['volume'].mean()
            
            # Отношение объемов
            if avg_volume_up + avg_volume_down > 0:
                volume_ratio = avg_volume_up / (avg_volume_up + avg_volume_down)
                # Преобразуем в силу тренда (отклонение от 0.5)
                return abs(volume_ratio - 0.5) * 2
            
            return 0.5
            
        except Exception as e:
            logger.error(f"Ошибка расчета объемной силы тренда: {e}")
            return 0.5
    
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
    
    def find_structure_breakouts(
        self, 
        data: pd.DataFrame, 
        timeframe: TimeFrame
    ) -> List[Dict]:
        """Поиск пробоев структуры"""
        try:
            breakouts = []
            
            # Анализируем структуру на скользящем окне
            window_size = 50
            min_bars = 20
            
            for i in range(min_bars, len(data) - window_size):
                window_data = data.iloc[i:i+window_size]
                prev_window_data = data.iloc[i-min_bars:i+window_size-min_bars]
                
                current_structure = self.analyze_structure(window_data)
                prev_structure = self.analyze_structure(prev_window_data)
                
                # Проверяем изменение структуры
                if (current_structure != prev_structure and 
                    current_structure != MarketStructure.UNDEFINED and
                    prev_structure != MarketStructure.UNDEFINED):
                    
                    breakout_info = {
                        'timestamp': data.index[i+window_size-1],
                        'from_structure': prev_structure,
                        'to_structure': current_structure,
                        'timeframe': timeframe,
                        'price': data.iloc[i+window_size-1]['close'],
                        'strength': self.calculate_trend_strength(window_data)
                    }
                    breakouts.append(breakout_info)
            
            return breakouts
            
        except Exception as e:
            logger.error(f"Ошибка поиска пробоев структуры: {e}")
            return []