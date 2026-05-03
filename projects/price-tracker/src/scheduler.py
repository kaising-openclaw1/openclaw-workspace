"""Price Tracker Pro - Scheduler module"""

import argparse
from apscheduler.schedulers.blocking import BlockingScheduler
from src.scraper import PriceScraper


def run_check():
    """执行一次价格检查"""
    print(f"\n{'='*50}")
    print(f"🔍 价格检查开始 - {__import__('datetime').datetime.now()}")
    print(f"{'='*50}")

    scraper = PriceScraper()
    results = scraper.scrape_all()

    print(f"\n📊 检查结果汇总:")
    for name, price in results.items():
        if price:
            print(f"  {name}: ¥{price:.2f}")
        else:
            print(f"  {name}: 抓取失败")


def main():
    parser = argparse.ArgumentParser(description="Price Tracker Pro - 定时任务")
    parser.add_argument("--cron", default="0 */6 * * *", help="Cron表达式 (默认: 每6小时)")
    parser.add_argument("--once", action="store_true", help="只执行一次")
    args = parser.parse_args()

    if args.once:
        run_check()
        return

    scheduler = BlockingScheduler()
    scheduler.add_job(run_check, "cron", minute="0", hour="*/6")

    print(f"⏰ 定时任务已启动 - Cron: {args.cron}")
    print("按 Ctrl+C 停止")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n⏹️ 定时任务已停止")


if __name__ == "__main__":
    main()
