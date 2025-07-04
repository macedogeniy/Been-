"""
Детектор ликвидности для стратегии "Охота за ликвидностью"
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

from core.interfaces import ILiquidityDetector
from core.data_types import (
    LiquidityPool, LiquidityType, SwingPoint, TimeFrame
)
from core.exceptions import LiquidityDetectionError
from config import get_config


class LiquidityDetector(ILiquidityDetector):
    """Детектор пулов ликвидности"""
    
    def __init__(self):
        self.config = get_config()
        self._liquidity_cache: Dict[str, List[LiquidityPool]] = {}
        
    def detect_liquidity_pools(
        self, 
        data: pd.DataFrame, 
        swing_points: List[SwingPoint]
    ) -> List[LiquidityPool]:
        """Детекция пулов ликвидности на основе свинг-точек"""
        try:
            liquidity_pools = []
            
            for swing in swing_points:
                # Определяем тип ликвидности
                liquidity_type = LiquidityType.BSL if swing.is_high else LiquidityType.SSL
                
                # Рассчитываем силу ликвидности
                volume_data = data['volume'] if 'volume' in data.columns else pd.Series([0] * len(data))
                strength = self.calculate_liquidity_strength(swing, volume_data)
                
                # Оцениваем объем ликвидности
                estimated_volume = self._estimate_liquidity_volume(swing, data)
                
                # Создаем пул ликвидности
                pool = LiquidityPool(
                    price=swing.price,
                    liquidity_type=liquidity_type,
                    strength=strength,
                    volume=estimated_volume,
                    created_at=swing.timestamp,
                    swept=False
                )
                
                # Проверяем минимальные требования
                if self._validate_liquidity_pool(pool, data):
                    liquidity_pools.append(pool)
            
            # Добавляем уровни поддержки/сопротивления как потенциальную ликвидность
            sr_pools = self._detect_support_resistance_liquidity(data)
            liquidity_pools.extend(sr_pools)
            
            # Фильтруем и ранжируем пулы
            filtered_pools = self._filter_and_rank_pools(liquidity_pools, data)
            
            logger.debug(f"Обнаружено {len(filtered_pools)} пулов ликвидности")
            return filtered_pools
            
        except Exception as e:
            logger.error(f"Ошибка детекции ликвидности: {e}")
            raise LiquidityDetectionError(f"Не удалось детектировать ликвидность: {e}")
    
    def check_liquidity_sweep(
        self, 
        current_price: float, 
        liquidity_pools: List[LiquidityPool]
    ) -> List[LiquidityPool]:
        """Проверка снятия ликвидности"""
        try:
            swept_pools = []
            
            for pool in liquidity_pools:
                if pool.swept:
                    continue
                
                # Проверяем, была ли снята ликвидность
                is_swept = False
                
                if pool.liquidity_type == LiquidityType.BSL:
                    # Buy Side Liquidity снимается при движении вверх
                    if current_price > pool.price:
                        is_swept = True
                elif pool.liquidity_type == LiquidityType.SSL:
                    # Sell Side Liquidity снимается при движении вниз
                    if current_price < pool.price:
                        is_swept = True
                
                if is_swept:
                    pool.swept = True
                    pool.swept_at = datetime.now()
                    swept_pools.append(pool)
                    
                    logger.info(
                        f"Снята ликвидность {pool.liquidity_type.value} "
                        f"на уровне {pool.price:.2f}, сила: {pool.strength:.2f}"
                    )
            
            return swept_pools
            
        except Exception as e:
            logger.error(f"Ошибка проверки снятия ликвидности: {e}")
            return []
    
    def calculate_liquidity_strength(
        self, 
        swing_point: SwingPoint, 
        volume_data: pd.Series
    ) -> float:
        """Расчет силы ликвидности"""
        try:
            strength = 0.0
            
            # 1. Базовая сила свинга (30%)
            strength += swing_point.strength * 0.3
            
            # 2. Возраст свинга (20%)
            # Более старые свинги считаются более значимыми
            age_hours = (datetime.now() - swing_point.timestamp).total_seconds() / 3600
            age_factor = min(age_hours / 24, 1.0)  # Максимум за сутки
            strength += age_factor * 0.2
            
            # 3. Объемный фактор (25%)
            if len(volume_data) > 0:
                # Ищем индекс ближайшей свечи к времени свинга
                swing_idx = self._find_nearest_candle_index(swing_point.timestamp, volume_data)
                if swing_idx is not None and swing_idx < len(volume_data):
                    swing_volume = volume_data.iloc[swing_idx]
                    avg_volume = volume_data.rolling(20).mean().iloc[swing_idx]
                    if avg_volume > 0:
                        volume_ratio = swing_volume / avg_volume
                        volume_strength = min(volume_ratio / 2, 1.0)  # Нормализуем
                        strength += volume_strength * 0.25
            
            # 4. Количество касаний уровня (15%)
            # Больше касаний = больше ожидающих ордеров
            touch_factor = min(self._count_level_touches(swing_point.price, volume_data) / 3, 1.0)
            strength += touch_factor * 0.15
            
            # 5. Психологический уровень (10%)
            if self._is_psychological_level(swing_point.price):
                strength += 0.1
            
            return min(strength, 1.0)
            
        except Exception as e:
            logger.error(f"Ошибка расчета силы ликвидности: {e}")
            return swing_point.strength  # Возвращаем базовую силу при ошибке
    
    def get_active_liquidity_pools(
        self, 
        current_price: float, 
        max_distance_percent: Optional[float] = None
    ) -> List[LiquidityPool]:
        """Получение активных пулов ликвидности"""
        max_distance = max_distance_percent or self.config.strategy.max_liquidity_distance
        
        active_pools = []
        
        for cache_key, pools in self._liquidity_cache.items():
            for pool in pools:
                if pool.swept:
                    continue
                
                # Проверяем расстояние до текущей цены
                distance = abs(pool.price - current_price) / current_price
                if distance <= max_distance:
                    # Проверяем возраст пула
                    if pool.age <= self.config.strategy.min_liquidity_age * 24:  # Конвертируем в часы
                        active_pools.append(pool)
        
        # Сортируем по силе и близости к цене
        active_pools.sort(key=lambda p: (p.strength, -abs(p.price - current_price)), reverse=True)
        
        return active_pools
    
    def _estimate_liquidity_volume(self, swing: SwingPoint, data: pd.DataFrame) -> float:
        """Оценка объема ликвидности в пуле"""
        try:
            base_volume = 1000.0  # Базовый объем
            
            # Умножаем на силу свинга
            volume = base_volume * swing.strength
            
            # Корректируем на основе объемов торгов
            if 'volume' in data.columns and len(data) > 0:
                avg_volume = data['volume'].mean()
                volume *= min(avg_volume / 1000, 10)  # Ограничиваем множитель
            
            # Добавляем случайность для реализма
            noise_factor = np.random.uniform(0.8, 1.2)
            volume *= noise_factor
            
            return max(volume, 100)  # Минимальный объем
            
        except Exception as e:
            logger.error(f"Ошибка оценки объема ликвидности: {e}")
            return 1000.0
    
    def _validate_liquidity_pool(self, pool: LiquidityPool, data: pd.DataFrame) -> bool:
        """Валидация пула ликвидности"""
        try:
            # Проверка минимальной силы
            if pool.strength < self.config.strategy.liquidity_sensitivity:
                return False
            
            # Проверка минимального возраста
            min_age_hours = self.config.strategy.min_liquidity_age
            if pool.age < min_age_hours:
                return False
            
            # Проверка разумности цены
            if len(data) > 0:
                recent_high = data['high'].max()
                recent_low = data['low'].min()
                
                # Цена должна быть в разумных пределах от недавних экстремумов
                if pool.price > recent_high * 1.1 or pool.price < recent_low * 0.9:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка валидации пула ликвидности: {e}")
            return False
    
    def _detect_support_resistance_liquidity(self, data: pd.DataFrame) -> List[LiquidityPool]:
        """Детекция ликвидности на уровнях поддержки/сопротивления"""
        try:
            sr_pools = []
            
            if len(data) < 50:
                return sr_pools
            
            # Ищем значимые уровни методом фрактальных точек
            resistance_levels = self._find_resistance_levels(data)
            support_levels = self._find_support_levels(data)
            
            current_time = datetime.now()
            
            # Создаем пулы ликвидности для уровней сопротивления
            for level_price, strength in resistance_levels:
                pool = LiquidityPool(
                    price=level_price,
                    liquidity_type=LiquidityType.BSL,
                    strength=strength,
                    volume=self._estimate_sr_volume(level_price, data),
                    created_at=current_time,
                    swept=False
                )
                sr_pools.append(pool)
            
            # Создаем пулы ликвидности для уровней поддержки
            for level_price, strength in support_levels:
                pool = LiquidityPool(
                    price=level_price,
                    liquidity_type=LiquidityType.SSL,
                    strength=strength,
                    volume=self._estimate_sr_volume(level_price, data),
                    created_at=current_time,
                    swept=False
                )
                sr_pools.append(pool)
            
            return sr_pools
            
        except Exception as e:
            logger.error(f"Ошибка детекции S/R ликвидности: {e}")
            return []
    
    def _find_resistance_levels(self, data: pd.DataFrame) -> List[Tuple[float, float]]:
        """Поиск уровней сопротивления"""
        resistance_levels = []
        
        try:
            # Используем локальные максимумы
            window = 10
            highs = data['high']
            
            for i in range(window, len(highs) - window):
                current_high = highs.iloc[i]
                
                # Проверяем, является ли текущий максимум локальным
                is_local_max = True
                for j in range(i - window, i + window + 1):
                    if j != i and highs.iloc[j] >= current_high:
                        is_local_max = False
                        break
                
                if is_local_max:
                    # Считаем количество касаний этого уровня
                    touches = self._count_level_touches(current_high, highs, tolerance=0.002)
                    
                    if touches >= 2:  # Минимум 2 касания для значимости
                        strength = min(touches / 5, 1.0)  # Нормализуем силу
                        resistance_levels.append((current_high, strength))
            
        except Exception as e:
            logger.error(f"Ошибка поиска уровней сопротивления: {e}")
        
        return resistance_levels
    
    def _find_support_levels(self, data: pd.DataFrame) -> List[Tuple[float, float]]:
        """Поиск уровней поддержки"""
        support_levels = []
        
        try:
            # Используем локальные минимумы
            window = 10
            lows = data['low']
            
            for i in range(window, len(lows) - window):
                current_low = lows.iloc[i]
                
                # Проверяем, является ли текущий минимум локальным
                is_local_min = True
                for j in range(i - window, i + window + 1):
                    if j != i and lows.iloc[j] <= current_low:
                        is_local_min = False
                        break
                
                if is_local_min:
                    # Считаем количество касаний этого уровня
                    touches = self._count_level_touches(current_low, lows, tolerance=0.002)
                    
                    if touches >= 2:  # Минимум 2 касания для значимости
                        strength = min(touches / 5, 1.0)  # Нормализуем силу
                        support_levels.append((current_low, strength))
            
        except Exception as e:
            logger.error(f"Ошибка поиска уровней поддержки: {e}")
        
        return support_levels
    
    def _filter_and_rank_pools(
        self, 
        pools: List[LiquidityPool], 
        data: pd.DataFrame
    ) -> List[LiquidityPool]:
        """Фильтрация и ранжирование пулов ликвидности"""
        try:
            if not pools:
                return []
            
            # 1. Удаляем дубликаты (близкие по цене пулы)
            unique_pools = []
            min_distance = 0.001  # 0.1% минимальное расстояние
            
            for pool in pools:
                is_duplicate = False
                for existing_pool in unique_pools:
                    price_distance = abs(pool.price - existing_pool.price) / existing_pool.price
                    if price_distance < min_distance:
                        # Оставляем пул с большей силой
                        if pool.strength > existing_pool.strength:
                            unique_pools.remove(existing_pool)
                        else:
                            is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_pools.append(pool)
            
            # 2. Фильтруем по минимальной силе
            min_strength = self.config.strategy.liquidity_sensitivity
            filtered_pools = [p for p in unique_pools if p.strength >= min_strength]
            
            # 3. Ограничиваем количество пулов
            max_pools = 20
            if len(filtered_pools) > max_pools:
                # Сортируем по силе и берем топ
                filtered_pools.sort(key=lambda p: p.strength, reverse=True)
                filtered_pools = filtered_pools[:max_pools]
            
            # 4. Финальная сортировка по релевантности
            if len(data) > 0:
                current_price = data['close'].iloc[-1]
                filtered_pools.sort(
                    key=lambda p: (p.strength, -abs(p.price - current_price)), 
                    reverse=True
                )
            
            return filtered_pools
            
        except Exception as e:
            logger.error(f"Ошибка фильтрации пулов: {e}")
            return pools
    
    def _find_nearest_candle_index(self, timestamp: datetime, volume_data: pd.Series) -> Optional[int]:
        """Поиск индекса ближайшей свечи к временной метке"""
        try:
            if hasattr(volume_data, 'index'):
                # Ищем ближайший индекс по времени
                time_diffs = [(abs((idx - timestamp).total_seconds()), i) 
                             for i, idx in enumerate(volume_data.index)]
                if time_diffs:
                    _, nearest_idx = min(time_diffs)
                    return nearest_idx
            return None
        except Exception:
            return None
    
    def _count_level_touches(
        self, 
        level_price: float, 
        price_series: pd.Series, 
        tolerance: float = 0.002
    ) -> int:
        """Подсчет касаний уровня"""
        try:
            touches = 0
            for price in price_series:
                if abs(price - level_price) / level_price <= tolerance:
                    touches += 1
            return touches
        except Exception:
            return 0
    
    def _is_psychological_level(self, price: float) -> bool:
        """Проверка психологического уровня"""
        try:
            # Проверяем круглые числа
            if price % 1000 == 0:  # Тысячи
                return True
            if price % 500 == 0:   # Полутысячи
                return True
            if price % 100 == 0:   # Сотни
                return True
            if price % 50 == 0:    # Полусотни
                return True
            
            return False
        except Exception:
            return False
    
    def _estimate_sr_volume(self, level_price: float, data: pd.DataFrame) -> float:
        """Оценка объема ликвидности для S/R уровня"""
        try:
            base_volume = 500.0
            
            # Увеличиваем объем для психологических уровней
            if self._is_psychological_level(level_price):
                base_volume *= 2
            
            # Корректируем на основе средних объемов
            if 'volume' in data.columns and len(data) > 0:
                avg_volume = data['volume'].mean()
                base_volume *= min(avg_volume / 1000, 5)
            
            return max(base_volume, 100)
            
        except Exception as e:
            logger.error(f"Ошибка оценки объема S/R: {e}")
            return 500.0
    
    def get_liquidity_heat_map(
        self, 
        data: pd.DataFrame, 
        price_range: Tuple[float, float],
        bins: int = 50
    ) -> Dict[float, float]:
        """Создание тепловой карты ликвидности"""
        try:
            min_price, max_price = price_range
            price_step = (max_price - min_price) / bins
            
            heat_map = {}
            
            # Инициализируем карту
            for i in range(bins):
                price_level = min_price + i * price_step
                heat_map[price_level] = 0.0
            
            # Получаем все пулы ликвидности
            swing_highs, swing_lows = [], []  # Здесь должны быть реальные свинги
            all_pools = self.detect_liquidity_pools(data, swing_highs + swing_lows)
            
            # Распределяем ликвидность по уровням
            for pool in all_pools:
                if min_price <= pool.price <= max_price:
                    # Находим ближайший уровень
                    level_idx = int((pool.price - min_price) / price_step)
                    if 0 <= level_idx < bins:
                        price_level = min_price + level_idx * price_step
                        heat_map[price_level] += pool.strength * pool.volume
            
            return heat_map
            
        except Exception as e:
            logger.error(f"Ошибка создания тепловой карты: {e}")
            return {}
    
    def update_liquidity_cache(self, symbol: str, timeframe: str, pools: List[LiquidityPool]) -> None:
        """Обновление кэша ликвидности"""
        cache_key = f"{symbol}_{timeframe}"
        self._liquidity_cache[cache_key] = pools.copy()
    
    def clear_liquidity_cache(self) -> None:
        """Очистка кэша ликвидности"""
        self._liquidity_cache.clear()
        logger.info("Кэш ликвидности очищен")