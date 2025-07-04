"""
Система алертов и уведомлений для торговой системы
"""

import smtplib
import json
import asyncio
import websockets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path
import requests


class AlertType(Enum):
    """Типы алертов"""
    SIGNAL = "signal"           # Новый торговый сигнал
    TRADE_OPENED = "trade_opened"    # Открытие позиции  
    TRADE_CLOSED = "trade_closed"    # Закрытие позиции
    PROFIT_TARGET = "profit_target"  # Достижение цели по прибыли
    STOP_LOSS = "stop_loss"         # Срабатывание стоп-лосса
    DRAWDOWN = "drawdown"           # Превышение просадки
    SYSTEM_ERROR = "system_error"   # Системная ошибка
    PERFORMANCE = "performance"     # Отчет о производительности


class AlertPriority(Enum):
    """Приоритеты алертов"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Alert:
    """Класс алерта"""
    id: str
    type: AlertType
    priority: AlertPriority
    title: str
    message: str
    timestamp: datetime
    data: Dict[str, Any] = None
    sent: bool = False
    channels: List[str] = None


class AlertManager:
    """
    Менеджер алертов и уведомлений
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Инициализация менеджера алертов
        
        Args:
            config: Конфигурация (email, telegram, webhook настройки)
        """
        self.config = config or {}
        self.alerts_history: List[Alert] = []
        self.handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
        
        # Регистрация обработчиков
        self._register_handlers()
        
        # Загрузка истории алертов
        self._load_alerts_history()
    
    def _register_handlers(self):
        """Регистрация обработчиков каналов уведомлений"""
        
        self.handlers = {
            'email': self._send_email_alert,
            'telegram': self._send_telegram_alert,
            'webhook': self._send_webhook_alert,
            'file': self._save_to_file,
            'console': self._print_to_console
        }
    
    def create_signal_alert(self, signal_data: Dict) -> Alert:
        """Создание алерта о новом сигнале"""
        
        priority = self._determine_signal_priority(signal_data)
        
        alert = Alert(
            id=f"signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            type=AlertType.SIGNAL,
            priority=priority,
            title=f"🎯 Новый сигнал {signal_data.get('action', 'N/A')}",
            message=self._format_signal_message(signal_data),
            timestamp=datetime.now(),
            data=signal_data,
            channels=['telegram', 'file']
        )
        
        return alert
    
    def create_trade_alert(self, trade_data: Dict, event_type: str) -> Alert:
        """Создание алерта о торговом событии"""
        
        alert_types = {
            'opened': AlertType.TRADE_OPENED,
            'closed': AlertType.TRADE_CLOSED,
            'profit_target': AlertType.PROFIT_TARGET,
            'stop_loss': AlertType.STOP_LOSS
        }
        
        alert_type = alert_types.get(event_type, AlertType.TRADE_OPENED)
        priority = AlertPriority.MEDIUM if event_type == 'opened' else AlertPriority.HIGH
        
        alert = Alert(
            id=f"trade_{event_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            type=alert_type,
            priority=priority,
            title=f"💼 Сделка {self._get_trade_event_title(event_type)}",
            message=self._format_trade_message(trade_data, event_type),
            timestamp=datetime.now(),
            data=trade_data,
            channels=['telegram', 'email', 'file']
        )
        
        return alert
    
    def create_performance_alert(self, metrics: Dict) -> Alert:
        """Создание алерта о производительности"""
        
        priority = self._determine_performance_priority(metrics)
        
        alert = Alert(
            id=f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            type=AlertType.PERFORMANCE,
            priority=priority,
            title="📊 Отчет о производительности",
            message=self._format_performance_message(metrics),
            timestamp=datetime.now(),
            data=metrics,
            channels=['email', 'file']
        )
        
        return alert
    
    def create_system_alert(self, error_message: str, error_data: Dict = None) -> Alert:
        """Создание системного алерта"""
        
        alert = Alert(
            id=f"system_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            type=AlertType.SYSTEM_ERROR,
            priority=AlertPriority.CRITICAL,
            title="🚨 Системная ошибка",
            message=f"Ошибка в системе: {error_message}",
            timestamp=datetime.now(),
            data=error_data or {},
            channels=['telegram', 'email', 'file']
        )
        
        return alert
    
    async def send_alert(self, alert: Alert) -> bool:
        """
        Отправка алерта через все настроенные каналы
        
        Args:
            alert: Алерт для отправки
            
        Returns:
            True если хотя бы один канал сработал успешно
        """
        
        if not alert.channels:
            alert.channels = ['file']  # По умолчанию сохраняем в файл
        
        success_count = 0
        
        for channel in alert.channels:
            try:
                if channel in self.handlers:
                    success = await self.handlers[channel](alert)
                    if success:
                        success_count += 1
                        
            except Exception as e:
                self.logger.error(f"Ошибка отправки алерта через {channel}: {e}")
        
        alert.sent = success_count > 0
        self.alerts_history.append(alert)
        
        # Сохранение истории
        self._save_alerts_history()
        
        return alert.sent
    
    def _determine_signal_priority(self, signal_data: Dict) -> AlertPriority:
        """Определение приоритета сигнала"""
        
        confidence = signal_data.get('confidence', 0)
        confluence_score = signal_data.get('confluence_score', 0)
        
        if confidence >= 0.8 and confluence_score >= 0.7:
            return AlertPriority.HIGH
        elif confidence >= 0.6 and confluence_score >= 0.6:
            return AlertPriority.MEDIUM
        else:
            return AlertPriority.LOW
    
    def _determine_performance_priority(self, metrics: Dict) -> AlertPriority:
        """Определение приоритета алерта производительности"""
        
        max_drawdown = metrics.get('max_drawdown', 0)
        current_drawdown = metrics.get('current_drawdown', 0)
        
        if current_drawdown > 10 or max_drawdown > 15:
            return AlertPriority.HIGH
        elif current_drawdown > 5 or max_drawdown > 10:
            return AlertPriority.MEDIUM
        else:
            return AlertPriority.LOW
    
    def _format_signal_message(self, signal_data: Dict) -> str:
        """Форматирование сообщения о сигнале"""
        
        action = signal_data.get('action', 'N/A')
        symbol = signal_data.get('symbol', 'N/A')
        price = signal_data.get('price', 0)
        confidence = signal_data.get('confidence', 0)
        confluence_score = signal_data.get('confluence_score', 0)
        poi_type = signal_data.get('poi_type', 'N/A')
        reason = signal_data.get('reason', 'N/A')
        
        message = f"""
