"""DeepfakeGuard 使用示例

演示如何使用 DeepfakeGuard 检测 AI 生成图像。
"""

from deepfake_guard import DeepfakeDetector


def demo_single_image():
    """单张图像检测"""
    detector = DeepfakeDetector()

    # 替换为实际图像路径
    image_path = "test_image.jpg"

    print(f"正在分析: {image_path}")
    result = detector.analyze(image_path)

    print(f"\n伪造概率: {result.fake_probability:.1%}")
    print(f"异常分数: {result.anomaly_score:.3f}")
    print(f"判断结果: {result.verdict}")
    print(f"\n分项得分:")
    print(f"  频域分析: {result.frequency_score:.3f}")
    print(f"  EXIF检查: {result.exif_score:.3f}")
    print(f"  噪声分析: {result.noise_score:.3f}")

    if result.signals:
        print(f"\n检测信号:")
        for sig in result.signals:
            print(f"  {sig}")


def demo_batch_scan():
    """批量扫描目录"""
    detector = DeepfakeDetector()

    # 替换为实际目录
    directory = "./input_images/"

    print(f"正在扫描: {directory}")
    results = detector.batch_scan(directory)
    detector.print_report(results)

    # 只看可疑结果
    print("\n--- 仅显示可疑图像 ---")
    detector.print_report(results, suspicious_only=True)


def demo_custom_weights():
    """自定义权重配置"""
    # 如果更关注频域特征（适合艺术风格检测）
    detector = DeepfakeDetector(freq_weight=0.6, exif_weight=0.1, noise_weight=0.3)

    # 如果更关注元数据（适合文件取证）
    # detector = DeepfakeDetector(freq_weight=0.2, exif_weight=0.6, noise_weight=0.2)

    print("使用自定义权重配置")


if __name__ == "__main__":
    demo_single_image()
    # demo_batch_scan()
    # demo_custom_weights()
