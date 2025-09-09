# PyEncryptor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**PyEncryptor** 是一个强大的 Python 项目加密与编译工具，可将 `.py` 源代码文件批量编译为 `.so` 二进制文件，有效保护源码不被轻易查看或篡改。同时完整保留项目目录结构，支持多线程加速、失败重试、智能跳过（如 `__init__.py`）、灵活配置，适用于生产环境部署前的代码保护。

---

## ✨ 特性

- ✅ **源码保护**：将 `.py` 文件编译为平台相关的 `.so` 文件，提升代码安全性。
- 🧭 **结构保留**：完整复制并保留原始项目目录结构。
- ⚙️ **智能跳过**：默认跳过 `__init__.py`、`__pycache__`、`.git` 等文件/目录。
- 🚀 **多线程加速**：支持并发编译，大幅提升大型项目处理速度。
- 🔄 **失败重试**：编译失败自动重试，提高成功率。
- 🧹 **临时清理**：自动管理临时文件，避免污染源码。
- 📋 **详细日志**：记录编译全过程，便于调试与审计。
- 📊 **统计报告**：输出编译成功率、耗时、失败文件等关键指标。
- 🛠️ **灵活配置**：支持命令行参数、环境变量、配置文件（未来扩展）。

---

## 📦 安装

### 方式一：通过 pip 安装（推荐）

```bash
pip install pyencryptor
```

### 方式二：从源码安装

```bash
git clone https://github.com/charlie3go/PyEncryptor.git
cd PyEncryptor
pip install -e .
```

> **依赖要求**：
> - Python ≥ 3.7
> - Cython ≥ 0.29.0（自动安装）

---

## 🚀 快速开始

### 基本用法

```bash
pyencryptor -p ./your_project -o ./your_project_compiled
```

### 示例

将项目 `my_app` 编译到 `my_app_dist`，使用 8 个线程，重试 3 次：

```bash
pyencryptor --project_path ./my_app --output_path ./my_app_dist --workers 8 --retry 3
```

---

## 🧩 命令行参数详解

```bash
usage: pyencryptor [-h] [--project_path PROJECT_PATH] [--output_path OUTPUT_PATH]
                   [--tmp_path TMP_PATH] [--exclude-dirs [EXCLUDE_DIRS ...]]
                   [--exclude-files [EXCLUDE_FILES ...]] [--keep-init]
                   [--workers WORKERS] [--retry RETRY] [--log-file LOG_FILE]
                   [--log-level {DEBUG,INFO,WARNING,ERROR}] [--version]

Python 项目加密编译与打包工具

可选参数:
  -h, --help            显示帮助信息并退出
  -p, --project_path    待加密项目路径（必需）
  -o, --output_path     输出路径（必需）
  -t, --tmp_path        临时文件目录（默认: ./temp）
  --exclude-dirs        要排除的目录列表（如：tests docs）
  --exclude-files       要排除的文件列表（如：config.py）
  --keep-init           保留 __init__.py 不编译（默认启用）
  -w, --workers         并行线程数（默认: 4）
  -r, --retry           编译失败重试次数（默认: 2）
  --log-file            日志文件路径（默认: ./logs/pyencryptor.log）
  --log-level           日志级别（DEBUG/INFO/WARNING/ERROR，默认: INFO）
  -v, --version         显示版本号
```

---

## 📁 输出结构示例

假设原始项目结构如下：

```
my_project/
├── main.py
├── utils/
│   ├── __init__.py
│   └── helper.py
└── config.ini
```

运行命令：

```bash
pyencryptor -p ./my_project -o ./my_project_compiled
```

输出结构：

```
my_project_compiled/
├── main.so          # 编译后的二进制文件
├── utils/
│   ├── __init__.py  # 默认保留不编译
│   └── helper.so    # 编译后的二进制文件
└── config.ini       # 原样复制
```

---

## 📝 日志与报告

所有操作日志将输出到控制台并记录在 `logs/pyencryptor.log`（可自定义）。

编译完成后，控制台将输出统计报告：

```
##########################
   统计信息:
   总文件数: 15
   编译成功: 12
   原样复制: 2
   跳过文件: 1
   编译失败: 0
   耗时: 8.45 秒
##########################
```

> ⚠️ 若有文件编译失败，会复制原始 `.py` 文件并输出警告，确保项目功能完整。

---

## 🛡️ 注意事项

1. **平台依赖**：`.so` 文件是平台相关的（Linux/macOS），Windows 生成 `.pyd`。编译环境需与目标运行环境一致。
2. **性能影响**：Cython 编译可能略微提升执行速度，但主要目的是保护源码。
3. **依赖管理**：编译后的项目仍需安装所有 Python 依赖包（如 `requirements.txt`）。
4. **调试困难**：编译后无法直接调试源码，建议仅在生产环境使用。
5. **非绝对安全**：`.so` 文件仍可被反汇编，但极大提高了逆向门槛。

---

## 🤝 贡献

欢迎提交 Issue 或 Pull Request！请确保代码风格一致并包含测试。

```bash
# 开发依赖安装
pip install -e .[dev]

# 运行测试（待补充）
pytest

# 构建分发包
python -m build
```

---

## 📜 许可证

本项目采用 **MIT 许可证** - 详情见 [LICENSE](LICENSE) 文件。

---

## 📬 联系作者

- 作者：charlie3go
- 邮箱：aslongrushan@gmail.com
- GitHub：https://github.com/charlie3go/PyEncryptor

---

> **温馨提示**：合理使用本工具，遵守相关法律法规，尊重知识产权。