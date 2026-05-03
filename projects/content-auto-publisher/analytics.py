"""
Content Auto-Publisher - 数据分析模块
跨平台效果数据汇总与分析
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


class AnalyticsDashboard:
    """跨平台数据分析仪表盘"""
    
    def __init__(self, db_path: str = 'analytics.db'):
        self.db_path = db_path
        self.db = sqlite3.connect(db_path)
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据库表"""
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                title TEXT NOT NULL,
                publish_time DATETIME NOT NULL,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS publish_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.db.commit()
    
    def record_metrics(self, platform: str, title: str,
                       views: int = 0, likes: int = 0,
                       comments: int = 0, shares: int = 0):
        """记录单篇内容的效果数据"""
        self.db.execute('''
            INSERT INTO posts (platform, title, publish_time, views, likes, comments, shares)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (platform, title, datetime.now(), views, likes, comments, shares))
        self.db.commit()
    
    def log_publish(self, platform: str, title: str,
                    status: str = 'success', error: str = None):
        """记录发布日志"""
        self.db.execute('''
            INSERT INTO publish_log (platform, title, status, error)
            VALUES (?, ?, ?, ?)
        ''', (platform, title, status, error))
        self.db.commit()
    
    def get_weekly_report(self) -> pd.DataFrame:
        """生成周报"""
        week_ago = datetime.now() - timedelta(days=7)
        
        df = pd.read_sql('''
            SELECT platform, 
                   COUNT(*) as post_count,
                   SUM(views) as total_views,
                   SUM(likes) as total_likes,
                   SUM(comments) as total_comments,
                   ROUND(AVG(views), 1) as avg_views
            FROM posts 
            WHERE publish_time > ?
            GROUP BY platform
        ''', self.db, params=(week_ago,))
        
        if df.empty:
            print("📭 本周暂无数据")
            return df
        
        print("📊 本周数据总览")
        print("=" * 70)
        print(df.to_string(index=False))
        print(f"\n🔥 总阅读: {df['total_views'].sum():,}")
        print(f"❤️  总点赞: {df['total_likes'].sum():,}")
        print(f"💬 总评论: {df['total_comments'].sum():,}")
        
        return df
    
    def get_best_platform(self, days: int = 30) -> str:
        """找出效果最好的平台"""
        cutoff = datetime.now() - timedelta(days=days)
        
        df = pd.read_sql('''
            SELECT platform, 
                   SUM(views + likes + comments) as engagement
            FROM posts 
            WHERE publish_time > ?
            GROUP BY platform
            ORDER BY engagement DESC
            LIMIT 1
        ''', self.db, params=(cutoff,))
        
        if df.empty:
            return "暂无数据"
        return df.iloc[0]['platform']
    
    def get_engagement_rate(self, platform: str = None) -> dict:
        """计算互动率"""
        where = ""
        params = []
        if platform:
            where = "WHERE platform = ?"
            params = [platform]
        
        df = pd.read_sql(f'''
            SELECT platform,
                   SUM(views) as total_views,
                   SUM(likes + comments) as total_engagement
            FROM posts {where}
            GROUP BY platform
        ''', self.db, params=params)
        
        if df.empty:
            return {}
        
        df['engagement_rate'] = df['total_engagement'] / df['total_views']
        return df.set_index('platform')['engagement_rate'].to_dict()
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


if __name__ == '__main__':
    dashboard = AnalyticsDashboard()
    
    # 演示：插入一些测试数据
    demo_data = [
        ('wechat', 'AI自动化如何帮我每周节省15小时', 5234, 312, 45, 23),
        ('zhihu', 'AI自动化如何帮我每周节省15小时', 8900, 567, 89, 34),
        ('xiaohongshu', 'AI自动化如何帮我每周节省15小时', 3200, 234, 28, 12),
        ('wechat', '10个Python脚本帮你每天省2小时', 4500, 289, 38, 19),
        ('zhihu', '10个Python脚本帮你每天省2小时', 7800, 456, 72, 28),
    ]
    
    for platform, title, views, likes, comments, shares in demo_data:
        dashboard.record_metrics(platform, title, views, likes, comments, shares)
    
    # 生成周报
    dashboard.get_weekly_report()
    
    # 找出最佳平台
    best = dashboard.get_best_platform()
    print(f"\n🏆 最佳平台: {best}")
    
    # 计算互动率
    rates = dashboard.get_engagement_rate()
    print(f"\n📈 各平台互动率:")
    for platform, rate in rates.items():
        print(f"   {platform}: {rate:.2%}")
    
    dashboard.close()
