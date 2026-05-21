"""噪声分布分析模块"""

import numpy as np
from typing import Tuple


def analyze_noise_distribution(image_array: np.ndarray) -> dict:
    """分析图像的噪声分布特征

    AI 生成图像的噪声分布与真实相机拍摄图像不同：
    - 真实图像：泊松-高斯混合噪声，与光照强度相关
    - AI 图像：噪声分布不自然，平滑区域噪声异常低

    Args:
        image_array: 灰度图像数组 (H, W), uint8

    Returns:
        噪声特征字典
    """
    gray = image_array.astype(np.float64)
    if gray.ndim > 2:
        gray = np.mean(gray, axis=2)

    h, w = gray.shape

    # 使用局部方差分析噪声
    kernel_size = 5
    local_vars = []

    for y in range(0, h - kernel_size, kernel_size):
        for x in range(0, w - kernel_size, kernel_size):
            block = gray[y:y + kernel_size, x:x + kernel_size]
            local_vars.append(np.var(block))

    if not local_vars:
        return {"warning": "图像太小，无法分析噪声"}

    local_vars = np.array(local_vars)

    # 统计局部方差分布
    mean_var = float(np.mean(local_vars))
    std_var = float(np.std(local_vars))
    median_var = float(np.median(local_vars))

    # 方差-均值比（泊松噪声的特征比值）
    if mean_var > 0:
        var_mean_ratio = std_var / mean_var
    else:
        var_mean_ratio = 0.0

    # 低方差区域比例（AI 图像通常有大面积异常平滑区域）
    low_var_threshold = np.percentile(local_vars, 10)
    low_var_ratio = float(np.mean(local_vars < low_var_threshold * 0.5))

    # 方差分布的偏度（真实图像的偏度通常为正）
    if std_var > 0:
        skewness = float(np.mean(((local_vars - mean_var) / std_var) ** 3))
    else:
        skewness = 0.0

    # 方差分布的峰度
    if std_var > 0:
        kurtosis = float(np.mean(((local_vars - mean_var) / std_var) ** 4) - 3)
    else:
        kurtosis = 0.0

    return {
        "mean_variance": mean_var,
        "std_variance": std_var,
        "median_variance": median_var,
        "var_mean_ratio": var_mean_ratio,
        "low_variance_ratio": low_var_ratio,
        "skewness": skewness,
        "kurtosis": kurtosis,
    }


def noise_anomaly_score(noise_features: dict) -> Tuple[float, str]:
    """根据噪声特征计算异常分数

    Returns:
        (异常分数 0-1, 描述)
    """
    score = 0.0
    signals = []

    # 大面积异常平滑区域
    low_var_ratio = noise_features.get("low_variance_ratio", 0)
    if low_var_ratio > 0.15:
        score += 0.3
        signals.append(f"大面积异常平滑区域 ({low_var_ratio:.1%})")
    elif low_var_ratio > 0.08:
        score += 0.15
        signals.append(f"平滑区域偏多 ({low_var_ratio:.1%})")

    # 方差-均值比异常
    ratio = noise_features.get("var_mean_ratio", 0)
    if ratio < 0.3:
        score += 0.2
        signals.append(f"噪声强度-均值比异常低 ({ratio:.3f})")
    elif ratio > 2.0:
        score += 0.15
        signals.append(f"噪声强度-均值比异常高 ({ratio:.3f})")

    # 偏度异常（真实图像偏度通常 1-5）
    skew = noise_features.get("skewness", 0)
    if skew < 0:
        score += 0.2
        signals.append(f"噪声分布偏度异常 ({skew:.2f})")

    return min(score, 1.0), "; ".join(signals) if signals else "噪声分布正常"
