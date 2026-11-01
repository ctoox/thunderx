from setuptools import setup, find_packages

setup(
    name="thunderx",
    version="1.0.0",
    description="ThunderX - High-speed download manager with P2P acceleration",
    author="ThunderX Team",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.9.0",
        "aiofiles>=23.2.0",
        "tqdm>=4.66.0",
        "click>=8.1.0",
        "rich>=13.7.0",
        "pyyaml>=6.0",
        "filelock>=3.13.0",
        "psutil>=5.9.0",
        "bencodepy>=0.9.5",
        "flask>=3.0.0",
        "flask-cors>=4.0.0",
        "PyQt6>=6.6.0",
    ],
    entry_points={
        "console_scripts": [
            "thunderx=thunderx.cli:main",
            "thunderx-gui=thunderx.ui.gui:main",
        ],
    },
    python_requires=">=3.9",
)
