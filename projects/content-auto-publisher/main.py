"""
Content Auto-Publisher - 入口文件
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='Content Auto-Publisher - 自动化社交媒体内容管理系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py adapt content/my-post.md output/
  python main.py schedule content/
  python main.py analytics
  python main.py demo
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # adapt 命令
    adapt_parser = subparsers.add_parser('adapt', help='生成各平台适配版本')
    adapt_parser.add_argument('content', help='内容文件路径')
    adapt_parser.add_argument('output', help='输出目录')
    
    # schedule 命令
    schedule_parser = subparsers.add_parser('schedule', help='启动定时发布调度器')
    schedule_parser.add_argument('content_dir', nargs='?', default='content', help='内容目录')
    
    # analytics 命令
    subparsers.add_parser('analytics', help='查看数据分析报告')
    
    # demo 命令
    subparsers.add_parser('demo', help='运行演示')
    
    args = parser.parse_args()
    
    if args.command == 'adapt':
        from adapter import generate_platform_versions
        results = generate_platform_versions(args.content, args.output)
        print(f"\n✅ 已生成 {len(results)} 个平台版本:")
        for platform, path in results.items():
            print(f"   📄 {platform} → {path}")
    
    elif args.command == 'schedule':
        from scheduler import ContentScheduler
        scheduler = ContentScheduler()
        scheduler.load_from_content(args.content_dir)
        scheduler.start()
    
    elif args.command == 'analytics':
        from analytics import AnalyticsDashboard
        dashboard = AnalyticsDashboard()
        dashboard.get_weekly_report()
        best = dashboard.get_best_platform()
        print(f"\n🏆 最佳平台: {best}")
        rates = dashboard.get_engagement_rate()
        if rates:
            print(f"\n📈 各平台互动率:")
            for platform, rate in rates.items():
                print(f"   {platform}: {rate:.2%}")
        dashboard.close()
    
    elif args.command == 'demo':
        print("🎬 Content Auto-Publisher 演示")
        print("=" * 50)
        
        # 演示 adapter
        print("\n📝 步骤 1: 内容适配")
        print("   读取 Markdown + YAML 格式的内容...")
        print("   自动生成公众号/知乎/小红书/微博版本...")
        
        # 演示 scheduler
        print("\n⏰ 步骤 2: 定时发布")
        print("   按各平台最佳时间加入发布队列...")
        print("   到时间自动发布...")
        
        # 演示 analytics
        print("\n📊 步骤 3: 数据分析")
        print("   汇总各平台阅读/点赞/评论数据...")
        print("   生成周报，找出最佳平台...")
        
        print("\n✨ 演示完成！更多信息请查看 README.md")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
