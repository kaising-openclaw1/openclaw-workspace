"""Price Tracker Pro - Data export module"""

import argparse
import csv
import json
from datetime import datetime
from src.scraper import PriceScraper


def export_data(fmt: str = "csv", output: str = None):
    """导出数据为 CSV 或 JSON"""
    scraper = PriceScraper()

    if not output:
        output = f"prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{fmt}"

    targets = scraper.config["targets"]
    all_data = []

    for target in targets:
        history = scraper.get_history(target["name"])
        for price, captured_at in history:
            all_data.append({
                "name": target["name"],
                "price": price,
                "currency": "CNY",
                "captured_at": captured_at,
            })

    if fmt == "csv":
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "price", "currency", "captured_at"])
            writer.writeheader()
            writer.writerows(all_data)
    elif fmt == "json":
        with open(output, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"📁 已导出 {len(all_data)} 条记录到 {output}")


def main():
    parser = argparse.ArgumentParser(description="导出价格数据")
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--output", help="输出文件名")
    args = parser.parse_args()
    export_data(args.format, args.output)


if __name__ == "__main__":
    main()
