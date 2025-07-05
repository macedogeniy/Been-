"""
Менеджер рисков для стратегии "Охота за ликвидностью"
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from loguru import logger

from core.interfaces import IRiskManager
from core.data_types import (
    Signal, Trade, MarketState, ContextState, PositionStatus,
    TimeFrame, MarketStructure
)
from core.exceptions import RiskManagementError
from config import get_config


class LiquidityHuntRiskManager(IRiskManager):
    """Менеджер рисков для стратегии "Охота за ликвидностью" """
    
    def __init__(self):
        self.config = get_config()
        self._open_positions: List[Trade] = []
        self._risk_metrics: Dict[str, float] = {}
        self._drawdown_tracker: List[float] = []
        
    def calculate_position_size(
        self, 
        signal: Signal, 
        account_balance: float
    ) -> float:
        """Расчет размера позиции с учетом рисков"""
        try:
            # Базовый риск на сделку (% от депозита)
            base_risk_percent = self.config.risk.max_risk_per_trade
            
            # Корректировка на основе качества сигнала
            quality_multiplier = self._calculate_quality_multiplier(signal)
            
            # Корректировка на основе текущего состояния счета
            balance_multiplier = self._calculate_balance_multiplier(account_balance)
            
            # Корректировка на основе волатильности
            volatility_multiplier = self._calculate_volatility_multiplier(signal)
            
            # Корректировка на основе корреляции с открытыми позициями
            correlation_multiplier = self._calculate_correlation_multiplier(signal)
            
            # Итоговый процент риска
            adjusted_risk_percent = (
                base_risk_percent * 
                quality_multiplier * 
                balance_multiplier * 
                volatility_multiplier * 
                correlation_multiplier
            )
            
            # Ограничиваем максимальным риском
            adjusted_risk_percent = min(
                adjusted_risk_percent, 
                self.config.risk.max_risk_per_trade * 2
            )
            
            # Рассчитываем размер позиции
            risk_amount = account_balance * (adjusted_risk_percent / 100)
            
            # Размер стоп-лосса в валюте
            stop_distance = abs(signal.entry_price - signal.stop_loss)
            
            if stop_distance > 0:
                position_size = risk_amount / stop_distance
            else:
                position_size = 0.0
            
            # Ограничиваем максимальным размером позиции
            max_position_value = account_balance * (self.config.risk.max_position_size / 100)
            max_position_size = max_position_value / signal.entry_price
            
            position_size = min(position_size, max_position_size)
            
            logger.debug(f"Расчет размера позиции: риск {adjusted_risk_percent:.2f}%, "
                        f"размер {position_size:.6f}")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Ошибка расчета размера позиции: {e}")
            # Возвращаем минимальный размер при ошибке
            return account_balance * 0.001 / signal.entry_price
    
    def validate_risk_parameters(self, signal: Signal) -> bool:
        """Валидация риск-параметров сигнала"""
        try:
            # Проверяем R:R соотношение
            if signal.risk_reward_ratio < self.config.risk.min_risk_reward:
                logger.warning(f"Сигнал отклонен: низкое R:R ({signal.risk_reward_ratio:.2f})")
                return False
            
            # Проверяем максимальный риск на сделку
            stop_distance_percent = abs(signal.entry_price - signal.stop_loss) / signal.entry_price
            if stop_distance_percent > self.config.risk.max_stop_distance:
                logger.warning(f"Сигнал отклонен: слишком большой стоп ({stop_distance_percent:.2%})")
                return False
            
            # Проверяем минимальный риск на сделку
            if stop_distance_percent < self.config.risk.min_stop_distance:
                logger.warning(f"Сигнал отклонен: слишком маленький стоп ({stop_distance_percent:.2%})")
                return False
            
            # Проверяем разумность цен
            if signal.entry_price <= 0 or signal.stop_loss <= 0 or signal.take_profit <= 0:
                logger.warning("Сигнал отклонен: некорректные цены")
                return False
            
            # Проверяем логику стоп-лосса и тейк-профита
            if signal.is_long:
                if signal.stop_loss >= signal.entry_price or signal.take_profit <= signal.entry_price:
                    logger.warning("Сигнал отклонен: некорректная логика лонг позиции")
                    return False
            else:
                if signal.stop_loss <= signal.entry_price or signal.take_profit >= signal.entry_price:
                    logger.warning("Сигнал отклонен: некорректная логика шорт позиции")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка валидации риск-параметров: {e}")
            return False
    
    def check_correlation_risk(
        self, 
        new_signal: Signal, 
        open_positions: List[Trade]
    ) -> bool:
        """Проверка корреляционного риска"""
        try:
            if not open_positions:
                return True
            
            # Обновляем список открытых позиций
            self._open_positions = [pos for pos in open_positions if pos.status == PositionStatus.OPEN]
            
            # Проверяем количество открытых позиций
            if len(self._open_positions) >= self.config.risk.max_open_positions:
                logger.warning(f"Превышено максимальное количество позиций: {len(self._open_positions)}")
                return False
            
            # Проверяем корреляцию по направлению
            same_direction_count = sum(
                1 for pos in self._open_positions 
                if self._same_direction(pos.signal, new_signal)
            )
            
            if same_direction_count >= self.config.risk.max_same_direction_positions:
                logger.warning(f"Превышено количество позиций в одном направлении: {same_direction_count}")
                return False
            
            # Проверяем корреляцию по времени
            time_correlation_risk = self._check_time_correlation(new_signal)
            if not time_correlation_risk:
                logger.warning("Отклонено из-за временной корреляции")
                return False
            
            # Проверяем общий риск портфеля
            portfolio_risk = self._calculate_portfolio_risk(new_signal)
            if portfolio_risk > self.config.risk.max_portfolio_risk:
                logger.warning(f"Превышен максимальный риск портфеля: {portfolio_risk:.2%}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка проверки корреляционного риска: {e}")
            return True  # При ошибке разрешаем сделку
    
    def update_stop_loss(
        self, 
        trade: Trade, 
        current_price: float, 
        market_state: MarketState
    ) -> Optional[float]:
        """Обновление стоп-лосса (трейлинг стоп)"""
        try:
            if trade.status != PositionStatus.OPEN:
                return None
            
            original_signal = trade.signal
            current_stop = original_signal.stop_loss
            
            # Проверяем, находится ли сделка в прибыли
            if original_signal.is_long:
                profit_points = current_price - trade.entry_price
                if profit_points <= 0:
                    return current_stop  # Не трейлим в убытке
                
                # Рассчитываем новый стоп на основе структуры
                new_stop = self._calculate_trailing_stop_long(
                    trade, current_price, market_state
                )
                
                # Стоп может только подниматься для лонга
                if new_stop > current_stop:
                    logger.info(f"Обновлен стоп для лонг позиции: {current_stop:.2f} -> {new_stop:.2f}")
                    return new_stop
                    
            else:  # Шорт позиция
                profit_points = trade.entry_price - current_price
                if profit_points <= 0:
                    return current_stop  # Не трейлим в убытке
                
                # Рассчитываем новый стоп
                new_stop = self._calculate_trailing_stop_short(
                    trade, current_price, market_state
                )
                
                # Стоп может только опускаться для шорта
                if new_stop < current_stop:
                    logger.info(f"Обновлен стоп для шорт позиции: {current_stop:.2f} -> {new_stop:.2f}")
                    return new_stop
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка обновления стоп-лосса: {e}")
            return None
    
    def get_risk_metrics(self) -> Dict[str, float]:
        """Получение текущих метрик риска"""
        try:
            return {
                'open_positions': len(self._open_positions),
                'portfolio_risk': self._calculate_current_portfolio_risk(),
                'max_drawdown': self._calculate_max_drawdown(),
                'current_drawdown': self._calculate_current_drawdown(),
                'risk_score': self._calculate_overall_risk_score(),
                'position_correlation': self._calculate_position_correlation(),
                'volatility_risk': self._calculate_volatility_risk()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения метрик риска: {e}")
            return {}
    
    def should_reduce_risk(self, context: ContextState) -> bool:
        """Определение необходимости снижения рисков"""
        try:
            # Проверяем уровень страха
            if context.fear_factor > 0.8:
                return True
            
            # Проверяем текущую просадку
            current_drawdown = self._calculate_current_drawdown()
            if current_drawdown > self.config.risk.max_drawdown * 0.8:
                return True
            
            # Проверяем количество убыточных сделок подряд
            recent_losses = self._count_recent_losses()
            if recent_losses >= 3:
                return True
            
            # Проверяем рыночную волатильность
            if context.market_regime == "high_volatility":
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка определения снижения рисков: {e}")
            return False
    
    # Приватные методы
    def _calculate_quality_multiplier(self, signal: Signal) -> float:
        """Корректировка размера на основе качества сигнала"""
        # Высокий скор конфлюенции = больший размер позиции
        base_multiplier = 0.5 + signal.confluence_score * 0.5
        
        # Корректировка на R:R соотношение
        rr_multiplier = min(signal.risk_reward_ratio / 2.0, 1.5)
        
        return base_multiplier * rr_multiplier
    
    def _calculate_balance_multiplier(self, account_balance: float) -> float:
        """Корректировка размера на основе состояния счета"""
        # При больших балансах можем позволить себе больший риск
        if account_balance > 100000:
            return 1.2
        elif account_balance > 50000:
            return 1.1
        elif account_balance < 10000:
            return 0.8
        else:
            return 1.0
    
    def _calculate_volatility_multiplier(self, signal: Signal) -> float:
        """Корректировка размера на основе волатильности"""
        # При высокой волатильности снижаем размер
        stop_distance = abs(signal.entry_price - signal.stop_loss) / signal.entry_price
        
        if stop_distance > 0.03:  # > 3%
            return 0.7
        elif stop_distance > 0.02:  # > 2%
            return 0.85
        else:
            return 1.0
    
    def _calculate_correlation_multiplier(self, signal: Signal) -> float:
        """Корректировка размера на основе корреляции"""
        # При большом количестве позиций снижаем размер новых
        position_count = len(self._open_positions)
        
        if position_count >= 3:
            return 0.6
        elif position_count >= 2:
            return 0.8
        else:
            return 1.0
    
    def _same_direction(self, signal1: Signal, signal2: Signal) -> bool:
        """Проверка совпадения направления сигналов"""
        return (signal1.is_long and signal2.is_long) or (signal1.is_short and signal2.is_short)
    
    def _check_time_correlation(self, new_signal: Signal) -> bool:
        """Проверка временной корреляции"""
        time_window = timedelta(hours=2)
        
        recent_signals = [
            pos.signal for pos in self._open_positions
            if abs((pos.entry_time - new_signal.timestamp).total_seconds()) < time_window.total_seconds()
        ]
        
        # Не более 2 сигналов в течение 2 часов
        return len(recent_signals) < 2
    
    def _calculate_portfolio_risk(self, new_signal: Signal) -> float:
        """Расчет общего риска портфеля"""
        total_risk = 0.0
        
        # Добавляем риски текущих позиций
        for pos in self._open_positions:
            position_risk = abs(pos.entry_price - pos.signal.stop_loss) / pos.entry_price
            total_risk += position_risk
        
        # Добавляем риск нового сигнала
        new_risk = abs(new_signal.entry_price - new_signal.stop_loss) / new_signal.entry_price
        total_risk += new_risk
        
        return total_risk
    
    def _calculate_trailing_stop_long(
        self, 
        trade: Trade, 
        current_price: float, 
        market_state: MarketState
    ) -> float:
        """Расчет трейлинг стопа для лонг позиции"""
        # Базовый трейлинг стоп на основе ATR или фиксированного %
        trailing_distance = trade.entry_price * 0.02  # 2%
        
        # Ищем структурные уровни для стопа
        structural_stop = self._find_structural_stop_long(current_price, market_state)
        
        if structural_stop:
            return max(structural_stop, current_price - trailing_distance)
        else:
            return current_price - trailing_distance
    
    def _calculate_trailing_stop_short(
        self, 
        trade: Trade, 
        current_price: float, 
        market_state: MarketState
    ) -> float:
        """Расчет трейлинг стопа для шорт позиции"""
        # Базовый трейлинг стоп
        trailing_distance = trade.entry_price * 0.02  # 2%
        
        # Ищем структурные уровни для стопа
        structural_stop = self._find_structural_stop_short(current_price, market_state)
        
        if structural_stop:
            return min(structural_stop, current_price + trailing_distance)
        else:
            return current_price + trailing_distance
    
    def _find_structural_stop_long(
        self, 
        current_price: float, 
        market_state: MarketState
    ) -> Optional[float]:
        """Поиск структурного стопа для лонг позиции"""
        # Ищем ближайший свинг-лоу ниже текущей цены
        suitable_lows = [
            swing.price for swing in market_state.swing_lows
            if swing.price < current_price and swing.confirmed
        ]
        
        if suitable_lows:
            return max(suitable_lows) * 0.999  # Чуть ниже свинг-лоу
        
        return None
    
    def _find_structural_stop_short(
        self, 
        current_price: float, 
        market_state: MarketState
    ) -> Optional[float]:
        """Поиск структурного стопа для шорт позиции"""
        # Ищем ближайший свинг-хай выше текущей цены
        suitable_highs = [
            swing.price for swing in market_state.swing_highs
            if swing.price > current_price and swing.confirmed
        ]
        
        if suitable_highs:
            return min(suitable_highs) * 1.001  # Чуть выше свинг-хай
        
        return None
    
    def _calculate_current_portfolio_risk(self) -> float:
        """Расчет текущего риска портфеля"""
        if not self._open_positions:
            return 0.0
        
        total_risk = 0.0
        for pos in self._open_positions:
            position_risk = abs(pos.entry_price - pos.signal.stop_loss) / pos.entry_price
            total_risk += position_risk
        
        return total_risk
    
    def _calculate_max_drawdown(self) -> float:
        """Расчет максимальной просадки"""
        if not self._drawdown_tracker:
            return 0.0
        return max(self._drawdown_tracker)
    
    def _calculate_current_drawdown(self) -> float:
        """Расчет текущей просадки"""
        if not self._drawdown_tracker:
            return 0.0
        return self._drawdown_tracker[-1] if self._drawdown_tracker else 0.0
    
    def _calculate_overall_risk_score(self) -> float:
        """Расчет общего скора риска (0-1)"""
        score = 0.0
        
        # Количество позиций
        position_score = len(self._open_positions) / self.config.risk.max_open_positions
        score += position_score * 0.3
        
        # Риск портфеля
        portfolio_risk = self._calculate_current_portfolio_risk()
        risk_score = portfolio_risk / self.config.risk.max_portfolio_risk
        score += risk_score * 0.4
        
        # Просадка
        drawdown = self._calculate_current_drawdown()
        drawdown_score = drawdown / self.config.risk.max_drawdown
        score += drawdown_score * 0.3
        
        return min(score, 1.0)
    
    def _calculate_position_correlation(self) -> float:
        """Расчет корреляции между позициями"""
        if len(self._open_positions) < 2:
            return 0.0
        
        # Простая корреляция на основе направления и времени
        same_direction_count = 0
        total_pairs = 0
        
        for i, pos1 in enumerate(self._open_positions):
            for pos2 in self._open_positions[i+1:]:
                total_pairs += 1
                if self._same_direction(pos1.signal, pos2.signal):
                    same_direction_count += 1
        
        return same_direction_count / total_pairs if total_pairs > 0 else 0.0
    
    def _calculate_volatility_risk(self) -> float:
        """Расчет риска волатильности"""
        if not self._open_positions:
            return 0.0
        
        avg_stop_distance = np.mean([
            abs(pos.entry_price - pos.signal.stop_loss) / pos.entry_price
            for pos in self._open_positions
        ])
        
        return min(avg_stop_distance / 0.05, 1.0)  # Нормализуем к 5%
    
    def _count_recent_losses(self, days: int = 7) -> int:
        """Подсчет недавних убыточных сделок"""
        # В реальной реализации это будет анализ истории сделок
        # Пока возвращаем 0 для демонстрации
        return 0
    
    def update_drawdown(self, current_balance: float, peak_balance: float) -> None:
        """Обновление трекера просадки"""
        try:
            if peak_balance > 0:
                drawdown = (peak_balance - current_balance) / peak_balance
                self._drawdown_tracker.append(drawdown)
                
                # Ограничиваем размер истории
                if len(self._drawdown_tracker) > 1000:
                    self._drawdown_tracker = self._drawdown_tracker[-500:]
                    
        except Exception as e:
            logger.error(f"Ошибка обновления просадки: {e}")
    
    def emergency_close_all(self) -> bool:
        """Экстренное закрытие всех позиций"""
        try:
            logger.warning("Активировано экстренное закрытие всех позиций!")
            
            # В реальной реализации здесь будет код закрытия позиций через API
            for pos in self._open_positions:
                pos.status = PositionStatus.CLOSED
                logger.info(f"Экстренно закрыта позиция {pos.trade_id}")
            
            self._open_positions.clear()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экстренного закрытия позиций: {e}")
            return False


# Alias for compatibility
RiskManager = LiquidityHuntRiskManager