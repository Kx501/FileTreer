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
        self.file_tree: List[Tuple[str, int, bool, str, Optional[bool]]] = []  # (path, depth, is_dir, name, has_more_files)
        # 缓存忽略清单，避免重复获取
        self._ignore_patterns = None
        self._ignore_patterns_set = None  # 精确匹配的集合，用于快速查找
    
    def _get_ignore_patterns(self):
        """获取并缓存忽略清单"""
        if self._ignore_patterns is None:
            self._ignore_patterns = self.config.get_ignore_patterns_list()
            # 创建精确匹配的集合，用于快速查找
            # 排除包含通配符的模式和以/结尾的目录匹配模式
            self._ignore_patterns_set = {p for p in self._ignore_patterns 
                                        if '*' not in p and '?' not in p and not p.endswith('/')}
        return self._ignore_patterns, self._ignore_patterns_set
    
    def should_ignore(self, path: Path, is_dir: Optional[bool] = None) -> bool:
        """
        判断是否应该忽略该路径
        
        Args:
            path: 文件或文件夹路径
            is_dir: 是否为目录，如果为None则自动检测
            
        Returns:
            True 如果应该忽略，False 否则
        """
        name = path.name
        
        # 如果未提供 is_dir，尝试检测（但可能不准确，建议在调用时提供）
        if is_dir is None:
            try:
                is_dir = path.is_dir()
            except OSError:
                is_dir = False
        
        # 检查隐藏文件
        if self.config.ignore_hidden and name.startswith('.'):
            return True
        
        # 获取缓存的忽略清单
        ignore_patterns, ignore_patterns_set = self._get_ignore_patterns()
        
        # 先检查精确匹配（这些模式不包含通配符，也不以/结尾）
        if name in ignore_patterns_set:
            return True
        
        # 再检查通配符匹配和目录匹配模式
        for pattern in ignore_patterns:
            if pattern not in ignore_patterns_set:  # 跳过已检查的精确匹配
                # 检查是否为目录匹配模式（以/结尾）
                if pattern.endswith('/'):
                    # 目录匹配模式：只匹配目录
                    if not is_dir:
                        # 当前项不是目录，跳过该模式
                        continue
                    # 去掉末尾的/后进行匹配
                    pattern_without_slash = pattern[:-1]
                    if fnmatch.fnmatch(name, pattern_without_slash) or fnmatch.fnmatch(str(path), pattern_without_slash):
                        return True
                else:
                    # 普通模式：匹配文件和目录
                    if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(path), pattern):
                        return True
        
        return False
    
    def scan_directory(self, root_path: Path, current_depth: int = 0) -> List[Tuple[str, int, bool, str, Optional[bool]]]:
        """
        递归扫描目录，在扫描过程中应用每层条目数限制
        
        Args:
            root_path: 要扫描的根目录
            current_depth: 当前深度
            
        Returns:
            文件树列表，每个元素为 (相对路径, 深度, 是否为目录, 文件名, 是否有更多文件被省略)
        """
        file_tree = []
        
        # 检查最大深度限制
        if self.config.max_depth is not None and current_depth >= self.config.max_depth:
            return file_tree
        
        try:
            entries = []
            with os.scandir(root_path) as it:
                for entry in it:
                    entry_path = Path(entry.path)
                    is_dir = entry.is_dir()
                    if not self.should_ignore(entry_path, is_dir=is_dir):
                        entries.append((entry_path, is_dir))
            
            # 排序：目录在前，然后按名称排序
            entries.sort(key=lambda x: (not x[1], x[0].name.lower()))
            
            # 应用每层条目数限制
            # 如果是根目录且设置了根目录不限制，则不限制
            if current_depth == 0 and self.config.unlimit_root_items:
                entries_to_process = [item[0] for item in entries]
                has_more = False
            elif self.config.max_items_per_level is not None:
                max_items = self.config.max_items_per_level
                entries_to_process = [item[0] for item in entries[:max_items]]
                has_more = len(entries) > max_items
            else:
                # 无限
                entries_to_process = [item[0] for item in entries]
                has_more = False
            
            # 计算父目录路径（用于 relative_path）
            parent_path = root_path.parent
            
            # 处理所有条目
            for entry in entries_to_process:
                # 使用相对路径字符串，避免重复的Path操作
                try:
                    relative_path = str(entry.relative_to(parent_path))
                except ValueError:
                    # 如果路径不在同一根下，使用绝对路径
                    relative_path = str(entry)
                name = entry.name
                file_tree.append((relative_path, current_depth, entry.is_dir(), name, None))
                
                # 如果是目录，递归扫描
                if entry.is_dir():
                    sub_tree = self.scan_directory(entry, current_depth + 1)
                    file_tree.extend(sub_tree)
            
            # 如果有更多条目被省略，在所有直接子项（包括递归子项）处理完后添加省略号
            # 省略号应该和该目录下的直接子项同级，所以 depth 是 current_depth
            if has_more:
                # 检查被省略的条目中是否还有文件（entries 是 (Path, is_dir) 元组列表）
                omitted_entries = entries[max_items:]
                has_files_in_omitted = any(not item[1] for item in omitted_entries)
                
                # 检查最后一个处理的条目是否是目录
                last_processed_is_dir = entries_to_process[-1].is_dir() if entries_to_process else False
                
                # 如果被省略的条目中还有文件，且最后一个处理的条目是目录，使用 ├──
                # 否则使用 └──
                use_branch = has_files_in_omitted and last_processed_is_dir
                
                # 添加省略号，深度为 current_depth（与直接子项同级）
                file_tree.append(("...", current_depth, False, "...", use_branch))
        
        except PermissionError:
            # 权限错误，跳过该目录
            pass
        except Exception as e:
            # 其他错误，记录但继续
            print(f"扫描目录 {root_path} 时出错: {e}")
        
        return file_tree
    
    def filter_ellipsis_children(self, file_tree: List[Tuple[str, int, bool, str, Optional[bool]]]) -> List[Tuple[str, int, bool, str, Optional[bool]]]:
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
        
        for i, (path, depth, is_dir, name, has_more_files) in enumerate(file_tree):
            if path == "...":
                # 遇到省略号，标记需要跳过后续更深层的项
                filtered_tree.append((path, depth, is_dir, name, has_more_files))
                # skip_until_depth 应该是省略号深度+1
                # 这样只会跳过该目录下的子项（递归子项），不会影响其他目录
                skip_until_depth = depth + 1
            elif skip_until_depth is not None:
                # 如果当前项比省略号的深度更深，跳过
                if depth >= skip_until_depth:
                    continue
                else:
                    # 遇到同级或更浅的项，停止跳过
                    skip_until_depth = None
                    filtered_tree.append((path, depth, is_dir, name, has_more_files))
            else:
                filtered_tree.append((path, depth, is_dir, name, has_more_files))
        
        return filtered_tree
    
    def generate_ascii_tree(self, root_name: str, file_tree: List[Tuple[str, int, bool, str, Optional[bool]]]) -> str:
        """
        生成ASCII艺术树格式
        
        Args:
            root_name: 根目录名称
            file_tree: 文件树列表
            
        Returns:
            ASCII格式的文件树字符串
        """
        # 使用列表收集所有行，最后一次性join
        lines = [root_name + '/']
        
        if not file_tree:
            return '\n'.join(lines)
        
        # 预先为每个深度建立索引，记录每个深度在哪些位置出现
        depth_indices = {}  # {depth: [indices]}
        for i, (_, depth, _, _, _) in enumerate(file_tree):
            if depth not in depth_indices:
                depth_indices[depth] = []
            depth_indices[depth].append(i)
        
        # 对于每个位置i和每个深度d，检查深度d在位置i之后是否还有条目
        # 这用于决定是否显示竖线
        def has_next_at_depth(pos: int, depth: int) -> bool:
            """检查深度depth在位置pos之后是否还有条目"""
            if depth not in depth_indices:
                return False
            # 找到深度depth的所有条目位置中，第一个大于pos的位置
            for idx in depth_indices[depth]:
                if idx > pos:
                    return True
            return False
        
        def is_last_in_parent(pos: int, depth: int) -> bool:
            """判断位置pos的条目是否是父目录下的最后一个条目"""
            if depth == 0:
                # 根目录下的条目，判断是否是整个文件树的最后一个条目
                return pos == len(file_tree) - 1
            
            # 从当前位置的下一个位置开始查找
            for j in range(pos + 1, len(file_tree)):
                next_depth = file_tree[j][1]
                if next_depth == depth:
                    # 找到了相同深度的条目，说明当前条目不是最后一个
                    return False
                if next_depth < depth:
                    # 找到了更上层的条目（父目录的兄弟或更上层），说明当前条目是父目录下的最后一个
                    return True
            
            # 没找到，说明当前条目是整个文件树的最后一个条目
            return True
        
        for i, (path, depth, is_dir, name, has_more_files) in enumerate(file_tree):
            # 判断是否是父目录下的最后一个条目
            is_last = is_last_in_parent(i, depth)
            
            # 构建前缀（使用列表拼接）
            prefix_parts = []
            for d in range(depth):
                if has_next_at_depth(i, d):
                    prefix_parts.append('│   ')
                else:
                    prefix_parts.append('    ')
            prefix = ''.join(prefix_parts)
            
            # 添加连接符
            if path == "...":
                # has_more_files 表示：被省略的条目中还有文件，且最后一个处理的条目是目录
                if has_more_files:
                    prefix += '├── '
                else:
                    prefix += '└── '
                display_name = "..."
            else:
                if is_last:
                    prefix += '└── '
                else:
                    prefix += '├── '
                
                display_name = name
                if is_dir:
                    display_name += '/'
            
            lines.append(prefix + display_name)
        
        return '\n'.join(lines)
    
    def generate_markdown_tree(self, root_name: str, file_tree: List[Tuple[str, int, bool, str, Optional[bool]]]) -> str:
        """
        生成Markdown格式的文件树
        
        Args:
            root_name: 根目录名称
            file_tree: 文件树列表
            
        Returns:
            Markdown格式的文件树字符串
        """
        lines = [f'- {root_name}/']
        
        # 预先计算常用缩进字符串，避免重复计算
        max_depth = max((d for _, d, _, _, _ in file_tree), default=0)
        indent_cache = {}
        for depth in range(max_depth + 2):
            indent_cache[depth] = '    ' * depth
        
        for path, depth, is_dir, name, _ in file_tree:
            indent = indent_cache[depth + 1]
            
            if path == "...":
                display_name = "..."
            else:
                display_name = name
                if is_dir:
                    display_name += '/'
            
            lines.append(f'{indent}- {display_name}')
        
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
        
        # 添加统计信息（在扫描时统计，避免再次遍历）
        file_count = sum(1 for item in self.file_tree if not item[2])  # 文件数量
        dir_count = sum(1 for item in self.file_tree if item[2])  # 目录数量
        result['stats'] = {'files': file_count, 'dirs': dir_count}
        
        return result