🎯 НОВЫЙ СИГНАЛ {action.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Пара: {symbol}
💰 Цена: ${price:,.4f}
🎯 Тип POI: {poi_type}
⭐ Уверенность: {confidence:.1%}
🔄 Конфлюенция: {confluence_score:.1%}
📝 Причина: {reason}

⏰ Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}
        """
        
        return message.strip()
    
    def _format_trade_message(self, trade_data: Dict, event_type: str) -> str:
        """Форматирование сообщения о сделке"""
        
        symbol = trade_data.get('symbol', 'N/A')
        direction = trade_data.get('direction', 'N/A')
        size = trade_data.get('size', 0)
        entry_price = trade_data.get('entry_price', 0)
        current_price = trade_data.get('current_price', entry_price)
        pnl = trade_data.get('pnl', 0)
        
        event_titles = {
            'opened': 'ОТКРЫТИЕ ПОЗИЦИИ',
            'closed': 'ЗАКРЫТИЕ ПОЗИЦИИ',
            'profit_target': 'ДОСТИЖЕНИЕ ЦЕЛИ',
            'stop_loss': 'СРАБАТЫВАНИЕ СТОПА'
        }
        
        title = event_titles.get(event_type, 'ТОРГОВОЕ СОБЫТИЕ')
        
        message = f"""
