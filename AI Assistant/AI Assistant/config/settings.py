# config/settings.py
import json
import os

class Settings:

    def __init__(self):
        self.config_file = "config/settings.json"
        self.settings = self.load_settings()

    def load_settings(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_settings(self):
        """保存配置到文件"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4)

    def get(self, key, default=None):
        """获取配置项"""
        return self.settings.get(key, default)

    def update(self, new_settings):
        """更新配置"""
        self.settings.update(new_settings)
        self.save_settings()
        # 添加链接设置
        self.default_settings.update({
            "github_url": "https://github.com/bone-de",
            "website_url": "https://open.api.gu28.top"
        })