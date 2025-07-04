"""
Класс для представления торговых операций в бэк-тестинге
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class TradeDirection(Enum):
    """Направление торговой операции"""
    LONG = "long"
    SHORT = "short"

class TradeStatus(Enum):
    """Статус торговой операции"""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

@dataclass
class Trade:
    """
    Класс для представления торговой операции
    """
    
    # Основные параметры
    id: str
    symbol: str
    direction: TradeDirection
    entry_price: float
    entry_time: datetime
    quantity: float
    
    # Параметры выхода
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    
    # Управление рисками
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Статус и результаты
    status: TradeStatus = TradeStatus.OPEN
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    commission: float = 0.0
    
    # Метаданные стратегии
    strategy_context: Optional[Dict[str, Any]] = None
    timeframe: Optional[str] = None
    poi_type: Optional[str] = None  # Тип зоны интереса
    confidence: Optional[float] = None  # Уверенность в сигнале
    current_price: Optional[float] = None  # Текущая цена для расчета нереализованного P&L
    
    def close_trade(self, exit_price: float, exit_time: datetime, exit_reason: str = "manual"):
        """Закрытие торговой операции"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = exit_reason
        self.status = TradeStatus.CLOSED
        
        # Расчет P&L
        if self.direction == TradeDirection.LONG:
            price_diff = exit_price - self.entry_price
        else:
            price_diff = self.entry_price - exit_price
            
        self.pnl = (price_diff * self.quantity) - self.commission
        self.pnl_percent = (price_diff / self.entry_price) * 100
        
    @property
    def is_open(self) -> bool:
        """Проверка, открыта ли сделка"""
        return self.status == TradeStatus.OPEN
    
    @property
    def is_profitable(self) -> bool:
        """Проверка прибыльности сделки"""
        return self.pnl is not None and self.pnl > 0
    
    @property
    def duration(self) -> Optional[float]:
        """Длительность сделки в часах"""
        if self.exit_time and self.entry_time:
            return (self.exit_time - self.entry_time).total_seconds() / 3600
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для экспорта"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'direction': self.direction.value,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_reason': self.exit_reason,
            'quantity': self.quantity,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'status': self.status.value,
            'pnl': self.pnl,
            'pnl_percent': self.pnl_percent,
            'commission': self.commission,
            'duration_hours': self.duration,
            'timeframe': self.timeframe,
            'poi_type': self.poi_type,
            'confidence': self.confidence
        }