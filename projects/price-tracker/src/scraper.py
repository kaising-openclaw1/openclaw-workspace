"""Price Tracker Pro - Core scraper module"""

import time
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
import requests
from bs4 import BeautifulSoup


class PriceScraper:
    """抓取并存储价格数据"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        data_dir = Path(self.config["settings"]["data_dir"])
        data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = data_dir / "prices.db"
        self._init_db()

    def _init_db(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'CNY',
                captured_at TEXT NOT NULL,
                raw_html TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                old_price REAL NOT NULL,
                new_price REAL NOT NULL,
                change_pct REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def scrape_single(self, target: dict) -> Optional[float]:
        """抓取单个目标的价格"""
        headers = {
            "User-Agent": self.config["settings"]["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        max_retries = self.config["settings"]["max_retries"]
        timeout = self.config["settings"]["timeout_seconds"]

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    target["url"], headers=headers, timeout=timeout
                )
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                element = soup.select_one(target["selector"])

                if element:
                    price_text = element.get_text(strip=True)
                    # 提取数字（支持 ¥, $, € 等）
                    price = self._extract_price(price_text)
                    if price:
                        self._save_price(target["name"], target["url"], price, response.text[:500])
                        self._check_alert(target["name"], price, target["notify_threshold"])
                        return price

                print(f"[警告] 未找到价格元素: {target['name']} - {target['selector']}")
                return None

            except Exception as e:
                print(f"[错误] 抓取失败 (尝试 {attempt + 1}/{max_retries}): {target['name']} - {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        return None

    def scrape_all(self) -> dict:
        """抓取所有目标"""
        results = {}
        targets = self.config["targets"]

        for target in targets:
            print(f"\n📡 正在抓取: {target['name']}")
            price = self.scrape_single(target)
            results[target["name"]] = price
            # 礼貌延迟
            time.sleep(2)

        return results

    def _extract_price(self, text: str) -> Optional[float]:
        """从文本中提取价格数字"""
        import re

        # 匹配各种价格格式: ¥1,234.56 / $123.45 / 1234元
        patterns = [
            r"[¥$€£]\s*([\d,]+\.?\d*)",
            r"([\d,]+\.?\d*)\s*元",
            r"([\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1).replace(",", ""))

        return None

    def _save_price(self, name: str, url: str, price: float, raw_html: str = ""):
        """保存价格到数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO prices (name, url, price, captured_at, raw_html) VALUES (?, ?, ?, ?, ?)",
            (name, url, price, datetime.now().isoformat(), raw_html),
        )
        conn.commit()
        conn.close()
        print(f"  ✅ {name}: ¥{price:.2f}")

    def _check_alert(self, name: str, new_price: float, threshold: float):
        """检查价格变动是否超过阈值"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT price FROM prices WHERE name = ? ORDER BY captured_at DESC LIMIT 1 OFFSET 1",
            (name,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            old_price = row[0]
            change_pct = ((new_price - old_price) / old_price) * 100

            if abs(change_pct) >= threshold:
                direction = "📈 上涨" if change_pct > 0 else "📉 下降"
                print(f"  {direction} {name}: ¥{old_price:.2f} → ¥{new_price:.2f} ({change_pct:+.1f}%)")

                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    "INSERT INTO price_alerts (name, old_price, new_price, change_pct, created_at) VALUES (?, ?, ?, ?, ?)",
                    (name, old_price, new_price, round(change_pct, 2), datetime.now().isoformat()),
                )
                conn.commit()
                conn.close()

    def get_history(self, name: str, days: int = 30) -> list:
        """获取价格历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT price, captured_at FROM prices WHERE name = ? ORDER BY captured_at DESC LIMIT ?",
            (name, days * 4),  # 假设每天4次
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
