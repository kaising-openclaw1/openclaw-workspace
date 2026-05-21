"""深度伪造检测核心引擎"""

import os
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from PIL import Image

from .frequency import analyze_frequency, frequency_anomaly_score
from .exif_check import check_exif_metadata, exif_anomaly_score
from .noise_analysis import analyze_noise_distribution, noise_anomaly_score
from .report import generate_report


@dataclass
class DetectionResult:
    """单次检测结果"""
    image_path: str
    fake_probability: float = 0.0
    anomaly_score: float = 0.0
    signals: List[str] = field(default_factory=list)
    frequency_score: float = 0.0
    exif_score: float = 0.0
    noise_score: float = 0.0
    frequency_signals: str = ""
    exif_signals: str = ""
    noise_signals: str = ""
    details: dict = field(default_factory=dict)

    @property
    def verdict(self) -> str:
        """判断结果"""
        if self.fake_probability >= 0.7:
            return "⚠️  疑似 AI 生成"
        elif self.fake_probability >= 0.4:
            return "🔶 存在可疑特征"
        else:
            return "✅ 未发现明显异常"


class DeepfakeDetector:
    """深度伪造检测器

    结合频域分析、EXIF 元数据检查和噪声分布分析，
    对图像进行多维度深度伪造检测。
    """

    def __init__(
        self,
        freq_weight: float = 0.4,
        exif_weight: float = 0.25,
        noise_weight: float = 0.35,
    ):
        """初始化检测器

        Args:
            freq_weight: 频域分析权重
            exif_weight: EXIF 检查权重
            noise_weight: 噪声分析权重
        """
        self.freq_weight = freq_weight
        self.exif_weight = exif_weight
        self.noise_weight = noise_weight

        total = freq_weight + exif_weight + noise_weight
        if abs(total - 1.0) > 0.01:
            self.freq_weight /= total
            self.exif_weight /= total
            self.noise_weight /= total

    def analyze(self, image_path: str) -> DetectionResult:
        """分析单张图像

        Args:
            image_path: 图像文件路径

        Returns:
            DetectionResult 检测结果
        """
        result = DetectionResult(image_path=image_path)

        # 加载图像
        try:
            img = Image.open(image_path)
            img_array = np.array(img)
        except Exception as e:
            result.signals.append(f"无法加载图像: {e}")
            return result

        # 1. 频域分析
        freq_features = analyze_frequency(img_array)
        result.frequency_score, result.frequency_signals = frequency_anomaly_score(
            freq_features
        )

        # 2. EXIF 检查
        exif_result = check_exif_metadata(image_path)
        result.exif_score, result.exif_signals = exif_anomaly_score(exif_result)

        # 3. 噪声分析
        noise_features = analyze_noise_distribution(img_array)
        result.noise_score, result.noise_signals = noise_anomaly_score(noise_features)

        # 综合评分
        result.anomaly_score = (
            self.freq_weight * result.frequency_score
            + self.exif_weight * result.exif_score
            + self.noise_weight * result.noise_score
        )

        # 映射到伪造概率（sigmoid-like 映射）
        result.fake_probability = 1.0 / (
            1.0 + np.exp(-10 * (result.anomaly_score - 0.4))
        )

        # 收集信号
        all_signals = []
        if result.frequency_signals != "频域特征正常":
            all_signals.append(f"[频域] {result.frequency_signals}")
        if result.exif_signals != "EXIF 元数据正常":
            all_signals.append(f"[EXIF] {result.exif_signals}")
        if result.noise_signals != "噪声分布正常":
            all_signals.append(f"[噪声] {result.noise_signals}")
        result.signals = all_signals

        # 详细信息
        result.details = {
            "frequency_features": freq_features,
            "exif_result": exif_result,
            "noise_features": noise_features,
            "weights": {
                "frequency": self.freq_weight,
                "exif": self.exif_weight,
                "noise": self.noise_weight,
            },
        }

        return result

    def batch_scan(self, directory: str, extensions: tuple = None) -> List[DetectionResult]:
        """批量扫描目录中的图像

        Args:
            directory: 扫描目录
            extensions: 支持的扩展名

        Returns:
            检测结果列表
        """
        if extensions is None:
            extensions = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")

        results = []
        for root, _, files in os.walk(directory):
            for fname in sorted(files):
                if fname.lower().endswith(extensions):
                    fpath = os.path.join(root, fname)
                    result = self.analyze(fpath)
                    results.append(result)

        return results

    def print_report(self, results: List[DetectionResult], suspicious_only: bool = False) -> None:
        """打印检测报告"""
        if not results:
            print("未找到可检测的图像文件。")
            return

        if suspicious_only:
            results = [r for r in results if r.fake_probability >= 0.3]
            if not results:
                print("所有图像均未发现明显异常特征。")
                return

        print(f"\n{'='*60}")
        print(f"  DeepfakeGuard 检测报告")
        print(f"  检测数量: {len(results)}")
        print(f"{'='*60}\n")

        suspicious_count = 0
        for r in results:
            if r.fake_probability >= 0.4:
                suspicious_count += 1

            print(f"  文件: {os.path.basename(r.image_path)}")
            print(f"  伪造概率: {r.fake_probability:.1%}  {r.verdict}")
            print(f"  综合异常分数: {r.anomaly_score:.3f}")
            if r.signals:
                for sig in r.signals:
                    print(f"    - {sig}")
            print(f"  分项得分: 频域={r.frequency_score:.3f} | "
                  f"EXIF={r.exif_score:.3f} | 噪声={r.noise_score:.3f}")
            print()

        print(f"{'='*60}")
        print(f"  总结: {suspicious_count}/{len(results)} 张图像存在可疑特征")
        print(f"{'='*60}\n")
