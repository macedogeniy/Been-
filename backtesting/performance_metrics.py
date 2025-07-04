"""
Класс для расчета метрик производительности торговых стратегий
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import math

from .trade import Trade
from .portfolio import Portfolio, PortfolioState


class PerformanceMetrics:
    """
    Класс для расчета метрик производительности торговых стратегий
    """
    
    def __init__(self, portfolio: Portfolio, benchmark_return: float = 0.0):
        """
        Инициализация метрик производительности
        
        Args:
            portfolio: Портфель для анализа
            benchmark_return: Доходность бенчмарка для сравнения (годовая, в процентах)
        """
        self.portfolio = portfolio
        self.benchmark_return = benchmark_return
        self.trades = portfolio.trades
        self.equity_curve = portfolio.equity_curve
        
    def get_comprehensive_metrics(self) -> Dict:
        """Получение полного набора метрик производительности"""
        
        if not self.trades or not self.equity_curve:
            return {}
        
        # Базовые метрики
        basic_metrics = self._calculate_basic_metrics()
        
        # Метрики риска
        risk_metrics = self._calculate_risk_metrics()
        
        # Метрики сделок
        trade_metrics = self._calculate_trade_metrics()
        
        # Временные метрики
        time_metrics = self._calculate_time_metrics()
        
        # Метрики просадки
        drawdown_metrics = self._calculate_drawdown_metrics()
        
        # Метрики по типам POI
        poi_metrics = self._calculate_poi_metrics()
        
        return {
            **basic_metrics,
            **risk_metrics,
            **trade_metrics,
            **time_metrics,
            **drawdown_metrics,
            **poi_metrics
        }
    
    def _calculate_basic_metrics(self) -> Dict:
        """Расчет базовых метрик доходности"""
        initial_balance = self.portfolio.initial_balance
        final_equity = self.portfolio.equity
        
        # Общая доходность
        total_return = ((final_equity - initial_balance) / initial_balance) * 100
        
        # Период тестирования
        start_date = self.equity_curve[0].timestamp
        end_date = self.equity_curve[-1].timestamp
        total_days = (end_date - start_date).days
        
        # Годовая доходность
        if total_days > 0:
            annual_return = ((final_equity / initial_balance) ** (365.25 / total_days) - 1) * 100
        else:
            annual_return = 0
        
        # Альфа (превышение над бенчмарком)
        alpha = annual_return - self.benchmark_return
        
        return {
            'total_return_percent': round(total_return, 2),
            'annual_return_percent': round(annual_return, 2),
            'alpha_percent': round(alpha, 2),
            'initial_balance': initial_balance,
            'final_equity': round(final_equity, 2),
            'total_days': total_days,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    
    def _calculate_risk_metrics(self) -> Dict:
        """Расчет метрик риска"""
        if len(self.equity_curve) < 2:
            return {}
        
        # Получение дневных доходностей
        daily_returns = self._get_daily_returns()
        
        if len(daily_returns) < 2:
            return {}
        
        # Волатильность
        volatility_daily = np.std(daily_returns) * 100
        volatility_annual = volatility_daily * np.sqrt(252)  # 252 торговых дня в году
        
        # Коэффициент Шарпа
        mean_daily_return = np.mean(daily_returns)
        sharpe_ratio = (mean_daily_return / np.std(daily_returns) * np.sqrt(252)) if np.std(daily_returns) > 0 else 0
        
        # Максимальная просадка
        max_drawdown = self._calculate_max_drawdown()
        
        # Коэффициент Калмара (годовая доходность / максимальная просадка)
        annual_return = self._calculate_annual_return()
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # VaR (Value at Risk) на уровне 95%
        var_95 = np.percentile(daily_returns, 5) * 100
        
        # CVaR (Conditional Value at Risk)
        cvar_95 = np.mean([r for r in daily_returns if r <= np.percentile(daily_returns, 5)]) * 100
        
        return {
            'volatility_annual_percent': round(volatility_annual, 2),
            'sharpe_ratio': round(sharpe_ratio, 3),
            'calmar_ratio': round(calmar_ratio, 3),
            'var_95_percent': round(var_95, 2),
            'cvar_95_percent': round(cvar_95, 2)
        }
    
    def _calculate_trade_metrics(self) -> Dict:
        """Расчет метрик сделок"""
        closed_trades = [t for t in self.trades if not t.is_open]
        
        if not closed_trades:
            return {'total_trades': 0}
        
        total_trades = len(closed_trades)
        winning_trades = len([t for t in closed_trades if t.is_profitable])
        losing_trades = total_trades - winning_trades
        
        # Винрейт
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Средняя прибыль/убыток
        profits = [t.pnl for t in closed_trades if t.is_profitable and t.pnl is not None]
        losses = [t.pnl for t in closed_trades if not t.is_profitable and t.pnl is not None]
        
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 0
        
        # Profit Factor
        total_profit = sum(profits) if profits else 0
        total_loss = abs(sum(losses)) if losses else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0
        
        # Largest win/loss
        largest_win = max(profits) if profits else 0
        largest_loss = min(losses) if losses else 0
        
        # Средняя длительность сделок
        durations = [t.duration for t in closed_trades if t.duration is not None]
        avg_duration_hours = np.mean(durations) if durations else 0
        
        # Consecutives wins/losses
        max_consecutive_wins, max_consecutive_losses = self._calculate_consecutive_trades(closed_trades)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate_percent': round(win_rate, 2),
            'avg_profit': round(avg_profit, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2),
            'avg_duration_hours': round(avg_duration_hours, 2),
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'total_commission': round(self.portfolio.total_commission, 2)
        }
    
    def _calculate_time_metrics(self) -> Dict:
        """Расчет временных метрик"""
        closed_trades = [t for t in self.trades if not t.is_open]
        
        if not closed_trades:
            return {}
        
        # Анализ по часам дня
        hourly_pnl = {}
        for trade in closed_trades:
            if trade.entry_time and trade.pnl is not None:
                hour = trade.entry_time.hour
                if hour not in hourly_pnl:
                    hourly_pnl[hour] = []
                hourly_pnl[hour].append(trade.pnl)
        
        # Лучший и худший час
        hourly_avg = {hour: np.mean(pnls) for hour, pnls in hourly_pnl.items()}
        best_hour = max(hourly_avg.keys(), key=lambda x: hourly_avg[x]) if hourly_avg else None
        worst_hour = min(hourly_avg.keys(), key=lambda x: hourly_avg[x]) if hourly_avg else None
        
        # Анализ по дням недели
        daily_pnl = {}
        for trade in closed_trades:
            if trade.entry_time and trade.pnl is not None:
                weekday = trade.entry_time.weekday()  # 0=Monday, 6=Sunday
                if weekday not in daily_pnl:
                    daily_pnl[weekday] = []
                daily_pnl[weekday].append(trade.pnl)
        
        # Лучший и худший день недели
        daily_avg = {day: np.mean(pnls) for day, pnls in daily_pnl.items()}
        best_weekday = max(daily_avg.keys(), key=lambda x: daily_avg[x]) if daily_avg else None
        worst_weekday = min(daily_avg.keys(), key=lambda x: daily_avg[x]) if daily_avg else None
        
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        return {
            'best_hour': best_hour,
            'worst_hour': worst_hour,
            'best_weekday': weekday_names[best_weekday] if best_weekday is not None else None,
            'worst_weekday': weekday_names[worst_weekday] if worst_weekday is not None else None,
            'hourly_performance': {f'hour_{hour}': round(avg, 2) for hour, avg in hourly_avg.items()},
            'daily_performance': {weekday_names[day]: round(avg, 2) for day, avg in daily_avg.items()}
        }
    
    def _calculate_drawdown_metrics(self) -> Dict:
        """Расчет метрик просадки"""
        if not self.equity_curve:
            return {}
        
        max_dd_percent = 0
        max_dd_duration = 0
        current_dd_duration = 0
        peak_equity = self.portfolio.initial_balance
        
        for state in self.equity_curve:
            if state.equity > peak_equity:
                peak_equity = state.equity
                current_dd_duration = 0
            else:
                current_dd_duration += 1
                max_dd_duration = max(max_dd_duration, current_dd_duration)
            
            dd_percent = ((peak_equity - state.equity) / peak_equity) * 100
            max_dd_percent = max(max_dd_percent, dd_percent)
        
        # Underwater curve - время в просадке
        underwater_periods = sum(1 for state in self.equity_curve if state.drawdown_percent > 1)
        underwater_percent = (underwater_periods / len(self.equity_curve)) * 100 if self.equity_curve else 0
        
        return {
            'max_drawdown_percent': round(max_dd_percent, 2),
            'max_drawdown_duration_periods': max_dd_duration,
            'underwater_percent': round(underwater_percent, 2)
        }
    
    def _calculate_poi_metrics(self) -> Dict:
        """Анализ производительности по типам POI"""
        closed_trades = [t for t in self.trades if not t.is_open]
        
        poi_stats = {}
        for trade in closed_trades:
            if trade.poi_type and trade.pnl is not None:
                if trade.poi_type not in poi_stats:
                    poi_stats[trade.poi_type] = {'trades': [], 'wins': 0}
                
                poi_stats[trade.poi_type]['trades'].append(trade.pnl)
                if trade.is_profitable:
                    poi_stats[trade.poi_type]['wins'] += 1
        
        # Статистика по типам POI
        poi_performance = {}
        for poi_type, stats in poi_stats.items():
            total_trades = len(stats['trades'])
            win_rate = (stats['wins'] / total_trades) * 100 if total_trades > 0 else 0
            avg_pnl = np.mean(stats['trades']) if stats['trades'] else 0
            
            poi_performance[f'{poi_type}_trades'] = total_trades
            poi_performance[f'{poi_type}_win_rate'] = round(win_rate, 2)
            poi_performance[f'{poi_type}_avg_pnl'] = round(avg_pnl, 2)
        
        return poi_performance
    
    def _get_daily_returns(self) -> List[float]:
        """Получение дневных доходностей"""
        if len(self.equity_curve) < 2:
            return []
        
        daily_returns = []
        prev_equity = self.equity_curve[0].equity
        
        for state in self.equity_curve[1:]:
            if prev_equity > 0:
                daily_return = (state.equity - prev_equity) / prev_equity
                daily_returns.append(daily_return)
            prev_equity = state.equity
        
        return daily_returns
    
    def _calculate_max_drawdown(self) -> float:
        """Расчет максимальной просадки"""
        if not self.equity_curve:
            return 0
        
        max_dd = 0
        peak = self.portfolio.initial_balance
        
        for state in self.equity_curve:
            if state.equity > peak:
                peak = state.equity
            
            dd = ((peak - state.equity) / peak) * 100
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def _calculate_annual_return(self) -> float:
        """Расчет годовой доходности"""
        if not self.equity_curve or len(self.equity_curve) < 2:
            return 0
        
        start_date = self.equity_curve[0].timestamp
        end_date = self.equity_curve[-1].timestamp
        total_days = (end_date - start_date).days
        
        if total_days <= 0:
            return 0
        
        initial_equity = self.portfolio.initial_balance
        final_equity = self.portfolio.equity
        
        annual_return = ((final_equity / initial_equity) ** (365.25 / total_days) - 1) * 100
        return annual_return
    
    def _calculate_consecutive_trades(self, trades: List[Trade]) -> Tuple[int, int]:
        """Расчет максимальных последовательных выигрышей/проигрышей"""
        if not trades:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in sorted(trades, key=lambda x: x.entry_time):
            if trade.is_profitable:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    def generate_report(self) -> str:
        """Генерация текстового отчета"""
        metrics = self.get_comprehensive_metrics()
        
        if not metrics:
            return "Недостаточно данных для генерации отчета"
        
        report = f"""