💼 {title}
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Пара: {symbol}
📈 Направление: {direction.upper()}
📦 Размер: {size:,.4f}
💰 Цена входа: ${entry_price:,.4f}
📍 Текущая цена: ${current_price:,.4f}
"""
        
        if event_type in ['closed', 'profit_target', 'stop_loss']:
            pnl_emoji = "💚" if pnl > 0 else "❤️"
            message += f"\n{pnl_emoji} P&L: ${pnl:,.2f}"
        
        message += f"\n\n⏰ Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}"
        
        return message.strip()
    
    def _format_performance_message(self, metrics: Dict) -> str:
        """Форматирование сообщения о производительности"""
        
        total_return = metrics.get('total_return', 0)
        win_rate = metrics.get('win_rate', 0)
        profit_factor = metrics.get('profit_factor', 0)
        max_drawdown = metrics.get('max_drawdown', 0)
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        total_trades = metrics.get('total_trades', 0)
        
        message = f"""
📊 ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Общая доходность: {total_return:.2f}%
🎯 Винрейт: {win_rate:.1f}%
💎 Profit Factor: {profit_factor:.2f}
📉 Макс. просадка: {max_drawdown:.2f}%
⚡ Коэф. Шарпа: {sharpe_ratio:.3f}
🔢 Всего сделок: {total_trades}

