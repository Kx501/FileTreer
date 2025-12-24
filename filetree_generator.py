"""
文件树生成器核心模块
负责扫描目录并生成不同格式的文件树
"""
import os
import fnmatch
from pathlib import Path
from typing import List, Tuple, Optional
from config import Config


class FileTreeGenerator:
    """文件树生成器类"""
    
    def __init__(self, config: Config):
        """初始化生成器"""
        self.config = config
        self.file_tree: List[Tuple[str, int, bool]] = []  # (path, depth, is_dir)
    
    def should_ignore(self, path: Path, is_dir: bool = False) -> bool:
        """
        判断是否应该忽略该路径
        
        Args:
            path: 文件或文件夹路径
            is_dir: 是否为目录
            
        Returns:
            True 如果应该忽略，False 否则
        """
        name = path.name
        
        # 检查隐藏文件
        if self.config.ignore_hidden:
            if name.startswith('.'):
                return True
        
        # 检查忽略清单
        ignore_patterns = self.config.get_ignore_patterns_list()
        for pattern in ignore_patterns:
            # 支持通配符匹配
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(path), pattern):
                return True
            # 精确匹配
            if name == pattern:
                return True
        
        return False
    
    def scan_directory(self, root_path: Path, current_depth: int = 0) -> List[Tuple[str, int, bool]]:
        """
        递归扫描目录，在扫描过程中应用每层条目数限制
        
        Args:
            root_path: 要扫描的根目录
            current_depth: 当前深度
            
        Returns:
            文件树列表，每个元素为 (相对路径, 深度, 是否为目录)
        """
        file_tree = []
        
        # 检查最大深度限制
        if self.config.max_depth is not None and current_depth >= self.config.max_depth:
            return file_tree
        
        try:
            # 获取所有条目并排序（目录在前，文件在后）
            entries = []
            for item in root_path.iterdir():
                if not self.should_ignore(item, item.is_dir()):
                    entries.append(item)
            
            # 排序：目录在前，然后按名称排序
            entries.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            # 应用每层条目数限制
            # 如果是根目录且设置了根目录不限制，则不限制
            if current_depth == 0 and self.config.unlimit_root_items:
                entries_to_process = entries
                has_more = False
            elif self.config.max_items_per_level is not None:
                max_items = self.config.max_items_per_level
                entries_to_process = entries[:max_items]
                has_more = len(entries) > max_items
            else:
                # 无限
                entries_to_process = entries
                has_more = False
            
            for entry in entries_to_process:
                relative_path = entry.relative_to(root_path.parent)
                file_tree.append((str(relative_path), current_depth, entry.is_dir()))
                
                # 如果是目录，递归扫描
                if entry.is_dir():
                    sub_tree = self.scan_directory(entry, current_depth + 1)
                    file_tree.extend(sub_tree)
            
            # 如果有更多条目被省略，添加省略号标记
            if has_more:
                file_tree.append(("...", current_depth, False))
        
        except PermissionError:
            # 权限错误，跳过该目录
            pass
        except Exception as e:
            # 其他错误，记录但继续
            print(f"扫描目录 {root_path} 时出错: {e}")
        
        return file_tree
    
    def filter_ellipsis_children(self, file_tree: List[Tuple[str, int, bool]]) -> List[Tuple[str, int, bool]]:
        """
        过滤掉省略号后面的所有子项
        
        Args:
            file_tree: 原始文件树列表
            
        Returns:
            过滤后的文件树列表
        """
        if not file_tree:
            return file_tree
        
        filtered_tree = []
        skip_until_depth = None
        
        for i, (path, depth, is_dir) in enumerate(file_tree):
            if path == "...":
                # 遇到省略号，标记需要跳过后续更深层的项
                filtered_tree.append((path, depth, is_dir))
                skip_until_depth = depth
            elif skip_until_depth is not None:
                # 如果当前项比省略号的深度更深，跳过
                if depth > skip_until_depth:
                    continue
                else:
                    # 遇到同级或更浅的项，停止跳过
                    skip_until_depth = None
                    filtered_tree.append((path, depth, is_dir))
            else:
                filtered_tree.append((path, depth, is_dir))
        
        return filtered_tree
    
    def generate_ascii_tree(self, root_name: str, file_tree: List[Tuple[str, int, bool]]) -> str:
        """
        生成ASCII艺术树格式
        
        Args:
            root_name: 根目录名称
            file_tree: 文件树列表
            
        Returns:
            ASCII格式的文件树字符串
        """
        lines = [root_name + '/']
        
        if not file_tree:
            return '\n'.join(lines)
        
        for i, (path, depth, is_dir) in enumerate(file_tree):
            # 判断是否是当前深度的最后一个条目
            is_last = True
            if i < len(file_tree) - 1:
                # 检查后续是否有相同或更深层级的条目
                for j in range(i + 1, len(file_tree)):
                    next_path, next_depth, _ = file_tree[j]
                    if next_depth == depth:
                        # 找到同级的后续条目
                        is_last = False
                        break
                    elif next_depth < depth:
                        # 遇到更浅的层级，说明当前是最后一个
                        break
            
            # 构建前缀
            prefix = ''
            for d in range(depth):
                # 检查这一层是否有后续条目（同级或子级）
                has_next = False
                for j in range(i + 1, len(file_tree)):
                    next_depth = file_tree[j][1]
                    if next_depth == d:
                        # 找到同级的后续条目
                        has_next = True
                        break
                    elif next_depth < d:
                        # 遇到更浅的层级，停止搜索
                        break
                    # 如果 next_depth > d，继续搜索
                
                if has_next:
                    prefix += '│   '
                else:
                    prefix += '    '
            
            # 添加连接符
            if is_last:
                prefix += '└── '
            else:
                prefix += '├── '
            
            # 添加文件名
            if path == "...":
                name = "..."
            else:
                path_obj = Path(path)
                name = path_obj.name
                if is_dir:
                    name += '/'
            
            lines.append(prefix + name)
        
        return '\n'.join(lines)
    
    def generate_markdown_tree(self, root_name: str, file_tree: List[Tuple[str, int, bool]]) -> str:
        """
        生成Markdown格式的文件树
        
        Args:
            root_name: 根目录名称
            file_tree: 文件树列表
            
        Returns:
            Markdown格式的文件树字符串
        """
        lines = [f'- {root_name}/']
        
        for path, depth, is_dir in file_tree:
            # 计算缩进（每层4个空格）
            indent = '    ' * (depth + 1)
            
            if path == "...":
                name = "..."
            else:
                path_obj = Path(path)
                name = path_obj.name
                if is_dir:
                    name += '/'
            
            lines.append(f'{indent}- {name}')
        
        return '\n'.join(lines)
    
    def generate(self, root_path: Path) -> dict:
        """
        生成文件树（所有格式）
        
        Args:
            root_path: 要扫描的根目录路径
            
        Returns:
            包含不同格式文件树的字典
        """
        # 重置文件树
        self.file_tree = []
        
        # 扫描目录（限制已在扫描过程中应用）
        raw_file_tree = self.scan_directory(root_path, current_depth=0)
        
        # 过滤掉省略号后面的子项
        self.file_tree = self.filter_ellipsis_children(raw_file_tree)
        
        root_name = root_path.name
        
        result = {}
        
        # 根据配置生成相应格式
        if self.config.output_format == 'ascii':
            content = self.generate_ascii_tree(root_name, self.file_tree)
            result['content'] = content
            result['format'] = 'ascii'
        elif self.config.output_format == 'markdown':
            content = self.generate_markdown_tree(root_name, self.file_tree)
            result['content'] = content
            result['format'] = 'markdown'
        else:
            # 默认使用 ASCII 格式
            content = self.generate_ascii_tree(root_name, self.file_tree)
            result['content'] = content
            result['format'] = 'ascii'
        
        # 添加统计信息
        file_count = len([item for item in self.file_tree if not item[2]])  # 文件数量
        dir_count = len([item for item in self.file_tree if item[2]])  # 目录数量
        result['stats'] = {'files': file_count, 'dirs': dir_count}
        
        return result

