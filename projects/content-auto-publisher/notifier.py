"""
Content Auto-Publisher - 告警通知模块
支持邮件、Telegram、企业微信等通知方式
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


class Notifier:
    """多通道告警通知器"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
    
    def notify(self, message: str, level: str = 'info', **kwargs):
        """发送通知到所有已启用的通道"""
        icon = {'info': 'ℹ️', 'success': '✅', 'warning': '⚠️', 'error': '❌'}.get(level, 'ℹ️')
        formatted_msg = f"{icon} [{level.upper()}] {message}"
        
        print(formatted_msg)
        
        # 发送邮件通知
        if self.config.get('email', {}).get('enabled'):
            self._send_email(formatted_msg, **kwargs)
        
        # 发送 Telegram 通知
        if self.config.get('telegram', {}).get('enabled'):
            self._send_telegram(formatted_msg, **kwargs)
    
    def _send_email(self, message: str, subject: str = None, **kwargs):
        """发送邮件通知"""
        email_cfg = self.config['email']
        subject = subject or 'Content Auto-Publisher 通知'
        
        msg = MIMEMultipart()
        msg['From'] = email_cfg['username']
        msg['To'] = email_cfg['to']
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain', 'utf-8'))
        
        try:
            server = smtplib.SMTP(email_cfg['smtp_server'], email_cfg['smtp_port'])
            server.starttls()
            server.login(email_cfg['username'], email_cfg['password'])
            server.send_message(msg)
            server.quit()
            print("📧 邮件通知已发送")
        except Exception as e:
            print(f"⚠️ 邮件发送失败: {e}")
    
    def _send_telegram(self, message: str, **kwargs):
        """发送 Telegram 通知"""
        import requests
        
        tg_cfg = self.config['telegram']
        url = f"https://api.telegram.org/bot{tg_cfg['bot_token']}/sendMessage"
        
        try:
            requests.post(url, json={
                'chat_id': tg_cfg['chat_id'],
                'text': message,
                'parse_mode': 'HTML'
            }, timeout=10)
            print("📨 Telegram 通知已发送")
        except Exception as e:
            print(f"⚠️ Telegram 发送失败: {e}")


# 便捷函数
def notify_success(message: str):
    """成功通知"""
    notifier = Notifier()
    notifier.notify(message, level='success')


def notify_error(message: str):
    """错误通知"""
    notifier = Notifier()
    notifier.notify(message, level='error')


if __name__ == '__main__':
    # 测试通知
    config = {
        'email': {'enabled': False},
        'telegram': {'enabled': False}
    }
    notifier = Notifier(config)
    
    notifier.notify("这是一条测试通知", level='info')
    notifier.notify("内容发布成功", level='success')
    notifier.notify("发布失败: API 超时", level='error')
