# DeepfakeGuard - AI 深度伪造检测工具

> 🔍 基于频域分析和 AI 模型的深度伪造（Deepfake）图像检测工具

## 项目概述

DeepfakeGuard 是一个轻量级的深度伪造检测工具，专注于通过频域分析和 EXIF 元数据检测 AI 生成的图像。支持批量检测、API 接口和 Web 界面，适合个人用户和企业安全团队使用。

## 为什么需要深度伪造检测

2026 年，AI 生成图像已经逼真到肉眼难以分辨。Deepfake 技术被广泛用于：
- 伪造新闻图片误导舆论
- 制作虚假身份证明进行诈骗
- 生成虚假证据用于法律纠纷
- 冒充他人进行社交工程攻击

DeepfakeGuard 提供了一层基础防护，帮助用户快速筛查可疑图片。

## 功能特性

- ✅ 频域分析（DCT 系数异常检测）
- ✅ EXIF 元数据完整性检查
- ✅ 图像噪声分布一致性分析
- ✅ 批量检测模式（文件夹扫描）
- ✅ REST API 接口
- ✅ Web 界面（可视化结果展示）
- ✅ 置信度评分 + 热力图标注
- ✅ 零外部模型依赖（纯算法实现）

## 安装

```bash
pip install -r requirements.txt
pip install -e .
```

## 快速使用

### 单张图像检测

```python
from deepfake_guard import DeepfakeDetector

detector = DeepfakeDetector()
result = detector.analyze("suspect_image.jpg")

print(f"伪造概率: {result.fake_probability:.1%}")
print(f"异常分数: {result.anomaly_score:.2f}")
print(f"检测信号: {', '.join(result.signals)}")
```

### 批量检测

```python
from deepfake_guard import DeepfakeDetector

detector = DeepfakeDetector()
results = detector.batch_scan("./input_images/")
detector.print_report(results)
```

### 启动 API 服务

```bash
python api_server.py --port 8080

# API 调用
curl -X POST http://localhost:8080/detect \
  -F "image=@suspect_image.jpg"
```

### 启动 Web 界面

```bash
python web_app.py --port 3000
# 访问 http://localhost:3000
```

## 检测原理

### 1. 频域分析 (DCT)

AI 生成图像在离散余弦变换（DCT）频域中表现出与真实相机拍摄图像不同的系数分布。GAN 和扩散模型在生成过程中会留下独特的频域指纹。

```
真实图像: DCT 系数呈自然衰减
AI 生成图像: DCT 系数在特定频率出现异常峰值
```

### 2. EXIF 元数据检查

AI 生成图像通常缺少完整的 EXIF 数据，或包含不一致的元信息：
- 缺失相机型号、光圈、焦距等参数
- 时间戳异常
- 软件标签暴露生成工具（DALL·E, Midjourney, Stable Diffusion）

### 3. 噪声分布分析

真实照片的噪声遵循物理传感器的泊松-高斯分布。AI 生成图像的噪声分布不自然，特别是在平滑区域和边缘过渡区。

## 项目结构

```
deepfake-guard/
├── deepfake_guard/
│   ├── __init__.py
│   ├── detector.py          # 核心检测引擎
│   ├── frequency.py         # 频域分析模块
│   ├── exif_check.py        # EXIF 元数据检查
│   ├── noise_analysis.py    # 噪声分布分析
│   └── report.py            # 报告生成
├── api_server.py            # REST API 服务
├── web_app.py               # Web 界面
├── examples/
│   └── basic_usage.py       # 使用示例
├── tests/
│   └── test_detector.py     # 测试套件
├── requirements.txt
├── setup.py
└── README.md
```

## 技术栈

- Python 3.8+
- NumPy / SciPy（频域计算）
- Pillow（图像处理）
- piexif（EXIF 读写）
- FastAPI（API 服务）
- Jinja2（Web 模板）

## 局限性

- 基于算法的检测无法覆盖所有 Deepfake 类型
- 对高质量伪造可能产生误判
- 不适合法庭级证据鉴定（需要专业取证工具）
- 建议作为辅助筛查工具，而非唯一判断依据

## 许可证

MIT License

## 作者

Kai Studio

---

💡 **商业价值：** 可为企业、媒体机构、法律团队提供深度伪造检测服务，单次检测定价 ¥50-500，批量检测套餐 ¥2,000-10,000/月。
