"""
Интерактивный визуализатор графиков для стратегии "Охота за ликвидностью"
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import json

class ChartVisualizer:
    """
    Класс для создания интерактивных графиков с разметкой POI и зон ликвидности
    """
    
    def __init__(self, theme: str = "dark"):
        """
        Инициализация визуализатора
        
        Args:
            theme: Тема оформления ("dark" или "light")
        """
        self.theme = theme
        self.colors = self._get_color_scheme()
        
    def _get_color_scheme(self) -> Dict[str, str]:
        """Получение цветовой схемы в зависимости от темы"""
        
        if self.theme == "dark":
            return {
                'background': '#1e1e1e',
                'paper': '#2d2d2d',
                'text': '#ffffff',
                'grid': '#404040',
                'bullish': '#00ff88',
                'bearish': '#ff4444',
                'volume': '#666666',
                # Ликвидность
                'bsl': '#ff6b6b',  # Buy Side Liquidity - красный
                'ssl': '#4ecdc4',  # Sell Side Liquidity - голубой  
                'liquidity_zone': 'rgba(255, 107, 107, 0.1)',
                # POI
                'order_block_bull': 'rgba(0, 255, 136, 0.2)',
                'order_block_bear': 'rgba(255, 68, 68, 0.2)',
                'imbalance': 'rgba(255, 255, 0, 0.3)',
                'support_resistance': '#9b59b6',
                # Сигналы
                'buy_signal': '#00ff00',
                'sell_signal': '#ff0000',
                'entry_zone': 'rgba(0, 255, 0, 0.1)'
            }
        else:
            return {
                'background': '#ffffff',
                'paper': '#fafafa', 
                'text': '#000000',
                'grid': '#e0e0e0',
                'bullish': '#26a69a',
                'bearish': '#ef5350',
                'volume': '#90a4ae',
                'bsl': '#e74c3c',
                'ssl': '#3498db',
                'liquidity_zone': 'rgba(231, 76, 60, 0.1)',
                'order_block_bull': 'rgba(38, 166, 154, 0.2)',
                'order_block_bear': 'rgba(239, 83, 80, 0.2)',
                'imbalance': 'rgba(255, 193, 7, 0.3)',
                'support_resistance': '#9c27b0',
                'buy_signal': '#4caf50',
                'sell_signal': '#f44336',
                'entry_zone': 'rgba(76, 175, 80, 0.1)'
            }
    
    def create_comprehensive_chart(self, 
                                 data: pd.DataFrame,
                                 analysis_results: Dict[str, Any],
                                 signals: List[Dict] = None,
                                 title: str = "Liquidity Hunt Analysis") -> go.Figure:
        """
        Создание комплексного графика с полной разметкой
        
        Args:
            data: OHLCV данные
            analysis_results: Результаты анализа (swing_points, liquidity, POI)
            signals: Торговые сигналы
            title: Заголовок графика
            
        Returns:
            Plotly Figure объект
        """
        
        # Создание субплотов
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=('Price Action & Analysis', 'Volume', 'RSI'),
            row_heights=[0.7, 0.2, 0.1]
        )
        
        # 1. Основной график - свечи
        self._add_candlestick_chart(fig, data, row=1)
        
        # 2. Разметка свинг-точек
        if 'swing_points' in analysis_results:
            self._add_swing_points(fig, analysis_results['swing_points'], row=1)
        
        # 3. Зоны ликвидности
        if 'liquidity_zones' in analysis_results:
            self._add_liquidity_zones(fig, analysis_results['liquidity_zones'], row=1)
        
        # 4. Зоны интереса (POI)
        if 'order_blocks' in analysis_results:
            self._add_order_blocks(fig, analysis_results['order_blocks'], row=1)
        
        if 'imbalances' in analysis_results:
            self._add_imbalances(fig, analysis_results['imbalances'], row=1)
        
        if 'support_resistance' in analysis_results:
            self._add_support_resistance(fig, analysis_results['support_resistance'], row=1)
        
        # 5. Торговые сигналы
        if signals:
            self._add_trading_signals(fig, signals, row=1)
        
        # 6. Объемы
        self._add_volume_chart(fig, data, row=2)
        
        # 7. RSI индикатор
        self._add_rsi_indicator(fig, data, row=3)
        
        # 8. Оформление
        self._apply_chart_styling(fig, title)
        
        return fig
    
    def _add_candlestick_chart(self, fig: go.Figure, data: pd.DataFrame, row: int):
        """Добавление свечного графика"""
        
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name="OHLC",
                increasing_line_color=self.colors['bullish'],
                decreasing_line_color=self.colors['bearish'],
                increasing_fillcolor=self.colors['bullish'],
                decreasing_fillcolor=self.colors['bearish']
            ),
            row=row, col=1
        )
    
    def _add_swing_points(self, fig: go.Figure, swing_points: List[Dict], row: int):
        """Добавление свинг-точек"""
        
        swing_highs_x = []
        swing_highs_y = []
        swing_lows_x = []
        swing_lows_y = []
        
        for point in swing_points:
            if point['type'] == 'high':
                swing_highs_x.append(point['timestamp'])
                swing_highs_y.append(point['price'])
            else:
                swing_lows_x.append(point['timestamp'])
                swing_lows_y.append(point['price'])
        
        # Свинг-максимумы
        if swing_highs_x:
            fig.add_trace(
                go.Scatter(
                    x=swing_highs_x,
                    y=swing_highs_y,
                    mode='markers',
                    marker=dict(
                        symbol='triangle-down',
                        size=10,
                        color=self.colors['bearish'],
                        line=dict(width=1, color='white')
                    ),
                    name='Swing Highs',
                    hovertemplate='Swing High<br>Price: %{y}<br>Time: %{x}<extra></extra>'
                ),
                row=row, col=1
            )
        
        # Свинг-минимумы
        if swing_lows_x:
            fig.add_trace(
                go.Scatter(
                    x=swing_lows_x,
                    y=swing_lows_y,
                    mode='markers',
                    marker=dict(
                        symbol='triangle-up',
                        size=10,
                        color=self.colors['bullish'],
                        line=dict(width=1, color='white')
                    ),
                    name='Swing Lows',
                    hovertemplate='Swing Low<br>Price: %{y}<br>Time: %{x}<extra></extra>'
                ),
                row=row, col=1
            )
    
    def _add_liquidity_zones(self, fig: go.Figure, liquidity_zones: List[Dict], row: int):
        """Добавление зон ликвидности"""
        
        for i, zone in enumerate(liquidity_zones):
            zone_type = zone.get('type', 'unknown')
            color = self.colors['bsl'] if zone_type == 'BSL' else self.colors['ssl']
            
            # Горизонтальная линия для уровня ликвидности
            fig.add_hline(
                y=zone['price'],
                line=dict(
                    color=color,
                    width=2,
                    dash='dash'
                ),
                annotation_text=f"{zone_type}: {zone['strength']:.1f}",
                annotation_position="top right",
                row=row, col=1
            )
            
            # Зона вокруг уровня ликвидности
            if 'range' in zone:
                fig.add_shape(
                    type="rect",
                    x0=zone.get('start_time', fig.data[0].x[0]),
                    x1=zone.get('end_time', fig.data[0].x[-1]),
                    y0=zone['price'] - zone['range'],
                    y1=zone['price'] + zone['range'],
                    fillcolor=self.colors['liquidity_zone'],
                    opacity=0.3,
                    line_width=0,
                    row=row, col=1
                )
    
    def _add_order_blocks(self, fig: go.Figure, order_blocks: List[Dict], row: int):
        """Добавление Order Blocks"""
        
        for i, ob in enumerate(order_blocks):
            color = (self.colors['order_block_bull'] if ob['direction'] == 'bullish' 
                    else self.colors['order_block_bear'])
            
            # Прямоугольник Order Block
            fig.add_shape(
                type="rect",
                x0=ob['start_time'],
                x1=ob['end_time'],
                y0=ob['low'],
                y1=ob['high'],
                fillcolor=color,
                opacity=0.4,
                line=dict(color=color.replace('0.2', '0.8'), width=1),
                name=f"OB {ob['direction']}"
            )
            
            # Аннотация
            fig.add_annotation(
                x=ob['start_time'],
                y=(ob['high'] + ob['low']) / 2,
                text=f"OB-{ob['direction'][0].upper()}",
                showarrow=False,
                font=dict(size=10, color=self.colors['text']),
                bgcolor=color,
                bordercolor=color.replace('0.2', '1.0'),
                borderwidth=1
            )
    
    def _add_imbalances(self, fig: go.Figure, imbalances: List[Dict], row: int):
        """Добавление Fair Value Gaps (Imbalances)"""
        
        for i, gap in enumerate(imbalances):
            fig.add_shape(
                type="rect",
                x0=gap['start_time'],
                x1=gap['end_time'],
                y0=gap['low'],
                y1=gap['high'],
                fillcolor=self.colors['imbalance'],
                opacity=0.3,
                line=dict(color=self.colors['imbalance'].replace('0.3', '0.8'), width=1, dash='dot'),
                name=f"FVG {gap.get('type', 'unknown')}"
            )
            
            # Аннотация
            fig.add_annotation(
                x=gap['start_time'],
                y=(gap['high'] + gap['low']) / 2,
                text="FVG",
                showarrow=False,
                font=dict(size=9, color=self.colors['text']),
                bgcolor=self.colors['imbalance'],
                bordercolor=self.colors['imbalance'].replace('0.3', '1.0'),
                borderwidth=1
            )
    
    def _add_support_resistance(self, fig: go.Figure, sr_levels: List[Dict], row: int):
        """Добавление уровней поддержки/сопротивления"""
        
        for level in sr_levels:
            fig.add_hline(
                y=level['price'],
                line=dict(
                    color=self.colors['support_resistance'],
                    width=1,
                    dash='dashdot'
                ),
                annotation_text=f"S/R: {level['touches']} touches",
                annotation_position="bottom right",
                row=row, col=1
            )
    
    def _add_trading_signals(self, fig: go.Figure, signals: List[Dict], row: int):
        """Добавление торговых сигналов"""
        
        for signal in signals:
            if signal['action'] == 'BUY':
                fig.add_trace(
                    go.Scatter(
                        x=[signal['timestamp']],
                        y=[signal['price']],
                        mode='markers',
                        marker=dict(
                            symbol='triangle-up',
                            size=15,
                            color=self.colors['buy_signal'],
                            line=dict(width=2, color='white')
                        ),
                        name='Buy Signal',
                        hovertemplate=(
                            f"BUY SIGNAL<br>"
                            f"Price: %{{y}}<br>"
                            f"Time: %{{x}}<br>"
                            f"Confidence: {signal.get('confidence', 'N/A')}<br>"
                            f"Reason: {signal.get('reason', 'N/A')}<extra></extra>"
                        )
                    ),
                    row=row, col=1
                )
            
            elif signal['action'] == 'SELL':
                fig.add_trace(
                    go.Scatter(
                        x=[signal['timestamp']],
                        y=[signal['price']],
                        mode='markers',
                        marker=dict(
                            symbol='triangle-down',
                            size=15,
                            color=self.colors['sell_signal'],
                            line=dict(width=2, color='white')
                        ),
                        name='Sell Signal',
                        hovertemplate=(
                            f"SELL SIGNAL<br>"
                            f"Price: %{{y}}<br>"
                            f"Time: %{{x}}<br>"
                            f"Confidence: {signal.get('confidence', 'N/A')}<br>"
                            f"Reason: {signal.get('reason', 'N/A')}<extra></extra>"
                        )
                    ),
                    row=row, col=1
                )
    
    def _add_volume_chart(self, fig: go.Figure, data: pd.DataFrame, row: int):
        """Добавление графика объемов"""
        
        colors = [
            self.colors['bullish'] if close >= open_price 
            else self.colors['bearish']
            for close, open_price in zip(data['close'], data['open'])
        ]
        
        fig.add_trace(
            go.Bar(
                x=data.index,
                y=data['volume'],
                name='Volume',
                marker_color=colors,
                opacity=0.7,
                hovertemplate='Volume: %{y}<br>Time: %{x}<extra></extra>'
            ),
            row=row, col=1
        )
    
    def _add_rsi_indicator(self, fig: go.Figure, data: pd.DataFrame, row: int, period: int = 14):
        """Добавление RSI индикатора"""
        
        # Расчет RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=rsi,
                mode='lines',
                name='RSI',
                line=dict(color=self.colors['text'], width=1),
                hovertemplate='RSI: %{y:.1f}<br>Time: %{x}<extra></extra>'
            ),
            row=row, col=1
        )
        
        # Линии перекупленности/перепроданности
        fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=row, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.3, row=row, col=1)
    
    def _apply_chart_styling(self, fig: go.Figure, title: str):
        """Применение стилизации к графику"""
        
        fig.update_layout(
            title=dict(
                text=title,
                x=0.5,
                font=dict(size=20, color=self.colors['text'])
            ),
            paper_bgcolor=self.colors['paper'],
            plot_bgcolor=self.colors['background'],
            font=dict(color=self.colors['text']),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left", 
                x=0.01,
                bgcolor="rgba(0,0,0,0.5)",
                bordercolor=self.colors['grid'],
                borderwidth=1
            ),
            xaxis=dict(
                gridcolor=self.colors['grid'],
                showgrid=True,
                zeroline=False
            ),
            height=800
        )
        
        # Обновление осей для всех субплотов
        fig.update_xaxes(gridcolor=self.colors['grid'])
        fig.update_yaxes(gridcolor=self.colors['grid'])
        
        # Убираем range selector для чистоты
        fig.update_layout(xaxis_rangeslider_visible=False)
    
    def save_chart(self, fig: go.Figure, filename: str, format: str = "html"):
        """Сохранение графика в файл"""
        
        if format.lower() == "html":
            fig.write_html(filename)
        elif format.lower() == "png":
            fig.write_image(filename)
        elif format.lower() == "json":
            fig.write_json(filename)
        else:
            raise ValueError(f"Неподдерживаемый формат: {format}")
    
    def create_comparison_chart(self, 
                              strategies_data: Dict[str, Dict],
                              title: str = "Strategy Comparison") -> go.Figure:
        """
        Создание графика сравнения стратегий
        
        Args:
            strategies_data: Словарь {название_стратегии: {equity_curve, trades}}
            title: Заголовок графика
        """
        
        fig = go.Figure()
        
        for strategy_name, data in strategies_data.items():
            equity_curve = data['equity_curve']
            
            fig.add_trace(
                go.Scatter(
                    x=equity_curve['timestamp'],
                    y=equity_curve['equity'],
                    mode='lines',
                    name=strategy_name,
                    line=dict(width=2),
                    hovertemplate=f'{strategy_name}<br>Equity: %{{y}}<br>Time: %{{x}}<extra></extra>'
                )
            )
        
        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title="Equity ($)",
            paper_bgcolor=self.colors['paper'],
            plot_bgcolor=self.colors['background'],
            font=dict(color=self.colors['text']),
            showlegend=True
        )
        
        return fig