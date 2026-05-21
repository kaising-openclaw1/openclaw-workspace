"""EXIF 元数据检查模块"""

from typing import Dict, List, Optional, Tuple

try:
    import piexif
    HAS_PIEXIF = True
except ImportError:
    HAS_PIEXIF = False

# 相机制造商列表（常见品牌）
KNOWN_MANUFACTURERS = {
    "Canon", "Nikon", "Sony", "Fujifilm", "Olympus",
    "Panasonic", "Pentax", "Leica", "Hasselblad", "Sigma",
    "Kodak", "Casio", "Ricoh", "GoPro", "DJI",
    "Apple", "Samsung", "Huawei", "Xiaomi", "Google"
}

# AI 生成工具的软件标签
AI_SOFTWARE_TAGS = {
    "DALL·E", "DALL-E", "Midjourney", "Stable Diffusion",
    "GAN", "Firefly", "Imagen", "SDXL", "ControlNet",
    "ComfyUI", "Automatic1111", "DreamStudio",
    "Adobe Firefly", "Runway", "Pika", "Sora",
    "Kling", "Viggle", "Haiper"
}


def check_exif_metadata(image_path: str) -> dict:
    """检查图像的 EXIF 元数据

    Args:
        image_path: 图像文件路径

    Returns:
        EXIF 检查结果字典
    """
    result = {
        "has_exif": False,
        "manufacturer": None,
        "camera_model": None,
        "software": None,
        "datetime": None,
        "missing_fields": [],
        "ai_signals": [],
        "exif_completeness": 0.0,
        "suspicious": False,
    }

    if not HAS_PIEXIF:
        result["warning"] = "piexif 未安装，跳过 EXIF 检查"
        return result

    try:
        exif_dict = piexif.load(image_path)
    except Exception:
        result["has_exif"] = False
        return result

    result["has_exif"] = True

    # 检查 0th IFD
    if exif_dict.get("0th"):
        zeroth = exif_dict["0th"]

        # 制造商
        if piexif.ImageIFD.Make in zeroth:
            make = zeroth[piexif.ImageIFD.Make]
            if isinstance(make, bytes):
                make = make.decode("utf-8", errors="ignore")
            result["manufacturer"] = make
            if make in KNOWN_MANUFACTURERS:
                result["exif_completeness"] += 0.1

        # 相机型号
        if piexif.ImageIFD.Model in zeroth:
            model = zeroth[piexif.ImageIFD.Model]
            if isinstance(model, bytes):
                model = model.decode("utf-8", errors="ignore")
            result["camera_model"] = model

        # 软件
        if piexif.ImageIFD.Software in zeroth:
            software = zeroth[piexif.ImageIFD.Software]
            if isinstance(software, bytes):
                software = software.decode("utf-8", errors="ignore")
            result["software"] = software
            # 检查是否是 AI 生成工具
            for tag in AI_SOFTWARE_TAGS:
                if tag.lower() in software.lower():
                    result["ai_signals"].append(
                        f"软件标签包含 AI 工具标识: {tag}"
                    )
                    result["suspicious"] = True

        # 日期时间
        if piexif.ImageIFD.DateTime in zeroth:
            dt = zeroth[piexif.ImageIFD.DateTime]
            if isinstance(dt, bytes):
                dt = dt.decode("utf-8", errors="ignore")
            result["datetime"] = dt

    # 检查 Exif IFD
    if exif_dict.get("Exif"):
        exif_data = exif_dict["Exif"]
        if piexif.ExifIFD.DateTimeOriginal in exif_data:
            result["exif_completeness"] += 0.1

    # 评估元数据完整性
    expected_fields = ["manufacturer", "camera_model", "software", "datetime"]
    missing = [f for f in expected_fields if result.get(f) is None]
    result["missing_fields"] = missing

    # 计算完整性分数
    completeness = result["exif_completeness"]
    if len(missing) > 2:
        completeness += max(0, 0.5 - len(missing) * 0.15)

    result["exif_completeness"] = min(completeness, 1.0)

    # 无 EXIF 数据 → 可疑（大多数真实照片有 EXIF）
    if not result["has_exif"]:
        result["suspicious"] = True
        result["ai_signals"].append("缺少 EXIF 元数据")

    return result


def exif_anomaly_score(exif_result: dict) -> Tuple[float, str]:
    """根据 EXIF 检查结果计算异常分数

    Returns:
        (异常分数 0-1, 描述)
    """
    score = 0.0
    signals = []

    # 无 EXIF 数据
    if not exif_result.get("has_exif"):
        score += 0.4
        signals.append("缺少 EXIF 元数据")

    # 元数据不完整
    completeness = exif_result.get("exif_completeness", 1.0)
    if completeness < 0.3:
        score += 0.25
        signals.append(f"元数据不完整 (完整性 {completeness:.0%})")
    elif completeness < 0.5:
        score += 0.1
        signals.append(f"元数据较不完整 (完整性 {completeness:.0%})")

    # 检测到 AI 软件标签
    ai_signals = exif_result.get("ai_signals", [])
    if ai_signals:
        score += 0.5
        signals.extend(ai_signals)

    # 检测到 AI 信号
    if exif_result.get("suspicious"):
        score += 0.2

    return min(score, 1.0), "; ".join(signals) if signals else "EXIF 元数据正常"
