#！/usr/bin/env python3 

"""PyEncryptor: A Python project encryption and compilation tool.

This tool compiles .py files within a Python project into .so files,
preserving the original directory structure in a new output directory.
It offers smart skipping of __init__.py files, multiple configuration
sources (config file, CLI, environment variables), and robust error
handling with retries and temporary file cleanup.

Example:
    A typical usage might look like this:

    $ python3 pyencryptor.py -p ./my_project -o ./my_project_compiled

Author: charlie3go
Date: 2025/09/09
Version: 1.0.0
License: MIT (see full license text below)
"""


""" 
MIT License

Copyright (c) 2025 charlie3go

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import os
import sys
import shutil
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from datetime import datetime


class PyEncryptor:
    def __init__(
            self,
            project_path: str,
            output_path: str,
            tmp_path: Optional[str] = None,
            exclude_dirs: Optional[List[str]] = None,
            exclude_files: Optional[List[str]] = None,
            keep_init: bool = True,
            workers: int = 4,
            retry_times: int = 2,
            log_file: str = 'pyencryptor.log',
            log_level: int = logging.INFO
        ):
        """
        初始化 PyEncryptor

        :param project_path: 待加密项目路径
        :param output_path: 输出路径
        :param tmp_path: 临时数据存放路径
        :param exclude_dirs: 要排除的目录列表
        :param exclude_files: 要排除的文件列表
        :param keep_init: 是否保留 __init__.py（不编译）
        :param workers: 并行编译线程数
        :param retry_times: 编译失败重试次数
        :param log_dir: 日志文件路径
        :param log_level: 日志级别
        """
        self.project_path = Path(project_path).absolute()
        self.output_path = Path(output_path).absolute()
        self.tmp_path = Path(tmp_path).absolute() if tmp_path else None
        self.exclude_dirs = set(exclude_dirs or ['__pycache__', '.git', '.idea', 'venv', '.venv', '.mypy_cache'])
        self.exclude_files = set(exclude_files or [])
        self.keep_init = keep_init
        self.workers = max(1, workers)
        self.retry_times = max(0, retry_times)
        self.log_file = Path(log_file)

        # 设置日志
        self._setup_logging(log_level)

        # 验证路径
        self._validate_paths()

        # 统计信息
        self.stats = {
            'total_files': 0,
            'compiled_files': 0,
            'copied_files': 0,
            'skipped_files': 0,
            'failed_files': 0,
            'start_time': datetime.now().isoformat(),
            'end_time': None
        }

        # 编译失败文件记录
        self.failed_files: List[str] = []


    def _setup_logging(self, log_level: int) -> None:
        """配置日志记录"""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('PyEncryptor')
        self.logger.info(f"############\n{self.project_path}项目正在加密编译...\n############")


    def _validate_paths(self) -> None:
        """验证输入路径是否有效"""
        if not self.project_path.exists():
            raise FileNotFoundError(f"项目路径不存在: {self.project_path}")

        if not self.project_path.is_dir():
            raise NotADirectoryError(f"项目路径不是目录: {self.project_path}")

        self.logger.info(f"项目路径: {self.project_path}")
        self.logger.info(f"输出路径: {self.output_path}")


    def _should_exclude(self, path: Path) -> bool:
        """判断是否应该排除某个文件或目录"""
        # 检查排除目录
        for part in path.parts:
            if part in self.exclude_dirs:
                return True

        # 检查排除文件
        if path.name in self.exclude_files:
            return True

        # 保留 __init__.py
        if self.keep_init and path.name == '__init__.py':
            return True

        return False
    

    def _compile_py_to_so(self, py_file: Path, temp_dir: Path) -> Optional[Path]:
        """
        将单个 .py 文件编译为 .so 文件

        :param py_file: Python 文件路径
        :param temp_dir: 临时目录
        :return: 编译后的 .so 文件路径，失败返回 None
        """
        for attempt in range(self.retry_times + 1):
            try:
                build_dir = temp_dir / "build"
                build_dir.mkdir(exist_ok=True)

                setup_name = f"setup_{py_file.stem}_{hash(py_file) % 10000}"
                setup_file = temp_dir / f"{setup_name}.py"

                # 拷贝 .py 文件 到临时目录（防止编译过程中产生 .c 文件，污染源文件）
                # 为每个文件创建一个独立的编译环境，防止并发冲突和文件名污染
                # 使用哈希值作为子目录名，保证唯一性和路径长度可控
                file_hash = hash(str(py_file.absolute()))
                compile_temp_dir = temp_dir / f"compile_{file_hash % 100000}"
                compile_temp_dir.mkdir(parents=True, exist_ok=True)
                
                temp_py_file = compile_temp_dir / py_file.name
                shutil.copy2(py_file, temp_py_file)

                with open(setup_file, 'w', encoding='utf-8') as f:
                    f.write(f"""
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        r"{temp_py_file.absolute()}",
        compiler_directives={{
            'language_level': 3,
            'boundscheck': False,
            'wraparound': False
        }},
        nthreads={self.workers}
    ),
    script_args=['build_ext', '--inplace']
)
""")

                # 执行编译
                self.logger.info(f"[{attempt + 1}/{self.retry_times + 1}] 编译中: {py_file}")
                result = subprocess.run(
                    [sys.executable, str(setup_file)],
                    cwd=compile_temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=60  # 1分钟超时
                )

                if result.returncode != 0:
                    raise RuntimeError(f"编译失败:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

                # 精确匹配 .so 文件：模块名 + .cpython-xxx-x86_64-linux-gnu.so
                expected_stem = temp_py_file.stem
                for f in compile_temp_dir.iterdir():
                    if f.suffix == '.so' and f.stem.startswith(expected_stem):
                        self.logger.info(f"编译成功: {py_file.name} -> {f.name}")
                        return f

                raise FileNotFoundError(f"在 {compile_temp_dir} 中未找到匹配的 .so 文件")

            except Exception as e:
                self.logger.warning(f"第 {attempt + 1} 次编译失败: {py_file} - {str(e)}")
                if attempt == self.retry_times:
                    self.logger.error(f"最终编译失败: {py_file}")
                    return None
                continue

        return None
    

    def _process_file(self, src_file: Path, dst_dir: Path, temp_dir: Path) -> Dict[str, Any]:
        """
        处理单个文件（线程安全）

        :return: 处理结果字典
        """
        result = {
            'file': str(src_file),
            'status': 'skipped',
            'message': '',
            'dst': None
        }

        if self._should_exclude(src_file):
            result['status'] = 'skipped'
            result['message'] = 'excluded'
            return result

        dst_dir.mkdir(parents=True, exist_ok=True)

        if src_file.suffix == '.py':
            so_file = self._compile_py_to_so(src_file, temp_dir)
            if so_file:
                dst_file = dst_dir / f"{src_file.stem}.so"
                shutil.copy2(so_file, dst_file)
                result['status'] = 'compiled'
                result['dst'] = str(dst_file)
            else:
                # 编译失败，复制原文件
                dst_file = dst_dir / src_file.name
                shutil.copy2(src_file, dst_file)
                result['status'] = 'copied_fallback'
                result['dst'] = str(dst_file)
                result['message'] = '编译失败，复制原文件'
        else:
            dst_file = dst_dir / src_file.name
            shutil.copy2(src_file, dst_file)
            result['status'] = 'copied'
            result['dst'] = str(dst_file)

        return result
    

    def _process_directory(self, src_dir: Path, dst_dir: Path, temp_dir: Path) -> None:
        """
        递归处理目录
        """
        if self._should_exclude(src_dir):
            self.logger.info(f"跳过目录: {src_dir}")
            return

        # 收集所有待处理文件
        files_to_process = []
        for item in src_dir.rglob("*"):
            if item.is_file() and not self._should_exclude(item):
                rel_path = item.relative_to(src_dir)
                target_dir = dst_dir / rel_path.parent
                files_to_process.append((item, target_dir))

        if not files_to_process:
            return

        self.logger.info(f"处理目录: {src_dir} → {len(files_to_process)} 个文件")

        # 多线程处理
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self._process_file, src, dst, temp_dir): (src, dst)
                for src, dst in files_to_process
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    self.stats['total_files'] += 1

                    if result['status'] == 'compiled':
                        self.stats['compiled_files'] += 1
                    elif result['status'] in ['copied', 'copied_fallback']:
                        self.stats['copied_files'] += 1
                    elif result['status'] == 'skipped':
                        self.stats['skipped_files'] += 1
        
                    if result['status'] == 'copied_fallback':
                        self.failed_files.append(result['file'])

                except Exception as e:
                    self.logger.error(f"处理文件时发生异常: {e}")
                    self.stats['failed_files'] += 1


    def encrypt(self):
        """
        执行加密编译过程
        """
        self.logger.info("开始加密编译过程...")
        self.logger.info(f"使用线程数: {self.workers}")

        try:
            with tempfile.TemporaryDirectory(dir=self.tmp_path) as temp_dir:
                temp_dir = Path(temp_dir)
                self.logger.info(f"临时目录: {temp_dir}")

                if self.output_path.exists():
                    self.logger.info(f"输出目录已存在，将被覆盖: {self.output_path}")
                    shutil.rmtree(self.output_path)
                self.output_path.mkdir(parents=True, exist_ok=True)

                # 开始处理
                self._process_directory(self.project_path, self.output_path, temp_dir)

        except Exception as e:
            self.logger.error(f"加密过程中发生严重错误: {e}")
            raise

        # 结束统计
        self.stats['end_time'] = datetime.now().isoformat()
        duration = (datetime.fromisoformat(self.stats['end_time']) -
                    datetime.fromisoformat(self.stats['start_time'])).total_seconds()
        self.stats['duration_seconds'] = round(duration, 2)

        # 输出总结
        self.logger.info("加密编译完成!")
        summary = (
            f"   统计信息:\n"
            f"   总文件数: {self.stats['total_files']}\n"
            f"   编译成功: {self.stats['compiled_files']}\n"
            f"   原样复制: {self.stats['copied_files']}\n"
            f"   跳过文件: {self.stats['skipped_files']}\n"
            f"   编译失败: {self.stats['failed_files']}\n"
            f"   耗时: {self.stats['duration_seconds']} 秒"
        )
        self.logger.info(f"##########################\n{summary}\n##########################")

        if self.failed_files:
            self.logger.warning(f"以下文件编译失败（已复制原文件）:\n" + "\n".join(self.failed_files))


def encryptor_cli():
    ENCRYPTOR_LOG_DIR = Path(__file__).parent / "logs"
    TEMP_FILE_DIR = Path(__file__).parent / "temp"

    ENCRYPTOR_LOG_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_FILE_DIR.mkdir(parents=True, exist_ok=True)
    
    parser = argparse.ArgumentParser(
        description="Python 项目加密编译与打包工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
```python pyencryptor.py --project_path project_path --output_path output_path --workers 8
"""
    )

    parser.add_argument("--project_path", "-p", help="待加密项目路径")
    parser.add_argument("--output_path", "-o", help="输出路径")
    parser.add_argument("--tmp_path", "-t", default=str(TEMP_FILE_DIR), help="编译临时文件路径")
    parser.add_argument("--exclude-dirs", nargs="*", default=[], help="要排除的目录列表")
    parser.add_argument("--exclude-files", nargs="*", default=[], help="要排除的文件列表")
    parser.add_argument("--keep-init", action="store_true", help="保留 __init__.py 不编译")
    parser.add_argument("--workers", "-w", type=int, default=4, help="并行线程数")
    parser.add_argument("--retry", "-r", type=int, default=2, help="编译失败重试次数")
    parser.add_argument("--log-file", default=os.path.join(ENCRYPTOR_LOG_DIR, 'pyencryptor.log'), help="日志文件路径")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help="日志级别")
    parser.add_argument("--version", "-v", action="store_true", help="显示版本")

    args = parser.parse_args()
        
    try:
        encryptor = PyEncryptor(
            project_path=args.project_path,
            output_path=args.output_path,
            tmp_path=args.tmp_path,
            exclude_dirs=args.exclude_dirs,
            exclude_files=args.exclude_files,
            keep_init=args.keep_init,
            workers=args.workers,
            retry_times=args.retry,
            log_file=args.log_file,
            log_level=getattr(logging, args.log_level)
        )
        encryptor.encrypt()

    except Exception as e:
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"加密编译过程中发生错误: {str(e)}")
        sys.exit(1)

