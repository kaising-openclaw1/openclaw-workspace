"""检测报告生成模块"""

import os
from typing import List, Optional
from .detector import DetectionResult


def generate_report(
    results: List[DetectionResult],
    output_path: Optional[str] = None,
    title: str = "DeepfakeGuard 检测报告"
) -> str:
    """生成 HTML 格式检测报告

    Args:
        results: 检测结果列表
        output_path: 输出文件路径（None 则返回字符串）
        title: 报告标题

    Returns:
        HTML 报告内容
    """
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='zh-CN'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        f"<title>{title}</title>",
        "<style>",
        "body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }",
        "h1 { color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: 10px; }",
        ".summary { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
        ".result-card { background: white; padding: 16px; border-radius: 8px; margin: 12px 0; border-left: 4px solid #ddd; }",
        ".result-card.suspicious { border-left-color: #e94560; }",
        ".result-card.warning { border-left-color: #f0ad4e; }",
        ".result-card.safe { border-left-color: #5cb85c; }",
        ".score-bar { height: 8px; border-radius: 4px; background: #eee; margin: 8px 0; }",
        ".score-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }",
        ".signals { color: #666; font-size: 14px; margin-top: 8px; }",
        ".verdict { font-weight: bold; font-size: 18px; }",
        ".footer { color: #999; text-align: center; margin-top: 40px; font-size: 12px; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{title}</h1>",
    ]

    # Summary
    total = len(results)
    suspicious = sum(1 for r in results if r.fake_probability >= 0.7)
    warning = sum(1 for r in results if 0.4 <= r.fake_probability < 0.7)
    safe = sum(1 for r in results if r.fake_probability < 0.4)

    html_parts.extend([
        "<div class='summary'>",
        f"<h2>检测摘要</h2>",
        f"<p>共检测 <strong>{total}</strong> 张图像</p>",
        f"<p>⚠️ 疑似 AI 生成: <strong style='color:#e94560'>{suspicious}</strong></p>",
        f"<p>🔶 存在可疑特征: <strong style='color:#f0ad4e'>{warning}</strong></p>",
        f"<p>✅ 未发现异常: <strong style='color:#5cb85c'>{safe}</strong></p>",
        "</div>",
    ])

    # Individual results
    for r in results:
        if r.fake_probability >= 0.7:
            card_class = "suspicious"
            fill_color = "#e94560"
        elif r.fake_probability >= 0.4:
            card_class = "warning"
            fill_color = "#f0ad4e"
        else:
            card_class = "safe"
            fill_color = "#5cb85c"

        html_parts.extend([
            f"<div class='result-card {card_class}'>",
            f"<h3>{os.path.basename(r.image_path)}</h3>",
            f"<p class='verdict'>{r.verdict}</p>",
            f"<p>伪造概率: {r.fake_probability:.1%}</p>",
            f"<div class='score-bar'>",
            f"<div class='score-fill' style='width:{r.fake_probability*100:.1f}%; background:{fill_color}'></div>",
            f"</div>",
            f"<p style='font-size:13px; color:#666'>",
            f"频域: {r.frequency_score:.3f} | EXIF: {r.exif_score:.3f} | 噪声: {r.noise_score:.3f}",
            f"</p>",
        ])

        if r.signals:
            html_parts.append("<div class='signals'>")
            for sig in r.signals:
                html_parts.append(f"<p>• {sig}</p>")
            html_parts.append("</div>")

        html_parts.append("</div>")

    html_parts.extend([
        "<div class='footer'>",
        "<p>由 DeepfakeGuard v1.0.0 生成 · Kai Studio</p>",
        "<p>⚠️ 本报告仅供参考，不适合用作法律证据</p>",
        "</div>",
        "</body>",
        "</html>",
    ])

    html_content = "\n".join(html_parts)

    if output_path:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    return html_content
