"""
Веб-дашборд для отображения результатов торговой системы в реальном времени
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import time
import threading
from pathlib import Path

from .chart_visualizer import ChartVisualizer


class TradingDashboard:
    """
    Класс для создания веб-дашборда торговой системы
    """
    
    def __init__(self, data_source=None, refresh_interval: int = 30):
        """
        Инициализация дашборда
        
        Args:
            data_source: Источник данных (бот или файлы)
            refresh_interval: Интервал обновления в секундах
        """
        self.data_source = data_source
        self.refresh_interval = refresh_interval
        self.chart_visualizer = ChartVisualizer()
        
        # Настройка Streamlit
        st.set_page_config(
            page_title="Liquidity Hunt Trading Dashboard",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
    def run_dashboard(self):
        """Запуск основного дашборда"""
        
        # Заголовок
        st.title("🎯 Liquidity Hunt Trading Dashboard")
        st.markdown("---")
        
        # Боковая панель управления
        self._render_sidebar()
        
        # Основные метрики
        self._render_key_metrics()
        
        # Основной график
        self._render_main_chart()
        
        # Детальная аналитика
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_trades_table()
            
        with col2:
            self._render_performance_metrics()
        
        # Нижняя секция - дополнительные графики
        self._render_additional_charts()
        
        # Автообновление
        if st.session_state.get('auto_refresh', False):
            time.sleep(self.refresh_interval)
            st.rerun()
    
    def _render_sidebar(self):
        """Отрисовка боковой панели"""
        
        with st.sidebar:
            st.header("⚙️ Настройки")
            
            # Основные настройки
            st.subheader("Основные")
            symbol = st.selectbox("Торговая пара", ["BTCUSDT", "ETHUSDT", "ADAUSDT"])
            timeframe = st.selectbox("Таймфрейм", ["1m", "5m", "15m", "30m", "1h", "4h", "1d"])
            
            # Период данных
            st.subheader("Период")
            period_options = {
                "Последние 24 часа": 1,
                "Последние 3 дня": 3,
                "Последняя неделя": 7,
                "Последний месяц": 30
            }
            selected_period = st.selectbox("Период отображения", list(period_options.keys()))
            
            # Настройки обновления
            st.subheader("Обновление")
            auto_refresh = st.checkbox("Автообновление", value=False)
            refresh_interval = st.slider("Интервал (сек)", 10, 300, 30)
            
            if st.button("🔄 Обновить сейчас"):
                st.rerun()
            
            # Настройки отображения
            st.subheader("Отображение")
            show_liquidity = st.checkbox("Показать ликвидность", value=True)
            show_poi = st.checkbox("Показать POI", value=True)
            show_signals = st.checkbox("Показать сигналы", value=True)
            
            # Сохранение настроек в session_state
            st.session_state.update({
                'symbol': symbol,
                'timeframe': timeframe,
                'period_days': period_options[selected_period],
                'auto_refresh': auto_refresh,
                'refresh_interval': refresh_interval,
                'show_liquidity': show_liquidity,
                'show_poi': show_poi,
                'show_signals': show_signals
            })
    
    def _render_key_metrics(self):
        """Отрисовка ключевых метрик"""
        
        # Получение данных
        metrics = self._get_current_metrics()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total_pnl = metrics.get('total_pnl', 0)
            st.metric(
                "Общий P&L",
                f"${total_pnl:,.2f}",
                delta=f"{metrics.get('pnl_change_24h', 0):+.2f}"
            )
        
        with col2:
            win_rate = metrics.get('win_rate', 0)
            st.metric(
                "Винрейт",
                f"{win_rate:.1f}%",
                delta=f"{metrics.get('win_rate_change', 0):+.1f}%"
            )
        
        with col3:
            total_trades = metrics.get('total_trades', 0)
            st.metric(
                "Всего сделок",
                total_trades,
                delta=metrics.get('trades_today', 0)
            )
        
        with col4:
            current_drawdown = metrics.get('current_drawdown', 0)
            color = "inverse" if current_drawdown > 0 else "normal"
            st.metric(
                "Текущая просадка",
                f"{current_drawdown:.2f}%",
                delta=f"{metrics.get('drawdown_change', 0):+.2f}%"
            )
        
        with col5:
            active_signals = metrics.get('active_signals', 0)
            st.metric(
                "Активные сигналы",
                active_signals,
                delta=metrics.get('new_signals', 0)
            )
    
    def _render_main_chart(self):
        """Отрисовка основного графика"""
        
        st.subheader("📊 Основной график")
        
        # Получение данных
        chart_data = self._get_chart_data()
        
        if chart_data and not chart_data['ohlcv'].empty:
            
            # Создание графика через ChartVisualizer
            fig = self.chart_visualizer.create_comprehensive_chart(
                data=chart_data['ohlcv'],
                analysis_results=chart_data['analysis'],
                signals=chart_data.get('signals', []),
                title=f"{st.session_state.get('symbol', 'BTCUSDT')} - {st.session_state.get('timeframe', '15m')}"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.warning("Нет данных для отображения")
    
    def _render_trades_table(self):
        """Отрисовка таблицы сделок"""
        
        st.subheader("💼 Последние сделки")
        
        trades_data = self._get_recent_trades()
        
        if trades_data:
            df = pd.DataFrame(trades_data)
            
            # Форматирование
            if 'pnl' in df.columns:
                df['pnl'] = df['pnl'].apply(lambda x: f"${x:.2f}" if pd.notnull(x) else "")
            
            if 'entry_time' in df.columns:
                df['entry_time'] = pd.to_datetime(df['entry_time']).dt.strftime('%H:%M:%S')
            
            # Цветовое кодирование P&L
            def color_pnl(val):
                if 'Открыта' in str(val):
                    return 'background-color: #ffeaa7'
                elif val.startswith('$-'):
                    return 'background-color: #fab1a0'
                elif val.startswith('$'):
                    return 'background-color: #a8e6cf'
                return ''
            
            if 'pnl' in df.columns:
                styled_df = df.style.applymap(color_pnl, subset=['pnl'])
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)
        else:
            st.info("Нет данных о сделках")
    
    def _render_performance_metrics(self):
        """Отрисовка метрик производительности"""
        
        st.subheader("📈 Метрики производительности")
        
        metrics = self._get_performance_metrics()
        
        if metrics:
            # График эквити кривой
            if 'equity_curve' in metrics:
                equity_df = pd.DataFrame(metrics['equity_curve'])
                
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=equity_df['timestamp'],
                        y=equity_df['equity'],
                        mode='lines',
                        name='Equity',
                        line=dict(color='#00ff88', width=2)
                    )
                )
                
                fig.update_layout(
                    title="Эквити кривая",
                    xaxis_title="Время",
                    yaxis_title="Капитал ($)",
                    height=300,
                    showlegend=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Ключевые метрики
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Коэф. Шарпа", f"{metrics.get('sharpe_ratio', 0):.3f}")
                st.metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
                st.metric("Макс. просадка", f"{metrics.get('max_drawdown', 0):.2f}%")
            
            with col2:
                st.metric("Общая доходность", f"{metrics.get('total_return', 0):.2f}%")
                st.metric("Средняя прибыль", f"${metrics.get('avg_profit', 0):.2f}")
                st.metric("Средний убыток", f"${metrics.get('avg_loss', 0):.2f}")
        
        else:
            st.info("Нет данных о производительности")
    
    def _render_additional_charts(self):
        """Отрисовка дополнительных графиков"""
        
        st.subheader("🔍 Детальная аналитика")
        
        tab1, tab2, tab3 = st.tabs(["Распределение P&L", "Временной анализ", "Сигналы"])
        
        with tab1:
            self._render_pnl_distribution()
        
        with tab2:
            self._render_time_analysis()
        
        with tab3:
            self._render_signals_analysis()
    
    def _render_pnl_distribution(self):
        """График распределения P&L"""
        
        trades_data = self._get_all_trades()
        
        if trades_data:
            pnl_values = [trade.get('pnl', 0) for trade in trades_data if trade.get('pnl') is not None]
            
            if pnl_values:
                fig = go.Figure(data=[go.Histogram(x=pnl_values, nbinsx=20)])
                fig.update_layout(
                    title="Распределение P&L по сделкам",
                    xaxis_title="P&L ($)",
                    yaxis_title="Количество сделок",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Нет данных о P&L")
        else:
            st.info("Нет данных о сделках")
    
    def _render_time_analysis(self):
        """Временной анализ производительности"""
        
        trades_data = self._get_all_trades()
        
        if trades_data:
            # Анализ по часам
            hourly_pnl = {}
            for trade in trades_data:
                if trade.get('entry_time') and trade.get('pnl') is not None:
                    hour = pd.to_datetime(trade['entry_time']).hour
                    if hour not in hourly_pnl:
                        hourly_pnl[hour] = []
                    hourly_pnl[hour].append(trade['pnl'])
            
            if hourly_pnl:
                hours = list(hourly_pnl.keys())
                avg_pnl = [np.mean(hourly_pnl[hour]) for hour in hours]
                
                fig = go.Figure(data=[go.Bar(x=hours, y=avg_pnl)])
                fig.update_layout(
                    title="Средний P&L по часам дня",
                    xaxis_title="Час",
                    yaxis_title="Средний P&L ($)",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Недостаточно данных для временного анализа")
        else:
            st.info("Нет данных о сделках")
    
    def _render_signals_analysis(self):
        """Анализ сигналов"""
        
        signals_data = self._get_signals_data()
        
        if signals_data:
            # Статистика по типам сигналов
            signal_types = {}
            for signal in signals_data:
                signal_type = signal.get('poi_type', 'Unknown')
                if signal_type not in signal_types:
                    signal_types[signal_type] = {'count': 0, 'confidence': []}
                
                signal_types[signal_type]['count'] += 1
                if signal.get('confidence'):
                    signal_types[signal_type]['confidence'].append(signal['confidence'])
            
            # График типов сигналов
            types = list(signal_types.keys())
            counts = [signal_types[t]['count'] for t in types]
            
            fig = go.Figure(data=[go.Pie(labels=types, values=counts)])
            fig.update_layout(
                title="Распределение типов сигналов",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("Нет данных о сигналах")
    
    def _get_current_metrics(self) -> Dict:
        """Получение текущих метрик"""
        
        if self.data_source:
            # Получение из живого источника данных
            return self.data_source.get_current_metrics()
        else:
            # Получение из файлов результатов
            return self._load_metrics_from_files()
    
    def _get_chart_data(self) -> Dict:
        """Получение данных для графика"""
        
        if self.data_source:
            return self.data_source.get_chart_data(
                symbol=st.session_state.get('symbol', 'BTCUSDT'),
                timeframe=st.session_state.get('timeframe', '15m'),
                period_days=st.session_state.get('period_days', 3)
            )
        else:
            return self._load_chart_data_from_files()
    
    def _get_recent_trades(self) -> List[Dict]:
        """Получение последних сделок"""
        
        if self.data_source:
            return self.data_source.get_recent_trades(limit=10)
        else:
            return self._load_trades_from_files()
    
    def _get_performance_metrics(self) -> Dict:
        """Получение метрик производительности"""
        
        if self.data_source:
            return self.data_source.get_performance_metrics()
        else:
            return self._load_performance_from_files()
    
    def _get_all_trades(self) -> List[Dict]:
        """Получение всех сделок"""
        
        if self.data_source:
            return self.data_source.get_all_trades()
        else:
            return self._load_all_trades_from_files()
    
    def _get_signals_data(self) -> List[Dict]:
        """Получение данных о сигналах"""
        
        if self.data_source:
            return self.data_source.get_signals_data()
        else:
            return self._load_signals_from_files()
    
    def _load_metrics_from_files(self) -> Dict:
        """Загрузка метрик из файлов"""
        
        try:
            results_dir = Path("backtest_results")
            if not results_dir.exists():
                return {}
            
            # Поиск последнего файла метрик
            metric_files = list(results_dir.glob("*_metrics.json"))
            if not metric_files:
                return {}
            
            latest_file = max(metric_files, key=lambda f: f.stat().st_mtime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            st.error(f"Ошибка загрузки метрик: {e}")
            return {}
    
    def _load_chart_data_from_files(self) -> Dict:
        """Загрузка данных графика из файлов"""
        
        # Заглушка - в реальной реализации нужно загружать OHLCV данные
        return {
            'ohlcv': pd.DataFrame(),
            'analysis': {},
            'signals': []
        }
    
    def _load_trades_from_files(self) -> List[Dict]:
        """Загрузка сделок из файлов"""
        
        try:
            results_dir = Path("backtest_results")
            if not results_dir.exists():
                return []
            
            # Поиск последнего файла сделок
            trades_files = list(results_dir.glob("*_trades.json"))
            if not trades_files:
                return []
            
            latest_file = max(trades_files, key=lambda f: f.stat().st_mtime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                trades = json.load(f)
                return sorted(trades, key=lambda x: x.get('entry_time', ''), reverse=True)[:10]
                
        except Exception as e:
            st.error(f"Ошибка загрузки сделок: {e}")
            return []
    
    def _load_performance_from_files(self) -> Dict:
        """Загрузка метрик производительности из файлов"""
        return self._load_metrics_from_files()
    
    def _load_all_trades_from_files(self) -> List[Dict]:
        """Загрузка всех сделок из файлов"""
        
        try:
            results_dir = Path("backtest_results")
            if not results_dir.exists():
                return []
            
            trades_files = list(results_dir.glob("*_trades.json"))
            if not trades_files:
                return []
            
            latest_file = max(trades_files, key=lambda f: f.stat().st_mtime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            st.error(f"Ошибка загрузки всех сделок: {e}")
            return []
    
    def _load_signals_from_files(self) -> List[Dict]:
        """Загрузка сигналов из файлов"""
        # Заглушка - в реальной реализации нужно загружать данные о сигналах
        return []


def main():
    """Основная функция для запуска дашборда"""
    dashboard = TradingDashboard()
    dashboard.run_dashboard()


if __name__ == "__main__":
    main()