⏰ Отчет от: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}
        """
        
        return message.strip()
    
    def _get_trade_event_title(self, event_type: str) -> str:
        """Получение заголовка торгового события"""
        
        titles = {
            'opened': 'открыта',
            'closed': 'закрыта',
            'profit_target': 'достигла цели',
            'stop_loss': 'закрыта по стопу'
        }
        
        return titles.get(event_type, 'обновлена')
    
    async def _send_email_alert(self, alert: Alert) -> bool:
        """Отправка алерта по email"""
        
        try:
            if not self.config.get('email'):
                return False
            
            email_config = self.config['email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['from']
            msg['To'] = email_config['to']
            msg['Subject'] = f"[{alert.priority.name}] {alert.title}"
            
            body = alert.message
            if alert.data:
                body += f"\n\nДополнительные данные:\n{json.dumps(alert.data, indent=2, ensure_ascii=False)}"
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            
            text = msg.as_string()
            server.sendmail(email_config['from'], email_config['to'], text)
            server.quit()
            
            self.logger.info(f"Email алерт отправлен: {alert.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки email: {e}")
            return False
    
    async def _send_telegram_alert(self, alert: Alert) -> bool:
        """Отправка алерта в Telegram"""
        
        try:
            if not self.config.get('telegram'):
                return False
            
            tg_config = self.config['telegram']
            bot_token = tg_config['bot_token']
            chat_id = tg_config['chat_id']
            
            # Форматирование для Telegram
            message = alert.message.replace('━', '━')  # Telegram поддерживает эти символы
            
            # Эмодзи приоритета
            priority_emoji = {
                AlertPriority.LOW: "🟢",
                AlertPriority.MEDIUM: "🟡", 
                AlertPriority.HIGH: "🟠",
                AlertPriority.CRITICAL: "🔴"
            }
            
            emoji = priority_emoji.get(alert.priority, "ℹ️")
            telegram_message = f"{emoji} {message}"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            data = {
                'chat_id': chat_id,
                'text': telegram_message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            self.logger.info(f"Telegram алерт отправлен: {alert.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки Telegram: {e}")
            return False
    
    async def _send_webhook_alert(self, alert: Alert) -> bool:
        """Отправка алерта через webhook"""
        
        try:
            if not self.config.get('webhook'):
                return False
            
            webhook_config = self.config['webhook']
            url = webhook_config['url']
            
            payload = {
                'alert_id': alert.id,
                'type': alert.type.value,
                'priority': alert.priority.name,
                'title': alert.title,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'data': alert.data
            }
            
            headers = webhook_config.get('headers', {})
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            self.logger.info(f"Webhook алерт отправлен: {alert.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки webhook: {e}")
            return False
    
    async def _save_to_file(self, alert: Alert) -> bool:
        """Сохранение алерта в файл"""
        
        try:
            alerts_dir = Path("alerts")
            alerts_dir.mkdir(exist_ok=True)
            
            filename = alerts_dir / f"alerts_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            alert_data = {
                'id': alert.id,
                'type': alert.type.value,
                'priority': alert.priority.name,
                'title': alert.title,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'data': alert.data
            }
            
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(json.dumps(alert_data, ensure_ascii=False) + '\n')
            
            self.logger.info(f"Алерт сохранен в файл: {alert.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения в файл: {e}")
            return False
    
    async def _print_to_console(self, alert: Alert) -> bool:
        """Вывод алерта в консоль"""
        
        try:
            priority_colors = {
                AlertPriority.LOW: "\033[92m",      # Зеленый
                AlertPriority.MEDIUM: "\033[93m",   # Желтый
                AlertPriority.HIGH: "\033[91m",     # Красный
                AlertPriority.CRITICAL: "\033[95m"  # Пурпурный
            }
            
            color = priority_colors.get(alert.priority, "")
            reset = "\033[0m"
            
            print(f"\n{color}{'='*50}")
            print(f"ALERT [{alert.priority.name}]: {alert.title}")
            print(f"{'='*50}{reset}")
            print(alert.message)
            print(f"{color}{'='*50}{reset}\n")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка вывода в консоль: {e}")
            return False
    
    def _load_alerts_history(self):
        """Загрузка истории алертов"""
        
        try:
            history_file = Path("alerts") / "alerts_history.json"
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Восстановление объектов Alert
                for item in data:
                    alert = Alert(
                        id=item['id'],
                        type=AlertType(item['type']),
                        priority=AlertPriority[item['priority']],
                        title=item['title'],
                        message=item['message'],
                        timestamp=datetime.fromisoformat(item['timestamp']),
                        data=item.get('data'),
                        sent=item.get('sent', False),
                        channels=item.get('channels', [])
                    )
                    self.alerts_history.append(alert)
                    
        except Exception as e:
            self.logger.error(f"Ошибка загрузки истории алертов: {e}")
    
    def _save_alerts_history(self):
        """Сохранение истории алертов"""
        
        try:
            alerts_dir = Path("alerts")
            alerts_dir.mkdir(exist_ok=True)
            
            history_file = alerts_dir / "alerts_history.json"
            
            # Конвертация в сериализуемый формат
            data = []
            for alert in self.alerts_history[-1000:]:  # Сохраняем последние 1000 алертов
                data.append({
                    'id': alert.id,
                    'type': alert.type.value,
                    'priority': alert.priority.name,
                    'title': alert.title,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'data': alert.data,
                    'sent': alert.sent,
                    'channels': alert.channels
                })
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"Ошибка сохранения истории алертов: {e}")
    
    def get_alerts_by_type(self, alert_type: AlertType, days: int = 7) -> List[Alert]:
        """Получение алертов по типу за период"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        return [
            alert for alert in self.alerts_history
            if alert.type == alert_type and alert.timestamp >= cutoff_date
        ]
    
    def get_alerts_by_priority(self, priority: AlertPriority, days: int = 7) -> List[Alert]:
        """Получение алертов по приоритету за период"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        return [
            alert for alert in self.alerts_history
            if alert.priority == priority and alert.timestamp >= cutoff_date
        ]
    
    def get_alerts_stats(self, days: int = 30) -> Dict[str, Any]:
        """Получение статистики алертов"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_alerts = [
            alert for alert in self.alerts_history
            if alert.timestamp >= cutoff_date
        ]
        
        stats = {
            'total_alerts': len(recent_alerts),
            'by_type': {},
            'by_priority': {},
            'success_rate': 0
        }
        
        for alert in recent_alerts:
            # По типам
            type_name = alert.type.value
            if type_name not in stats['by_type']:
                stats['by_type'][type_name] = 0
            stats['by_type'][type_name] += 1
            
            # По приоритетам
            priority_name = alert.priority.name
            if priority_name not in stats['by_priority']:
                stats['by_priority'][priority_name] = 0
            stats['by_priority'][priority_name] += 1
        
        # Успешность отправки
        if recent_alerts:
            sent_count = sum(1 for alert in recent_alerts if alert.sent)
            stats['success_rate'] = sent_count / len(recent_alerts) * 100
        
        return stats