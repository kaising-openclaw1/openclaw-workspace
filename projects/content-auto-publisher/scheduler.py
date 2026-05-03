"""
Content Auto-Publisher - 定时发布调度器
基于 APScheduler 实现内容定时发布
"""

import sys
import yaml
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler


class ContentScheduler:
    """内容发布调度器"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        self.scheduler = BlockingScheduler()
        self.config = self._load_config(config_path)
        self.queue = []
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"⚠️ 配置文件 {config_path} 不存在，使用默认配置")
            return {'platforms': {}}
    
    def add_content(self, content_path: str, platform: str,
                    publish_time: datetime):
        """添加内容到发布队列"""
        self.queue.append({
            'path': content_path,
            'platform': platform,
            'publish_at': publish_time,
            'status': 'pending',
            'added_at': datetime.now()
        })
        print(f"📌 已加入队列: {platform} - {content_path} @ {publish_time}")
    
    def setup_schedule(self):
        """根据队列设置定时任务"""
        for item in self.queue:
            job_id = f"{item['platform']}_{item['path'].replace('/', '_')}"
            self.scheduler.add_job(
                self.publish_content,
                'date',
                run_date=item['publish_at'],
                args=[item],
                id=job_id,
                replace_existing=True
            )
    
    def publish_content(self, item: dict):
        """执行发布（核心逻辑）"""
        try:
            print(f"🚀 开始发布: {item['platform']} - {item['path']}")
            # TODO: 实际发布到平台的 API 调用
            # publisher = self._get_publisher(item['platform'])
            # result = publisher.publish(item['path'])
            
            item['status'] = 'published'
            item['published_at'] = datetime.now()
            self._notify(f"✅ {item['platform']} 发布成功: {item['path']}")
            print(f"✅ {item['platform']} 发布成功")
        except Exception as e:
            item['status'] = 'failed'
            item['error'] = str(e)
            self._notify(f"❌ {item['platform']} 发布失败: {item['path']} - {e}")
            print(f"❌ {item['platform']} 发布失败: {e}")
    
    def _notify(self, message: str):
        """发送通知"""
        print(f"🔔 通知: {message}")
        # TODO: 发送邮件/Telegram/微信通知
    
    def load_from_content(self, content_dir: str = 'content'):
        """从 content 目录的 YAML front matter 中读取发布计划"""
        from pathlib import Path
        from adapter import parse_content
        
        content_path = Path(content_dir)
        if not content_path.exists():
            print(f"⚠️ 内容目录 {content_dir} 不存在")
            return
        
        for md_file in content_path.glob('*.md'):
            try:
                meta = parse_content(str(md_file))
                if 'schedule' in meta:
                    for platform, time_str in meta['schedule'].items():
                        publish_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                        self.add_content(str(md_file), platform, publish_time)
            except Exception as e:
                print(f"⚠️ 解析 {md_file} 失败: {e}")
    
    def start(self):
        """启动调度器"""
        print(f"📅 调度器启动，{len(self.queue)} 个任务待执行")
        if self.queue:
            self.setup_schedule()
            self.scheduler.start()
        else:
            print("📭 没有待发布的任务")


if __name__ == '__main__':
    scheduler = ContentScheduler()
    
    # 从 content 目录加载发布计划
    if len(sys.argv) > 1:
        scheduler.load_from_content(sys.argv[1])
    else:
        scheduler.load_from_content()
    
    # 启动调度器
    scheduler.start()
