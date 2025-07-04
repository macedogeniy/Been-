"""
Система синхронизации таймфреймов для стратегии "Охота за ликвидностью"
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from loguru import logger

from core.interfaces import ITimeFrameSynchronizer
from core.data_types import (
    TimeFrame, MarketState, MarketStructure, SwingPoint, LiquidityPool, POI, OHLCV, Signal
)
from core.exceptions import SynchronizationError
from config import get_config


class TimeframeSynchronizer(ITimeFrameSynchronizer):
    """Синхронизатор многотаймфреймового анализа"""
    
    def __init__(self):
        self.config = get_config()
        self._timeframe_hierarchy = self._setup_timeframe_hierarchy()
        self._data_cache: Dict[str, Dict[TimeFrame, pd.DataFrame]] = {}
        self._analysis_cache: Dict[str, Dict[TimeFrame, Dict]] = {}
        
    def _setup_timeframe_hierarchy(self) -> Dict[str, List[TimeFrame]]:
        """Настройка иерархии таймфреймов"""
        return {
            'strategic': [TimeFrame.D1, TimeFrame.H4],
            'intermediate': [TimeFrame.H1, TimeFrame.M30],
            'tactical': [TimeFrame.M15, TimeFrame.M5],
            'sniper': [TimeFrame.M1]
        }
    
    def synchronize_timeframes(
        self, 
        data: Dict[TimeFrame, pd.DataFrame], 
        current_time: datetime
    ) -> Dict[TimeFrame, pd.DataFrame]:
        """Синхронизация данных по таймфреймам"""
        try:
            synchronized_data = {}
            
            # Сортируем таймфреймы по иерархии (от больших к меньшим)
            sorted_timeframes = self._sort_timeframes_by_hierarchy(list(data.keys()))
            
            for timeframe in sorted_timeframes:
                if timeframe not in data:
                    continue
                
                df = data[timeframe].copy()
                
                # Обрезаем данные до текущего времени (no look-ahead)
                df = self._trim_data_to_current_time(df, current_time, timeframe)
                
                # Валидируем данные
                df = self._validate_timeframe_data(df, timeframe)
                
                # Синхронизируем с высшими таймфреймами
                if timeframe != TimeFrame.D1:  # D1 - самый высший
                    higher_timeframes = self._get_higher_timeframes(timeframe, sorted_timeframes)
                    df = self._align_with_higher_timeframes(df, higher_timeframes, synchronized_data)
                
                synchronized_data[timeframe] = df
                
            logger.debug(f"Синхронизированы данные для {len(synchronized_data)} таймфреймов")
            return synchronized_data
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации таймфреймов: {e}")
            raise SynchronizationError(f"Не удалось синхронизировать таймфреймы: {e}")
    
    def propagate_context(
        self, 
        analysis_results: Dict[TimeFrame, Dict], 
        target_timeframe: TimeFrame
    ) -> Dict[str, Any]:
        """Передача контекста от высших таймфреймов к целевому"""
        try:
            context = {
                'market_structure': None,
                'trend_direction': None,
                'key_levels': [],
                'liquidity_pools': [],
                'active_pois': [],
                'manipulation_zones': [],
                'bias': 'neutral'
            }
            
            # Получаем высшие таймфреймы
            higher_timeframes = self._get_higher_timeframes_for_context(target_timeframe)
            
            for htf in higher_timeframes:
                if htf not in analysis_results:
                    continue
                
                htf_analysis = analysis_results[htf]
                
                # Передаем структуру рынка
                if 'market_state' in htf_analysis:
                    market_state: MarketState = htf_analysis['market_state']
                    context['market_structure'] = market_state.structure
                    
                    # Определяем направление тренда на основе структуры
                    if market_state.structure == MarketStructure.BULLISH:
                        context['trend_direction'] = 'bullish'
                    elif market_state.structure == MarketStructure.BEARISH:
                        context['trend_direction'] = 'bearish'
                    else:
                        context['trend_direction'] = 'ranging'
                    
                    # Определяем глобальный bias
                    if market_state.trend_strength > 0.6:
                        context['bias'] = context['trend_direction']
                
                # Передаем ключевые уровни
                if 'swing_points' in htf_analysis:
                    swing_points: List[SwingPoint] = htf_analysis['swing_points']
                    for swing in swing_points[-5:]:  # Последние 5 значимых точек
                        context['key_levels'].append({
                            'price': swing.price,
                            'type': swing.swing_type,
                            'timestamp': swing.timestamp,
                            'timeframe': htf,
                            'strength': swing.strength
                        })
                
                # Передаем пулы ликвидности
                if 'liquidity_pools' in htf_analysis:
                    pools: List[LiquidityPool] = htf_analysis['liquidity_pools']
                    for pool in pools:
                        if pool.strength > 0.5:  # Только сильные пулы
                            context['liquidity_pools'].append({
                                'price': pool.price,
                                'type': pool.liquidity_type,
                                'strength': pool.strength,
                                'timeframe': htf,
                                'is_swept': pool.swept
                            })
                
                # Передаем зоны интереса
                if 'active_pois' in htf_analysis:
                    pois: List[POI] = htf_analysis['active_pois']
                    for poi in pois:
                        if poi.strength > 0.6:  # Только сильные зоны
                            context['active_pois'].append({
                                'high_price': poi.high_price,
                                'low_price': poi.low_price,
                                'type': poi.poi_type,
                                'strength': poi.strength,
                                'timeframe': htf
                            })
            
            # Ранжируем элементы контекста по важности
            context['key_levels'] = sorted(
                context['key_levels'], 
                key=lambda x: x['strength'], 
                reverse=True
            )[:10]
            
            context['liquidity_pools'] = sorted(
                context['liquidity_pools'], 
                key=lambda x: x['strength'], 
                reverse=True
            )[:8]
            
            context['active_pois'] = sorted(
                context['active_pois'], 
                key=lambda x: x['strength'], 
                reverse=True
            )[:6]
            
            logger.debug(f"Сформирован контекст для {target_timeframe}: "
                        f"{len(context['key_levels'])} уровней, "
                        f"{len(context['liquidity_pools'])} пулов ликвидности, "
                        f"{len(context['active_pois'])} зон интереса")
            
            return context
            
        except Exception as e:
            logger.error(f"Ошибка передачи контекста: {e}")
            return {
                'market_structure': None,
                'trend_direction': None,
                'key_levels': [],
                'liquidity_pools': [],
                'active_pois': [],
                'manipulation_zones': [],
                'bias': 'neutral'
            }
    
    def validate_temporal_consistency(
        self, 
        signals: Dict[TimeFrame, List[Signal]], 
        current_time: datetime
    ) -> Dict[TimeFrame, List[Signal]]:
        """Валидация временной согласованности сигналов"""
        try:
            validated_signals = {}
            
            # Сортируем таймфреймы от высших к низшим
            sorted_timeframes = self._sort_timeframes_by_hierarchy(list(signals.keys()))
            
            # Проверяем согласованность сигналов между таймфреймами
            for tf in sorted_timeframes:
                tf_signals = signals.get(tf, [])
                validated_tf_signals = []
                
                for signal in tf_signals:
                    # Проверяем временную валидность
                    if signal.timestamp > current_time:
                        logger.warning(f"Сигнал из будущего обнаружен на {tf}: {signal.timestamp}")
                        continue
                    
                    # Проверяем согласованность с высшими таймфреймами
                    is_consistent = self._check_signal_consistency_with_htf(
                        signal, tf, validated_signals
                    )
                    
                    if is_consistent:
                        validated_tf_signals.append(signal)
                    else:
                        logger.debug(f"Сигнал {signal.signal_type} на {tf} "
                                   f"не согласован с высшими таймфреймами")
                
                validated_signals[tf] = validated_tf_signals
            
            total_original = sum(len(sigs) for sigs in signals.values())
            total_validated = sum(len(sigs) for sigs in validated_signals.values())
            
            logger.debug(f"Валидация сигналов: {total_validated}/{total_original} прошли проверку")
            
            return validated_signals
            
        except Exception as e:
            logger.error(f"Ошибка валидации временной согласованности: {e}")
            return signals  # Возвращаем оригинальные сигналы при ошибке
    
    def get_aligned_timestamps(
        self, 
        timeframe: TimeFrame, 
        data: pd.DataFrame
    ) -> pd.DatetimeIndex:
        """Получение выровненных временных меток для таймфрейма"""
        try:
            if data.empty:
                return pd.DatetimeIndex([])
            
            # Определяем интервал таймфрейма
            interval_minutes = self._get_timeframe_minutes(timeframe)
            
            # Выравниваем временные метки
            start_time = data.index[0]
            end_time = data.index[-1]
            
            # Округляем время начала вниз до границы таймфрейма
            aligned_start = self._align_timestamp_to_timeframe(start_time, timeframe, 'floor')
            
            # Создаем регулярную сетку временных меток
            timestamps = pd.date_range(
                start=aligned_start,
                end=end_time,
                freq=f'{interval_minutes}T'
            )
            
            return timestamps
            
        except Exception as e:
            logger.error(f"Ошибка выравнивания временных меток: {e}")
            return data.index
    
    def _sort_timeframes_by_hierarchy(self, timeframes: List[TimeFrame]) -> List[TimeFrame]:
        """Сортировка таймфреймов по иерархии (от больших к меньшим)"""
        timeframe_order = [
            TimeFrame.D1, TimeFrame.H4, TimeFrame.H1, 
            TimeFrame.M30, TimeFrame.M15, TimeFrame.M5, TimeFrame.M1
        ]
        
        return [tf for tf in timeframe_order if tf in timeframes]
    
    def _trim_data_to_current_time(
        self, 
        data: pd.DataFrame, 
        current_time: datetime, 
        timeframe: TimeFrame
    ) -> pd.DataFrame:
        """Обрезка данных до текущего времени (предотвращение look-ahead bias)"""
        try:
            # Учитываем задержку формирования свечи
            interval_minutes = self._get_timeframe_minutes(timeframe)
            formation_delay = timedelta(minutes=interval_minutes)
            
            # Обрезаем данные
            cutoff_time = current_time - formation_delay
            trimmed_data = data[data.index <= cutoff_time].copy()
            
            if len(trimmed_data) < len(data):
                logger.debug(f"Обрезано {len(data) - len(trimmed_data)} свечей "
                           f"для предотвращения look-ahead bias на {timeframe}")
            
            return trimmed_data
            
        except Exception as e:
            logger.error(f"Ошибка обрезки данных: {e}")
            return data
    
    def _validate_timeframe_data(self, data: pd.DataFrame, timeframe: TimeFrame) -> pd.DataFrame:
        """Валидация данных таймфрейма"""
        try:
            if data.empty:
                return data
            
            # Проверяем регулярность временных интервалов
            expected_interval = self._get_timeframe_minutes(timeframe)
            
            if len(data) > 1:
                actual_intervals = data.index.to_series().diff().dt.total_seconds() / 60
                median_interval = actual_intervals.median()
                
                if abs(median_interval - expected_interval) > expected_interval * 0.1:
                    logger.warning(f"Нерегулярные интервалы на {timeframe}: "
                                 f"ожидается {expected_interval}м, "
                                 f"получено {median_interval}м")
            
            # Проверяем OHLC данные
            invalid_rows = (
                (data['high'] < data['low']) |
                (data['high'] < data['open']) |
                (data['high'] < data['close']) |
                (data['low'] > data['open']) |
                (data['low'] > data['close'])
            )
            
            if invalid_rows.any():
                logger.warning(f"Найдены некорректные OHLC данные на {timeframe}: "
                             f"{invalid_rows.sum()} строк")
                data = data[~invalid_rows]
            
            return data
            
        except Exception as e:
            logger.error(f"Ошибка валидации данных: {e}")
            return data
    
    def _get_higher_timeframes(
        self, 
        timeframe: TimeFrame, 
        available_timeframes: List[TimeFrame]
    ) -> List[TimeFrame]:
        """Получение списка высших таймфреймов"""
        timeframe_hierarchy = [
            TimeFrame.D1, TimeFrame.H4, TimeFrame.H1,
            TimeFrame.M30, TimeFrame.M15, TimeFrame.M5, TimeFrame.M1
        ]
        
        try:
            current_index = timeframe_hierarchy.index(timeframe)
            higher_tfs = timeframe_hierarchy[:current_index]
            
            return [tf for tf in higher_tfs if tf in available_timeframes]
            
        except ValueError:
            return []
    
    def _align_with_higher_timeframes(
        self, 
        data: pd.DataFrame, 
        higher_timeframes: List[TimeFrame], 
        higher_data: Dict[TimeFrame, pd.DataFrame]
    ) -> pd.DataFrame:
        """Выравнивание данных с высшими таймфреймами"""
        try:
            if not higher_timeframes or not higher_data:
                return data
            
            # Находим общий временной диапазон
            min_start_time = data.index[0]
            max_end_time = data.index[-1]
            
            for htf in higher_timeframes:
                if htf in higher_data and not higher_data[htf].empty:
                    htf_data = higher_data[htf]
                    min_start_time = max(min_start_time, htf_data.index[0])
                    max_end_time = min(max_end_time, htf_data.index[-1])
            
            # Обрезаем данные до общего диапазона
            aligned_data = data[
                (data.index >= min_start_time) & 
                (data.index <= max_end_time)
            ].copy()
            
            return aligned_data
            
        except Exception as e:
            logger.error(f"Ошибка выравнивания с высшими таймфреймами: {e}")
            return data
    
    def _get_higher_timeframes_for_context(self, target_timeframe: TimeFrame) -> List[TimeFrame]:
        """Получение высших таймфреймов для формирования контекста"""
        if target_timeframe in [TimeFrame.M1, TimeFrame.M5]:
            return [TimeFrame.D1, TimeFrame.H4, TimeFrame.H1, TimeFrame.M30, TimeFrame.M15]
        elif target_timeframe == TimeFrame.M15:
            return [TimeFrame.D1, TimeFrame.H4, TimeFrame.H1, TimeFrame.M30]
        elif target_timeframe == TimeFrame.M30:
            return [TimeFrame.D1, TimeFrame.H4, TimeFrame.H1]
        elif target_timeframe == TimeFrame.H1:
            return [TimeFrame.D1, TimeFrame.H4]
        elif target_timeframe == TimeFrame.H4:
            return [TimeFrame.D1]
        else:
            return []
    
    def _check_signal_consistency_with_htf(
        self, 
        signal: Signal, 
        timeframe: TimeFrame, 
        htf_signals: Dict[TimeFrame, List[Signal]]
    ) -> bool:
        """Проверка согласованности сигнала с высшими таймфреймами"""
        try:
            higher_timeframes = self._get_higher_timeframes_for_context(timeframe)
            
            # Если нет высших таймфреймов, сигнал валиден
            if not higher_timeframes:
                return True
            
            # Проверяем наличие противоречащих сигналов на высших таймфреймах
            time_window = timedelta(hours=24)  # Окно для поиска конфликтующих сигналов
            
            for htf in higher_timeframes:
                if htf not in htf_signals:
                    continue
                
                for htf_signal in htf_signals[htf]:
                    # Проверяем временную близость
                    time_diff = abs((signal.timestamp - htf_signal.timestamp).total_seconds())
                    if time_diff > time_window.total_seconds():
                        continue
                    
                    # Проверяем противоречия в направлении
                    if (signal.signal_type.value in ['BUY', 'LONG'] and 
                        htf_signal.signal_type.value in ['SELL', 'SHORT']):
                        return False
                    
                    if (signal.signal_type.value in ['SELL', 'SHORT'] and 
                        htf_signal.signal_type.value in ['BUY', 'LONG']):
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка проверки согласованности сигнала: {e}")
            return True  # При ошибке считаем сигнал валидным
    
    def _get_timeframe_minutes(self, timeframe: TimeFrame) -> int:
        """Получение количества минут в таймфрейме"""
        timeframe_minutes = {
            TimeFrame.M1: 1,
            TimeFrame.M5: 5,
            TimeFrame.M15: 15,
            TimeFrame.M30: 30,
            TimeFrame.H1: 60,
            TimeFrame.H4: 240,
            TimeFrame.D1: 1440
        }
        
        return timeframe_minutes.get(timeframe, 60)
    
    def _align_timestamp_to_timeframe(
        self, 
        timestamp: datetime, 
        timeframe: TimeFrame, 
        direction: str = 'floor'
    ) -> datetime:
        """Выравнивание временной метки к границе таймфрейма"""
        try:
            interval_minutes = self._get_timeframe_minutes(timeframe)
            
            if direction == 'floor':
                # Округление вниз
                minutes_from_hour_start = timestamp.minute % interval_minutes
                seconds_from_minute_start = timestamp.second
                microseconds = timestamp.microsecond
                
                aligned_timestamp = timestamp - timedelta(
                    minutes=minutes_from_hour_start,
                    seconds=seconds_from_minute_start,
                    microseconds=microseconds
                )
            else:
                # Округление вверх
                minutes_to_next_interval = interval_minutes - (timestamp.minute % interval_minutes)
                if minutes_to_next_interval == interval_minutes:
                    minutes_to_next_interval = 0
                
                aligned_timestamp = timestamp.replace(
                    second=0, microsecond=0
                ) + timedelta(minutes=minutes_to_next_interval)
            
            return aligned_timestamp
            
        except Exception as e:
            logger.error(f"Ошибка выравнивания временной метки: {e}")
            return timestamp