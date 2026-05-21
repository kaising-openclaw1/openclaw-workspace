#!/usr/bin/env python3
"""DeepfakeGuard Web 界面"""

import argparse
import os
import tempfile
from flask import Flask, render_template_string, request, jsonify

from deepfake_guard import DeepfakeDetector
from deepfake_guard.report import generate_report

app = Flask(__name__)
detector = DeepfakeDetector()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DeepfakeGuard - AI 深度伪造检测</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0f0f23; color: #e0e0e0; min-height: 100vh; }
        .header { background: linear-gradient(135deg, #1a1a3e, #2d1b4e); padding: 30px; text-align: center; }
        .header h1 { font-size: 28px; color: #e94560; margin-bottom: 8px; }
        .header p { color: #aaa; font-size: 14px; }
        .container { max-width: 700px; margin: 0 auto; padding: 30px 20px; }
        .upload-area { border: 2px dashed #444; border-radius: 12px; padding: 40px; text-align: center; cursor: pointer; transition: all 0.3s; background: #1a1a2e; }
        .upload-area:hover { border-color: #e94560; background: #1e1e3a; }
        .upload-area input { display: none; }
        .upload-icon { font-size: 48px; margin-bottom: 16px; }
        .result { margin-top: 20px; padding: 20px; background: #1a1a2e; border-radius: 12px; }
        .result.suspicious { border-left: 4px solid #e94560; }
        .result.warning { border-left: 4px solid #f0ad4e; }
        .result.safe { border-left: 4px solid #5cb85c; }
        .verdict { font-size: 24px; font-weight: bold; margin-bottom: 8px; }
        .score { font-size: 42px; font-weight: bold; margin: 16px 0; }
        .signals { color: #aaa; margin-top: 12px; line-height: 1.8; }
        .loading { text-align: center; padding: 40px; color: #888; }
        .details { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-top: 16px; }
        .detail-card { background: #252540; padding: 12px; border-radius: 8px; text-align: center; }
        .detail-card label { display: block; font-size: 12px; color: #888; margin-bottom: 4px; }
        .detail-card span { font-size: 20px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 DeepfakeGuard</h1>
        <p>AI 深度伪造图像检测工具 · Kai Studio</p>
    </div>
    <div class="container">
        <div class="upload-area" onclick="document.getElementById('fileInput').click()">
            <div class="upload-icon">📷</div>
            <p>点击或拖拽上传图像</p>
            <p style="color:#666; font-size:12px; margin-top:8px">支持 JPG, PNG, BMP, WEBP</p>
            <input type="file" id="fileInput" accept="image/*" onchange="handleUpload(this.files[0])">
        </div>
        <div id="resultArea"></div>
    </div>
    <script>
        function handleUpload(file) {
            if (!file) return;
            const area = document.getElementById('resultArea');
            area.innerHTML = '<div class="loading">🔍 正在分析图像...</div>';
            const fd = new FormData();
            fd.append('image', file);
            fetch('/api/detect', { method: 'POST', body: fd })
                .then(r => r.json())
                .then(data => showResult(data, file.name))
                .catch(e => { area.innerHTML = '<div class="result warning"><p>检测失败: ' + e.message + '</p></div>'; });
        }
        function showResult(data, name) {
            const area = document.getElementById('resultArea');
            const cls = data.fake_probability >= 0.7 ? 'suspicious' : data.fake_probability >= 0.4 ? 'warning' : 'safe';
            const pct = Math.round(data.fake_probability * 100);
            let signals = data.signals ? data.signals.map(s => '• ' + s).join('<br>') : '无明显异常特征';
            area.innerHTML = '<div class="result ' + cls + '">'
                + '<p style="color:#888">' + name + '</p>'
                + '<p class="verdict">' + data.verdict + '</p>'
                + '<div class="score">' + pct + '%</div>'
                + '<p style="color:#888">伪造概率</p>'
                + '<div class="details">'
                + '<div class="detail-card"><label>频域分析</label><span>' + (data.frequency_score * 100).toFixed(0) + '%</span></div>'
                + '<div class="detail-card"><label>EXIF检查</label><span>' + (data.exif_score * 100).toFixed(0) + '%</span></div>'
                + '<div class="detail-card"><label>噪声分析</label><span>' + (data.noise_score * 100).toFixed(0) + '%</span></div>'
                + '</div>'
                + '<div class="signals">' + signals + '</div>'
                + '</div>';
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/detect", methods=["POST"])
def api_detect():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image = request.files["image"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        image.save(tmp.name)
        tmp.flush()
        result = detector.analyze(tmp.name)
    os.unlink(tmp.name)

    return jsonify({
        "filename": image.filename,
        "fake_probability": round(result.fake_probability, 4),
        "anomaly_score": round(result.anomaly_score, 4),
        "verdict": result.verdict,
        "signals": result.signals,
        "frequency_score": round(result.frequency_score, 4),
        "exif_score": round(result.exif_score, 4),
        "noise_score": round(result.noise_score, 4),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DeepfakeGuard Web App")
    parser.add_argument("--port", type=int, default=3000, help="端口号")
    args = parser.parse_args()
    app.run(host="0.0.0.0", port=args.port, debug=True)
