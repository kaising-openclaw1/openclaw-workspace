from setuptools import setup, find_packages

setup(
    name="deepfake-guard",
    version="1.0.0",
    description="AI 深度伪造图像检测工具",
    author="Kai Studio",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21",
        "pillow>=9.0",
        "piexif>=1.1",
    ],
    extras_require={
        "api": ["fastapi", "uvicorn", "python-multipart"],
        "web": ["flask"],
        "dev": ["pytest", "pytest-cov"],
    },
    entry_points={
        "console_scripts": [
            "deepfake-guard=deepfake_guard.detector:main",
        ],
    },
)
