"""
Идентификатор зон интереса (POI) для стратегии "Охота за ликвидностью"
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

from core.interfaces import IPOIIdentifier
from core.data_types import (
    POI, POIType, SwingPoint, OHLCV, TimeFrame
)
from core.exceptions import POIIdentificationError
from config import get_config


class POIIdentifier(IPOIIdentifier):
    """Идентификатор зон интереса (Points of Interest)"""
    
    def __init__(self):
        self.config = get_config()
        self._poi_cache: Dict[str, List[POI]] = {}
        
    def identify_order_blocks(self, data: pd.DataFrame) -> List[POI]:
        """Идентификация ордер-блоков"""
        try:
            order_blocks = []
            
            if len(data) < 10:
                return order_blocks
            
            # Ищем импульсные движения
            impulse_moves = self._find_impulse_moves(data)
            
            for move in impulse_moves:
                start_idx, end_idx, direction = move
                
                if direction == "bullish":
                    # Для бычьего импульса ищем последнюю медвежью свечу перед движением
                    ob_candle = self._find_last_bearish_candle(data, start_idx)
                    if ob_candle is not None:
                        ob_idx, candle = ob_candle
                        
                        # Создаем Order Block
                        ob = POI(
                            start_time=candle.name,
                            end_time=candle.name + timedelta(hours=1),  # Продолжительность 1 бар
                            high_price=candle['high'],
                            low_price=candle['low'],
                            poi_type=POIType.ORDER_BLOCK,
                            strength=self._calculate_ob_strength(data, ob_idx, direction),
                            created_by_candle=OHLCV(
                                timestamp=candle.name,
                                open=candle['open'],
                                high=candle['high'],
                                low=candle['low'],
                                close=candle['close'],
                                volume=candle['volume']
                            )
                        )
                        order_blocks.append(ob)
                        
                elif direction == "bearish":
                    # Для медвежьего импульса ищем последнюю бычью свечу перед движением
                    ob_candle = self._find_last_bullish_candle(data, start_idx)
                    if ob_candle is not None:
                        ob_idx, candle = ob_candle
                        
                        ob = POI(
                            start_time=candle.name,
                            end_time=candle.name + timedelta(hours=1),
                            high_price=candle['high'],
                            low_price=candle['low'],
                            poi_type=POIType.ORDER_BLOCK,
                            strength=self._calculate_ob_strength(data, ob_idx, direction),
                            created_by_candle=OHLCV(
                                timestamp=candle.name,
                                open=candle['open'],
                                high=candle['high'],
                                low=candle['low'],
                                close=candle['close'],
                                volume=candle['volume']
                            )
                        )
                        order_blocks.append(ob)
            
            # Фильтруем и ранжируем Order Blocks
            filtered_obs = self._filter_order_blocks(order_blocks, data)
            
            logger.debug(f"Найдено {len(filtered_obs)} Order Blocks")
            return filtered_obs
            
        except Exception as e:
            logger.error(f"Ошибка идентификации Order Blocks: {e}")
            raise POIIdentificationError(f"Не удалось идентифицировать Order Blocks: {e}")
    
    def identify_imbalances(self, data: pd.DataFrame) -> List[POI]:
        """Идентификация дисбалансов (Fair Value Gaps)"""
        try:
            imbalances = []
            
            if len(data) < 3:
                return imbalances
            
            # Проходим по данным и ищем разрывы
            for i in range(1, len(data) - 1):
                prev_candle = data.iloc[i-1]
                curr_candle = data.iloc[i]
                next_candle = data.iloc[i+1]
                
                # Проверяем бычий дисбаланс (gap вверх)
                bullish_gap = (
                    prev_candle['high'] < next_candle['low'] and
                    curr_candle['close'] > curr_candle['open']  # Импульсная свеча
                )
                
                if bullish_gap:
                    gap_size = next_candle['low'] - prev_candle['high']
                    gap_size_percent = gap_size / prev_candle['high']
                    
                    if gap_size_percent >= self.config.strategy.fvg_min_size:
                        imbalance = POI(
                            start_time=prev_candle.name,
                            end_time=next_candle.name,
                            high_price=next_candle['low'],
                            low_price=prev_candle['high'],
                            poi_type=POIType.IMBALANCE,
                            strength=self._calculate_imbalance_strength(gap_size_percent, curr_candle),
                            created_by_candle=OHLCV(
                                timestamp=curr_candle.name,
                                open=curr_candle['open'],
                                high=curr_candle['high'],
                                low=curr_candle['low'],
                                close=curr_candle['close'],
                                volume=curr_candle['volume']
                            )
                        )
                        imbalances.append(imbalance)
                
                # Проверяем медвежий дисбаланс (gap вниз)
                bearish_gap = (
                    prev_candle['low'] > next_candle['high'] and
                    curr_candle['close'] < curr_candle['open']  # Импульсная свеча
                )
                
                if bearish_gap:
                    gap_size = prev_candle['low'] - next_candle['high']
                    gap_size_percent = gap_size / prev_candle['low']
                    
                    if gap_size_percent >= self.config.strategy.fvg_min_size:
                        imbalance = POI(
                            start_time=prev_candle.name,
                            end_time=next_candle.name,
                            high_price=prev_candle['low'],
                            low_price=next_candle['high'],
                            poi_type=POIType.IMBALANCE,
                            strength=self._calculate_imbalance_strength(gap_size_percent, curr_candle),
                            created_by_candle=OHLCV(
                                timestamp=curr_candle.name,
                                open=curr_candle['open'],
                                high=curr_candle['high'],
                                low=curr_candle['low'],
                                close=curr_candle['close'],
                                volume=curr_candle['volume']
                            )
                        )
                        imbalances.append(imbalance)
            
            # Фильтруем перекрывающиеся дисбалансы
            filtered_imbalances = self._filter_imbalances(imbalances)
            
            logger.debug(f"Найдено {len(filtered_imbalances)} дисбалансов (FVG)")
            return filtered_imbalances
            
        except Exception as e:
            logger.error(f"Ошибка идентификации дисбалансов: {e}")
            raise POIIdentificationError(f"Не удалось идентифицировать дисбалансы: {e}")
    
    def identify_support_resistance(self, data: pd.DataFrame) -> List[POI]:
        """Идентификация уровней поддержки/сопротивления"""
        try:
            sr_levels = []
            
            if len(data) < 20:
                return sr_levels
            
            # Находим значимые уровни методом кластеризации цен
            price_clusters = self._find_price_clusters(data)
            
            for cluster in price_clusters:
                price_level, touches, strength = cluster
                
                # Определяем тип уровня на основе последнего взаимодействия
                recent_interactions = self._get_recent_price_interactions(data, price_level)
                
                if recent_interactions:
                    last_interaction = recent_interactions[-1]
                    
                    if last_interaction['type'] == 'bounce_up':
                        poi_type = POIType.SUPPORT
                    elif last_interaction['type'] == 'bounce_down':
                        poi_type = POIType.RESISTANCE
                    else:
                        # Определяем по положению относительно текущей цены
                        current_price = data['close'].iloc[-1]
                        poi_type = POIType.SUPPORT if price_level < current_price else POIType.RESISTANCE
                    
                    # Создаем зону вокруг уровня (±0.1% от цены)
                    zone_size = price_level * 0.001
                    
                    sr_poi = POI(
                        start_time=data.index[0],
                        end_time=data.index[-1],
                        high_price=price_level + zone_size,
                        low_price=price_level - zone_size,
                        poi_type=poi_type,
                        strength=strength,
                        test_count=touches
                    )
                    sr_levels.append(sr_poi)
            
            logger.debug(f"Найдено {len(sr_levels)} уровней S/R")
            return sr_levels
            
        except Exception as e:
            logger.error(f"Ошибка идентификации S/R: {e}")
            raise POIIdentificationError(f"Не удалось идентифицировать S/R: {e}")
    
    def calculate_fibonacci_levels(
        self, 
        swing_high: SwingPoint, 
        swing_low: SwingPoint
    ) -> Dict[float, float]:
        """Расчет уровней Фибоначчи"""
        try:
            # Стандартные уровни Фибоначчи
            fib_ratios = {
                0.0: "0%",
                0.236: "23.6%",
                0.382: "38.2%",
                0.5: "50%",
                0.618: "61.8%",
                0.786: "78.6%",
                1.0: "100%",
                1.272: "127.2%",
                1.618: "161.8%"
            }
            
            # Определяем диапазон
            high_price = swing_high.price
            low_price = swing_low.price
            price_range = high_price - low_price
            
            fib_levels = {}
            
            # Для восходящего движения (коррекция)
            if swing_high.timestamp > swing_low.timestamp:
                for ratio, label in fib_ratios.items():
                    level_price = high_price - (price_range * ratio)
                    fib_levels[ratio] = level_price
            else:
                # Для нисходящего движения (расширение)
                for ratio, label in fib_ratios.items():
                    level_price = low_price + (price_range * ratio)
                    fib_levels[ratio] = level_price
            
            logger.debug(f"Рассчитано {len(fib_levels)} уровней Фибоначчи")
            return fib_levels
            
        except Exception as e:
            logger.error(f"Ошибка расчета уровней Фибоначчи: {e}")
            return {}
    
    def validate_poi_relevance(self, poi: POI, current_time: datetime) -> bool:
        """Валидация актуальности зоны интереса"""
        try:
            # Проверяем возраст POI
            age_hours = (current_time - poi.start_time).total_seconds() / 3600
            
            if poi.poi_type == POIType.ORDER_BLOCK:
                max_age = self.config.strategy.ob_validity_period
                return age_hours <= max_age
            
            elif poi.poi_type == POIType.IMBALANCE:
                max_age = self.config.strategy.fvg_validity_period
                return age_hours <= max_age
            
            elif poi.poi_type in [POIType.SUPPORT, POIType.RESISTANCE]:
                # S/R уровни актуальны дольше, но теряют силу со временем
                max_age = 720  # 30 дней
                if age_hours > max_age:
                    return False
                
                # Проверяем, был ли уровень недавно протестирован
                return poi.test_count > 0
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка валидации POI: {e}")
            return False
    
    def _find_impulse_moves(self, data: pd.DataFrame, min_move_percent: float = 0.02) -> List[Tuple[int, int, str]]:
        """Поиск импульсных движений"""
        impulse_moves = []
        
        try:
            # Используем простой алгоритм поиска больших свечей
            for i in range(len(data)):
                candle = data.iloc[i]
                body_size = abs(candle['close'] - candle['open'])
                candle_range = candle['high'] - candle['low']
                
                # Проверяем размер тела свечи
                body_ratio = body_size / candle_range if candle_range > 0 else 0
                
                # Проверяем размер движения
                move_percent = body_size / candle['open'] if candle['open'] > 0 else 0
                
                if (body_ratio >= self.config.strategy.ob_min_body_ratio and 
                    move_percent >= min_move_percent):
                    
                    direction = "bullish" if candle['close'] > candle['open'] else "bearish"
                    impulse_moves.append((i, i, direction))
            
            return impulse_moves
            
        except Exception as e:
            logger.error(f"Ошибка поиска импульсов: {e}")
            return []
    
    def _find_last_bearish_candle(self, data: pd.DataFrame, before_idx: int) -> Optional[Tuple[int, pd.Series]]:
        """Поиск последней медвежьей свечи перед индексом"""
        for i in range(before_idx - 1, -1, -1):
            candle = data.iloc[i]
            if candle['close'] < candle['open']:
                return i, candle
        return None
    
    def _find_last_bullish_candle(self, data: pd.DataFrame, before_idx: int) -> Optional[Tuple[int, pd.Series]]:
        """Поиск последней бычьей свечи перед индексом"""
        for i in range(before_idx - 1, -1, -1):
            candle = data.iloc[i]
            if candle['close'] > candle['open']:
                return i, candle
        return None
    
    def _calculate_ob_strength(self, data: pd.DataFrame, ob_idx: int, direction: str) -> float:
        """Расчет силы Order Block"""
        try:
            strength = 0.0
            candle = data.iloc[ob_idx]
            
            # 1. Размер тела свечи (40%)
            body_size = abs(candle['close'] - candle['open'])
            candle_range = candle['high'] - candle['low']
            body_ratio = body_size / candle_range if candle_range > 0 else 0
            strength += body_ratio * 0.4
            
            # 2. Объем (30%)
            if 'volume' in data.columns and ob_idx >= 20:
                avg_volume = data.iloc[ob_idx-20:ob_idx]['volume'].mean()
                volume_ratio = candle['volume'] / avg_volume if avg_volume > 0 else 1
                volume_strength = min(volume_ratio / 2, 1.0)
                strength += volume_strength * 0.3
            
            # 3. Позиция в диапазоне (30%)
            if len(data) > ob_idx + 10:
                future_data = data.iloc[ob_idx:ob_idx+10]
                if direction == "bullish":
                    # Для бычьего OB проверяем, держится ли цена выше
                    price_respect = (future_data['low'] >= candle['low']).mean()
                else:
                    # Для медвежьего OB проверяем, держится ли цена ниже
                    price_respect = (future_data['high'] <= candle['high']).mean()
                strength += price_respect * 0.3
            
            return min(strength, 1.0)
            
        except Exception as e:
            logger.error(f"Ошибка расчета силы OB: {e}")
            return 0.5
    
    def _calculate_imbalance_strength(self, gap_size_percent: float, impulse_candle: pd.Series) -> float:
        """Расчет силы дисбаланса"""
        try:
            strength = 0.0
            
            # 1. Размер разрыва (50%)
            gap_strength = min(gap_size_percent * 100, 1.0)  # Нормализуем к 1%
            strength += gap_strength * 0.5
            
            # 2. Размер импульсной свечи (30%)
            body_size = abs(impulse_candle['close'] - impulse_candle['open'])
            candle_range = impulse_candle['high'] - impulse_candle['low']
            body_ratio = body_size / candle_range if candle_range > 0 else 0
            strength += body_ratio * 0.3
            
            # 3. Базовая сила (20%)
            strength += 0.2
            
            return min(strength, 1.0)
            
        except Exception as e:
            logger.error(f"Ошибка расчета силы дисбаланса: {e}")
            return 0.5
    
    def _filter_order_blocks(self, order_blocks: List[POI], data: pd.DataFrame) -> List[POI]:
        """Фильтрация Order Blocks"""
        if not order_blocks:
            return []
        
        # Сортируем по силе
        sorted_obs = sorted(order_blocks, key=lambda x: x.strength, reverse=True)
        
        # Убираем перекрывающиеся
        filtered_obs = []
        for ob in sorted_obs:
            is_overlapping = False
            for existing_ob in filtered_obs:
                if self._check_poi_overlap(ob, existing_ob):
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                filtered_obs.append(ob)
        
        return filtered_obs[:10]  # Максимум 10 Order Blocks
    
    def _filter_imbalances(self, imbalances: List[POI]) -> List[POI]:
        """Фильтрация дисбалансов"""
        if not imbalances:
            return []
        
        # Убираем перекрывающиеся дисбалансы
        filtered = []
        for imb in sorted(imbalances, key=lambda x: x.strength, reverse=True):
            is_overlapping = False
            for existing in filtered:
                if self._check_poi_overlap(imb, existing):
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                filtered.append(imb)
        
        return filtered
    
    def _check_poi_overlap(self, poi1: POI, poi2: POI) -> bool:
        """Проверка перекрытия зон интереса"""
        # Проверяем перекрытие по цене
        price_overlap = not (poi1.high_price < poi2.low_price or poi1.low_price > poi2.high_price)
        
        # Проверяем перекрытие по времени
        time_overlap = not (poi1.end_time < poi2.start_time or poi1.start_time > poi2.end_time)
        
        return price_overlap and time_overlap
    
    def _find_price_clusters(self, data: pd.DataFrame, tolerance: float = 0.005) -> List[Tuple[float, int, float]]:
        """Поиск кластеров цен для S/R уровней"""
        try:
            # Собираем все значимые цены (хаи и лоу)
            prices = []
            prices.extend(data['high'].tolist())
            prices.extend(data['low'].tolist())
            
            # Кластеризуем цены
            clusters = []
            sorted_prices = sorted(prices)
            
            i = 0
            while i < len(sorted_prices):
                cluster_prices = [sorted_prices[i]]
                j = i + 1
                
                # Собираем цены в кластер
                while j < len(sorted_prices):
                    if (sorted_prices[j] - sorted_prices[i]) / sorted_prices[i] <= tolerance:
                        cluster_prices.append(sorted_prices[j])
                        j += 1
                    else:
                        break
                
                if len(cluster_prices) >= 3:  # Минимум 3 касания
                    cluster_price = np.mean(cluster_prices)
                    touches = len(cluster_prices)
                    strength = min(touches / 5, 1.0)  # Нормализуем силу
                    clusters.append((cluster_price, touches, strength))
                
                i = j
            
            return clusters
            
        except Exception as e:
            logger.error(f"Ошибка поиска кластеров цен: {e}")
            return []
    
    def _get_recent_price_interactions(self, data: pd.DataFrame, price_level: float, tolerance: float = 0.002) -> List[Dict]:
        """Получение недавних взаимодействий с уровнем цены"""
        interactions = []
        
        try:
            for i in range(1, len(data)):
                prev_candle = data.iloc[i-1]
                curr_candle = data.iloc[i]
                
                # Проверяем касание уровня
                level_touched = (
                    curr_candle['low'] <= price_level * (1 + tolerance) and
                    curr_candle['high'] >= price_level * (1 - tolerance)
                )
                
                if level_touched:
                    # Определяем тип взаимодействия
                    if curr_candle['close'] > price_level and prev_candle['close'] < price_level:
                        interaction_type = 'bounce_up'
                    elif curr_candle['close'] < price_level and prev_candle['close'] > price_level:
                        interaction_type = 'bounce_down'
                    elif curr_candle['low'] < price_level < curr_candle['high']:
                        interaction_type = 'touch'
                    else:
                        continue
                    
                    interactions.append({
                        'timestamp': curr_candle.name,
                        'type': interaction_type,
                        'price': price_level
                    })
            
            return interactions[-10:]  # Последние 10 взаимодействий
            
        except Exception as e:
            logger.error(f"Ошибка получения взаимодействий с уровнем: {e}")
            return []
    
    def get_all_active_pois(self, data: pd.DataFrame, current_time: datetime) -> Dict[str, List[POI]]:
        """Получение всех активных зон интереса"""
        try:
            all_pois = {
                'order_blocks': [],
                'imbalances': [],
                'support_resistance': []
            }
            
            # Получаем все типы POI
            all_pois['order_blocks'] = self.identify_order_blocks(data)
            all_pois['imbalances'] = self.identify_imbalances(data)
            all_pois['support_resistance'] = self.identify_support_resistance(data)
            
            # Фильтруем по актуальности
            for poi_type in all_pois:
                all_pois[poi_type] = [
                    poi for poi in all_pois[poi_type] 
                    if self.validate_poi_relevance(poi, current_time)
                ]
            
            total_pois = sum(len(pois) for pois in all_pois.values())
            logger.info(f"Найдено {total_pois} активных зон интереса")
            
            return all_pois
            
        except Exception as e:
            logger.error(f"Ошибка получения активных POI: {e}")
            return {'order_blocks': [], 'imbalances': [], 'support_resistance': []}