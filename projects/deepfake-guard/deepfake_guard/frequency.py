"""频域分析模块 - DCT 系数异常检测"""

import numpy as np
from typing import Tuple


def compute_dct_2d(block: np.ndarray) -> np.ndarray:
    """对 8x8 块计算二维 DCT"""
    N = block.shape[0]
    result = np.zeros_like(block, dtype=np.float64)

    # 一维 DCT 基函数
    for k in range(N):
        for n in range(N):
            weight = 1.0 if k == 0 else np.sqrt(2)
            result[k, n] = weight * np.cos((2 * n + 1) * k * np.pi / (2 * N))

    # 二维 DCT: R * block * R^T
    return result @ block @ result.T


def analyze_frequency(image_array: np.ndarray) -> dict:
    """分析图像的频域特征

    Args:
        image_array: 灰度图像数组 (H, W), uint8

    Returns:
        频域特征字典
    """
    gray = image_array.astype(np.float64)
    if gray.ndim > 2:
        gray = np.mean(gray, axis=2)

    h, w = gray.shape
    block_size = 8

    # 分块计算 DCT 系数
    n_blocks_h = h // block_size
    n_blocks_w = w // block_size

    dct_coeffs = np.zeros((n_blocks_h, n_blocks_w, block_size, block_size))

    for i in range(n_blocks_h):
        for j in range(n_blocks_w):
            block = gray[
                i * block_size: (i + 1) * block_size,
                j * block_size: (j + 1) * block_size
            ]
            dct_coeffs[i, j] = compute_dct_2d(block)

    # 分析高频系数分布 (排除 DC 分量)
    high_freq = dct_coeffs[:, :, 1:, 1:]  # 去掉 DC
    high_freq_abs = np.abs(high_freq)

    # 统计指标
    mean_hf = float(np.mean(high_freq_abs))
    std_hf = float(np.std(high_freq_abs))

    # 高频/低频能量比
    dc_energy = np.mean(np.abs(dct_coeffs[:, :, 0, 0]))
    ac_energy = mean_hf
    energy_ratio = ac_energy / (dc_energy + 1e-10)

    # 系数直方图均匀度（AI 生成图像往往系数分布更均匀）
    all_ac = high_freq_abs.flatten()
    if len(all_ac) > 0:
        hist, _ = np.histogram(all_ac, bins=32, range=(0, np.percentile(all_ac, 99)))
        hist_norm = hist / (hist.sum() + 1e-10)
        # 计算熵
        entropy = -np.sum(hist_norm * np.log(hist_norm + 1e-10))
        max_entropy = np.log(32)
        uniformity = float(entropy / max_entropy) if max_entropy > 0 else 0.0
    else:
        entropy = 0.0
        uniformity = 0.0

    return {
        "mean_high_freq": mean_hf,
        "std_high_freq": std_hf,
        "energy_ratio": energy_ratio,
        "coefficient_entropy": entropy,
        "uniformity": uniformity,
        "n_blocks": n_blocks_h * n_blocks_w,
    }


def frequency_anomaly_score(freq_features: dict) -> Tuple[float, str]:
    """根据频域特征计算异常分数

    Returns:
        (异常分数 0-1, 描述)
    """
    score = 0.0
    signals = []

    # 高频能量异常高 → AI 生成特征
    energy_ratio = freq_features["energy_ratio"]
    if energy_ratio > 0.15:
        score += 0.3
        signals.append(f"高频能量异常高 ({energy_ratio:.3f})")
    elif energy_ratio > 0.08:
        score += 0.15
        signals.append(f"高频能量偏高 ({energy_ratio:.3f})")

    # 系数分布过于均匀 → GAN/扩散模型特征
    uniformity = freq_features["uniformity"]
    if uniformity > 0.92:
        score += 0.25
        signals.append(f"系数分布异常均匀 ({uniformity:.3f})")
    elif uniformity > 0.88:
        score += 0.1
        signals.append(f"系数分布较均匀 ({uniformity:.3f})")

    # 标准差异常
    std_hf = freq_features["std_high_freq"]
    if std_hf < 5.0:
        score += 0.15
        signals.append(f"高频标准差过低 ({std_hf:.1f})")

    return min(score, 1.0), "; ".join(signals) if signals else "频域特征正常"
