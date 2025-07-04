"""
Класс для управления портфелем в процессе бэк-тестинга
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd
from dataclasses import dataclass, field

from .trade import Trade, TradeDirection, TradeStatus


@dataclass
class PortfolioState:
    """Состояние портфеля на определенный момент времени"""
    timestamp: datetime
    equity: float
    available_balance: float
    margin_used: float
    unrealized_pnl: float
    realized_pnl: float
    drawdown: float
    drawdown_percent: float


class Portfolio:
    """
    Класс для управления портфелем в бэк-тестинге
    """
    
    def __init__(self, 
                 initial_balance: float = 10000.0,
                 leverage: float = 1.0,
                 commission_rate: float = 0.001,
                 slippage: float = 0.0001):
        """
        Инициализация портфеля
        
        Args:
            initial_balance: Начальный баланс
            leverage: Плечо
            commission_rate: Комиссия (в долях от оборота)
            slippage: Проскальзывание (в долях от цены)
        """
        self.initial_balance = initial_balance
        self.leverage = leverage
        self.commission_rate = commission_rate
        self.slippage = slippage
        
        # Текущее состояние
        self.balance = initial_balance
        self.equity = initial_balance
        self.margin_used = 0.0
        self.max_equity = initial_balance
        
        # Сделки
        self.trades: List[Trade] = []
        self.open_trades: Dict[str, Trade] = {}
        
        # История состояний
        self.equity_curve: List[PortfolioState] = []
        
        # Статистика
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission = 0.0
        
    def can_open_trade(self, 
                      quantity: float, 
                      price: float, 
                      direction: TradeDirection) -> bool:
        """Проверка возможности открытия сделки"""
        required_margin = (quantity * price) / self.leverage
        return self.available_balance >= required_margin
    
    @property
    def available_balance(self) -> float:
        """Доступный баланс для новых сделок"""
        return self.balance - self.margin_used
    
    @property
    def unrealized_pnl(self) -> float:
        """Нереализованная прибыль/убыток"""
        total_unrealized = 0.0
        for trade in self.open_trades.values():
            if hasattr(trade, 'current_price') and trade.current_price:
                if trade.direction == TradeDirection.LONG:
                    pnl = (trade.current_price - trade.entry_price) * trade.quantity
                else:
                    pnl = (trade.entry_price - trade.current_price) * trade.quantity
                total_unrealized += pnl
        return total_unrealized
    
    @property
    def current_drawdown(self) -> Tuple[float, float]:
        """Текущая просадка (абсолютная, процентная)"""
        current_equity = self.balance + self.unrealized_pnl
        drawdown_abs = self.max_equity - current_equity
        drawdown_pct = (drawdown_abs / self.max_equity) * 100 if self.max_equity > 0 else 0
        return drawdown_abs, drawdown_pct
    
    def open_trade(self, 
                   trade_id: str,
                   symbol: str,
                   direction: TradeDirection,
                   quantity: float,
                   price: float,
                   timestamp: datetime,
                   stop_loss: Optional[float] = None,
                   take_profit: Optional[float] = None,
                   strategy_context: Optional[Dict] = None) -> Optional[Trade]:
        """
        Открытие новой сделки
        """
        # Учет проскальзывания
        execution_price = price * (1 + self.slippage if direction == TradeDirection.LONG else 1 - self.slippage)
        
        # Проверка доступности средств
        if not self.can_open_trade(quantity, execution_price, direction):
            return None
        
        # Расчет комиссии
        commission = quantity * execution_price * self.commission_rate
        
        # Создание сделки
        trade = Trade(
            id=trade_id,
            symbol=symbol,
            direction=direction,
            entry_price=execution_price,
            entry_time=timestamp,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission=commission,
            strategy_context=strategy_context
        )
        
        # Обновление портфеля
        required_margin = (quantity * execution_price) / self.leverage
        self.margin_used += required_margin
        self.balance -= commission
        self.total_commission += commission
        
        # Сохранение сделки
        self.trades.append(trade)
        self.open_trades[trade_id] = trade
        self.total_trades += 1
        
        return trade
    
    def close_trade(self, 
                    trade_id: str, 
                    price: float, 
                    timestamp: datetime,
                    exit_reason: str = "manual") -> Optional[Trade]:
        """
        Закрытие сделки
        """
        if trade_id not in self.open_trades:
            return None
        
        trade = self.open_trades[trade_id]
        
        # Учет проскальзывания
        execution_price = price * (1 - self.slippage if trade.direction == TradeDirection.LONG else 1 + self.slippage)
        
        # Расчет дополнительной комиссии при закрытии
        close_commission = trade.quantity * execution_price * self.commission_rate
        trade.commission += close_commission
        
        # Закрытие сделки
        trade.close_trade(execution_price, timestamp, exit_reason)
        
        # Обновление портфеля
        released_margin = (trade.quantity * trade.entry_price) / self.leverage
        self.margin_used -= released_margin
        if trade.pnl is not None:
            self.balance += trade.pnl - close_commission
        else:
            self.balance -= close_commission
        self.total_commission += close_commission
        
        # Обновление статистики
        if trade.is_profitable:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Удаление из открытых сделок
        del self.open_trades[trade_id]
        
        return trade
    
    def update_equity(self, timestamp: datetime):
        """Обновление эквити с учетом нереализованных P&L"""
        current_equity = self.balance + self.unrealized_pnl
        self.equity = current_equity
        
        # Обновление максимального эквити
        if current_equity > self.max_equity:
            self.max_equity = current_equity
        
        # Расчет просадки
        drawdown_abs, drawdown_pct = self.current_drawdown
        
        # Сохранение состояния
        state = PortfolioState(
            timestamp=timestamp,
            equity=current_equity,
            available_balance=self.available_balance,
            margin_used=self.margin_used,
            unrealized_pnl=self.unrealized_pnl,
            realized_pnl=self.balance - self.initial_balance,
            drawdown=drawdown_abs,
            drawdown_percent=drawdown_pct
        )
        self.equity_curve.append(state)
    
    def check_stop_losses_and_take_profits(self, 
                                         current_prices: Dict[str, float], 
                                         timestamp: datetime) -> List[Trade]:
        """
        Проверка стоп-лоссов и тейк-профитов
        """
        closed_trades = []
        trades_to_close = []
        
        for trade in self.open_trades.values():
            if trade.symbol not in current_prices:
                continue
                
            current_price = current_prices[trade.symbol]
            
            # Обновление текущей цены для расчета нереализованного P&L
            trade.current_price = current_price
            
            should_close = False
            exit_reason = ""
            
            # Проверка стоп-лосса
            if trade.stop_loss:
                if ((trade.direction == TradeDirection.LONG and current_price <= trade.stop_loss) or
                    (trade.direction == TradeDirection.SHORT and current_price >= trade.stop_loss)):
                    should_close = True
                    exit_reason = "stop_loss"
            
            # Проверка тейк-профита
            if trade.take_profit and not should_close:
                if ((trade.direction == TradeDirection.LONG and current_price >= trade.take_profit) or
                    (trade.direction == TradeDirection.SHORT and current_price <= trade.take_profit)):
                    should_close = True
                    exit_reason = "take_profit"
            
            if should_close:
                trades_to_close.append((trade.id, current_price, exit_reason))
        
        # Закрытие сделок
        for trade_id, price, reason in trades_to_close:
            closed_trade = self.close_trade(trade_id, price, timestamp, reason)
            if closed_trade:
                closed_trades.append(closed_trade)
        
        return closed_trades
    
    def get_performance_summary(self) -> Dict:
        """Получение краткой сводки по производительности"""
        total_return = ((self.equity - self.initial_balance) / self.initial_balance) * 100
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        # Расчет максимальной просадки
        max_dd = 0
        for state in self.equity_curve:
            if state.drawdown_percent > max_dd:
                max_dd = state.drawdown_percent
        
        return {
            'total_return_percent': total_return,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate_percent': win_rate,
            'max_drawdown_percent': max_dd,
            'total_commission': self.total_commission,
            'final_equity': self.equity,
            'current_balance': self.balance
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """Конвертация истории эквити в DataFrame"""
        if not self.equity_curve:
            return pd.DataFrame()
        
        data = []
        for state in self.equity_curve:
            data.append({
                'timestamp': state.timestamp,
                'equity': state.equity,
                'available_balance': state.available_balance,
                'margin_used': state.margin_used,
                'unrealized_pnl': state.unrealized_pnl,
                'realized_pnl': state.realized_pnl,
                'drawdown': state.drawdown,
                'drawdown_percent': state.drawdown_percent
            })
        
        return pd.DataFrame(data)