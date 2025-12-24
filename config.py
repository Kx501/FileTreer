"""
配置管理模块
负责加载、保存和管理应用程序的配置设置
"""
import json
import os
from pathlib import Path
from typing import List


class Config:
    """配置管理类"""
    
    # 默认配置
    DEFAULT_IGNORE_PATTERNS = [
        '.git',
        '.gitignore',
        '__pycache__',
        '*.pyc',
        'node_modules',
        '.vscode',
        '.idea',
        '.DS_Store'
    ]
    
    def __init__(self, config_dir: Path = None):
        """
        初始化配置，使用默认值
        
        Args:
            config_dir: 配置文件目录，如果为None则使用项目目录
        """
        self.ignore_hidden = True
        self.ignore_patterns: List[str] = self.DEFAULT_IGNORE_PATTERNS.copy()
        self.max_depth = 4  # 默认最大深度为4
        self.max_items_per_level = 15  # 每层最大显示条目数，默认15
        self.unlimit_root_items = True  # 根目录文件数不限制，默认开启
        self.output_format: str = 'ascii'  # 输出格式：'ascii' 或 'markdown'
        
        # 配置文件保存在项目目录下
        if config_dir is None:
            # 获取项目目录（main.py所在目录）
            config_dir = Path(__file__).parent
        self.config_file = config_dir / 'filetreer_config.json'
    
    def to_dict(self) -> dict:
        """将配置转换为字典"""
        return {
            'ignore_hidden': self.ignore_hidden,
            'ignore_patterns': self.ignore_patterns,
            'max_depth': self.max_depth,
            'max_items_per_level': self.max_items_per_level,
            'unlimit_root_items': self.unlimit_root_items,
            'output_format': self.output_format
        }
    
    def from_dict(self, data: dict):
        """从字典加载配置"""
        self.ignore_hidden = data.get('ignore_hidden', True)
        self.ignore_patterns = data.get('ignore_patterns', self.DEFAULT_IGNORE_PATTERNS.copy())
        self.max_depth = data.get('max_depth', 4)
        self.max_items_per_level = data.get('max_items_per_level', 15)
        self.unlimit_root_items = data.get('unlimit_root_items', True)
        output_format = data.get('output_format', 'ascii')
        if output_format in ['ascii', 'markdown']:
            self.output_format = output_format
        else:
            self.output_format = 'ascii'
    
    def save_config(self):
        """保存配置到JSON文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def load_config(self):
        """从JSON文件加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.from_dict(data)
        except Exception as e:
            print(f"加载配置失败: {e}，使用默认配置")
            # 加载失败时使用默认配置，保留 config_file 路径
            config_file_path = self.config_file
            self.__init__(config_file_path.parent)
    
    def get_ignore_patterns_list(self) -> List[str]:
        """获取忽略清单（从字符串解析）"""
        return self.ignore_patterns
    
    def set_ignore_patterns_from_string(self, patterns_str: str):
        """从换行分隔的字符串设置忽略清单（类似.gitignore格式）"""
        if not patterns_str.strip():
            self.ignore_patterns = []
        else:
            # 按行分割，去除空白行和注释行（以#开头的行）
            patterns = []
            for line in patterns_str.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
            # 合并默认模式和用户自定义模式，保持顺序
            # 先添加默认模式，然后添加用户自定义模式（去重）
            all_patterns = list(dict.fromkeys(self.DEFAULT_IGNORE_PATTERNS + patterns))
            self.ignore_patterns = all_patterns
    
    def get_ignore_patterns_string(self) -> str:
        """获取忽略清单字符串（换行分隔）"""
        return '\n'.join(self.ignore_patterns)

