#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复 ModelScope 在 Python 3.8 中的类型注解兼容性问题
"""

import os
import sys

def fix_torch_utils():
    """修复 torch_utils.py 中的类型注解问题"""
    torch_utils_path = None

    # 查找 torch_utils.py 文件
    for root, dirs, files in os.walk(sys.prefix):
        if 'torch_utils.py' in files and 'modelscope' in root:
            torch_utils_path = os.path.join(root, 'torch_utils.py')
            break

    if not torch_utils_path:
        print("未找到 torch_utils.py 文件")
        return False

    print(f"修复文件: {torch_utils_path}")

    # 读取文件内容
    with open(torch_utils_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复类型注解
    old_content = content
    content = content.replace('list[int]', 'List[int]')
    content = content.replace('dict[str, Any]', 'Dict[str, Any]')
    content = content.replace('tuple[', 'Tuple[')

    # 添加必要的导入
    if 'from typing import' not in content:
        content = 'from typing import List, Dict, Tuple, Any\n' + content
    else:
        # 确保导入了必要的类型
        import_line = None
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('from typing import'):
                import_line = i
                break

        if import_line is not None:
            imports = lines[import_line]
            needed_imports = ['List', 'Dict', 'Tuple', 'Any']
            for imp in needed_imports:
                if imp not in imports:
                    imports += f', {imp}'
            lines[import_line] = imports
            content = '\n'.join(lines)

    # 如果有修改，写回文件
    if content != old_content:
        # 备份原文件
        backup_path = torch_utils_path + '.backup'
        if not os.path.exists(backup_path):
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(old_content)

        # 写入修复后的内容
        with open(torch_utils_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("✅ 类型注解修复完成")
        return True
    else:
        print("文件无需修复")
        return True

if __name__ == '__main__':
    success = fix_torch_utils()
    if success:
        print("现在可以运行: python api_server.py")
    else:
        print("修复失败，请检查错误信息")