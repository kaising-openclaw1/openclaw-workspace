"""
Content Auto-Publisher - 测试文件
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAdapter(unittest.TestCase):
    """测试内容格式适配器"""
    
    def setUp(self):
        """创建测试用的临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.content_dir = os.path.join(self.temp_dir, 'content')
        self.output_dir = os.path.join(self.temp_dir, 'output')
        os.makedirs(self.content_dir)
    
    def test_generate_versions(self):
        """测试生成各平台版本"""
        # 创建测试内容文件
        content = '''---
title: "测试文章"
subtitle: "这是副标题"
tags: [测试, Python]
key_points: ["要点1", "要点2"]
---

这是正文内容，包含一些测试用的文字。
'''
        content_path = os.path.join(self.content_dir, 'test.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        from adapter import generate_platform_versions
        results = generate_platform_versions(content_path, self.output_dir)
        
        # 验证所有平台版本都已生成
        self.assertIn('xiaohongshu', results)
        self.assertIn('wechat', results)
        self.assertIn('zhihu', results)
        self.assertIn('weibo', results)
        
        # 验证文件存在
        for path in results.values():
            self.assertTrue(os.path.exists(path))
        
        # 验证小红书版本包含话题标签
        xhs_content = open(results['xiaohongshu'], encoding='utf-8').read()
        self.assertIn('#测试', xhs_content)
        
        # 验证公众号版本包含引导关注
        wechat_content = open(results['wechat'], encoding='utf-8').read()
        self.assertIn('关注我', wechat_content)
    
    def test_parse_content(self):
        """测试内容解析"""
        content = '''---
title: "解析测试"
status: draft
---

正文内容
'''
        content_path = os.path.join(self.content_dir, 'parse-test.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        from adapter import parse_content
        meta = parse_content(content_path)
        
        self.assertEqual(meta['title'], '解析测试')
        self.assertEqual(meta['status'], 'draft')
        self.assertEqual(meta['content'], '正文内容')
        self.assertIn('summary', meta)  # 应自动生成摘要


class TestAnalytics(unittest.TestCase):
    """测试数据分析模块"""
    
    def setUp(self):
        """创建临时数据库"""
        import tempfile
        self.db_path = os.path.join(tempfile.mkdtemp(), 'test.db')
    
    def test_record_and_query(self):
        """测试数据记录和查询"""
        from analytics import AnalyticsDashboard
        
        dashboard = AnalyticsDashboard(self.db_path)
        dashboard.record_metrics('wechat', '测试文章', 1000, 50, 10, 5)
        dashboard.record_metrics('zhihu', '测试文章', 2000, 100, 20, 10)
        
        df = dashboard.get_weekly_report()
        self.assertEqual(len(df), 2)
        
        best = dashboard.get_best_platform()
        self.assertEqual(best, 'zhihu')
        
        dashboard.close()


if __name__ == '__main__':
    unittest.main()
