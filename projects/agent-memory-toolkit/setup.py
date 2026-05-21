from setuptools import setup, find_packages

setup(
    name="agent-memory-toolkit",
    version="1.0.0",
    description="Persistent memory system for AI coding agents",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="kaising-openclaw1",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "agent-memory=agent_memory.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
