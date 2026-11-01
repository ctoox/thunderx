"""Configuration management"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """Application configuration"""

    DEFAULT_CONFIG = {
        "max_concurrent_tasks": 3,
        "max_connections_per_task": 8,
        "chunk_size": 1024 * 1024,  # 1MB
        "buffer_size": 8192,
        "max_retries": 5,
        "default_save_path": str(Path.home() / "Downloads" / "ThunderX"),
        "user_agent": "ThunderX/1.0 Download Manager",
        "timeout": 30,
        "enable_p2p": True,
        "p2p_port": 6881,
        "enable_browser_extension": True,
        "browser_port": 9527,
        "speed_limit": 0,  # 0 = unlimited
        "theme": "dark",
        "language": "zh_CN",
    }

    def __init__(self, config_path: Optional[str] = None):
        self._config = self.DEFAULT_CONFIG.copy()
        self._config_path = config_path or self._get_default_config_path()
        self._load()

    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        config_dir = Path.home() / ".thunderx"
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / "config.yaml")

    def _load(self):
        """Load configuration from file"""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    user_config = yaml.safe_load(f) or {}
                    self._config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")

    def save(self):
        """Save configuration to file"""
        try:
            Path(self._config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(self._config, f, default_flow_style=False)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value"""
        self._config[key] = value

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return super().__getattribute__(name)
        return self._config.get(name)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return self._config.copy()