=== ОТЧЕТ ПО ПРОИЗВОДИТЕЛЬНОСТИ СТРАТЕГИИ ===

Период тестирования: {metrics.get('start_date', 'N/A')} - {metrics.get('end_date', 'N/A')}
Продолжительность: {metrics.get('total_days', 0)} дней

ОСНОВНЫЕ ПОКАЗАТЕЛИ:
- Общая доходность: {metrics.get('total_return_percent', 0):.2f}%
- Годовая доходность: {metrics.get('annual_return_percent', 0):.2f}%
- Начальный баланс: ${metrics.get('initial_balance', 0):,.2f}
- Финальный капитал: ${metrics.get('final_equity', 0):,.2f}

ПОКАЗАТЕЛИ РИСКА:
- Максимальная просадка: {metrics.get('max_drawdown_percent', 0):.2f}%
- Коэффициент Шарпа: {metrics.get('sharpe_ratio', 0):.3f}
- Коэффициент Калмара: {metrics.get('calmar_ratio', 0):.3f}
- Годовая волатильность: {metrics.get('volatility_annual_percent', 0):.2f}%

СТАТИСТИКА СДЕЛОК:
- Всего сделок: {metrics.get('total_trades', 0)}
- Прибыльных: {metrics.get('winning_trades', 0)}
- Убыточных: {metrics.get('losing_trades', 0)}
- Винрейт: {metrics.get('win_rate_percent', 0):.2f}%
- Profit Factor: {metrics.get('profit_factor', 0):.2f}
- Средняя прибыль: ${metrics.get('avg_profit', 0):.2f}
- Средний убыток: ${metrics.get('avg_loss', 0):.2f}
- Максимальная прибыль: ${metrics.get('largest_win', 0):.2f}
- Максимальный убыток: ${metrics.get('largest_loss', 0):.2f}
- Средняя длительность: {metrics.get('avg_duration_hours', 0):.1f} часов

ДОПОЛНИТЕЛЬНО:
- Общая комиссия: ${metrics.get('total_commission', 0):.2f}
- Время в просадке: {metrics.get('underwater_percent', 0):.1f}%
- Макс. последовательных выигрышей: {metrics.get('max_consecutive_wins', 0)}
- Макс. последовательных проигрышей: {metrics.get('max_consecutive_losses', 0)}
"""
        
        return report