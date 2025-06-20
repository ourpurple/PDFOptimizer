# PDF Optimizer

**版本: 2.0.0**

一款功能强大的多功能PDF桌面工具，旨在提供一个简单、高效的解决方案，用于优化、转换和合并PDF文件。

![软件运行界面](http://pic.mathe.cn/2025/06/20/b42ba7cda750b.jpg)

---

## 核心功能

- **PDF 压缩优化**:
    - **双引擎支持**:
        - **标准引擎 (PyMuPDF)**: 通过有损图像压缩和无损PDF结构优化来平衡速度和压缩率。
        - **Ghostscript 引擎**: 利用强大的 Ghostscript 进行深度优化，提供与标准引擎不同的优化策略。
    - **多种质量预设**: 提供“低质量”、“中等质量”和“高质量”三种预设，以满足不同场景的需求。

- **PDF 文本转曲**:
    - **依赖 Ghostscript**: 调用行业标准的 Ghostscript 将PDF中的所有文本转换为矢量路径，以确保打印或跨平台查看时的一致性。

- **PDF 文件合并**:
    - **双引擎支持**:
        - **标准引擎 (Pikepdf)**: 快速、可靠地合并多个PDF文件。
        - **Ghostscript 引擎**: 提供另一种合并文件的策略。
    - **拖拽排序**: 在合并前，您可以通过拖拽文件列表来轻松调整合并顺序。

## 用户体验特性

- **直观的界面**: 简洁明了的布局，所有核心功能一目了然。
- **批量处理**: 支持一次性添加和处理多个文件，大大提高工作效率。
- **实时反馈**:
    - 通过进度条和状态列实时更新每个文件的处理状态。
    - 优化完成后，清晰地显示原始大小、优化后大小和压缩率。
    - 任务失败时，状态列和提示框（Tooltip）会显示详细的错误信息，便于排查问题。
- **Ghostscript 自动检测**: 程序启动时会自动检测 Ghostscript 是否安装，并在界面右下角提供清晰的状态提示，相关功能会根据检测结果动态启用或禁用。
- **无需安装**: 提供单文件绿色版，下载即用。

---

## 🚀 快速上手

1.  从发布页面下载最新的可执行文件。
2.  双击运行程序。
3.  点击 **"选择 PDF 文件"** 按钮，将一个或多个文件添加到列表中。
4.  根据您的需求执行操作:
    - **优化**: 在界面顶部选择“优化质量”和“引擎”，然后点击 **"开始优化"**。
    - **转曲**: 确保已安装 Ghostscript，然后点击 **"开始转曲"**。
    - **合并**: 如果需要，拖拽列表中的文件以调整顺序，然后点击 **"合并 PDF"**，并选择保存位置。
5.  处理完成后，生成的新文件将保存在您指定的位置（合并）或原始文件所在的目录（优化/转曲）。文件名将包含后缀以区分，例如：
    - `_optimized_pymupdf` (标准引擎优化)
    - `_optimized_ghostscript` (Ghostscript 引擎优化)
    - `_curved_ghostscript` (Ghostscript 转曲)

---

## 🔧 技术实现

本工具主要基于 Python 和 PySide6 构建，其核心功能通过调用以下库和工具实现：

- **标准引擎 (优化与合并)**:
    - **`PyMuPDF`**: 用于在优化过程中提取和替换PDF中的图像。
    - **`Pikepdf`**: 用于执行PDF的无损结构优化（如对象流压缩、线性化）和文件合并。

- **Ghostscript 引擎 (优化、转曲与合并)**:
    - **`subprocess`**: 通过此模块调用外部的 Ghostscript 命令行程序。
    - **优化**: 使用 `-dPDFSETTINGS` 参数 (如 `/screen`, `/ebook`, `/prepress`) 来应用不同的预设优化策略。
    - **转曲**: 使用 `-dNoOutputFonts` 参数将文本转换为矢量路径。
    - **合并**: 调用 Ghostscript 的标准命令来合并文件列表。

---

## 🛠️ 开发与构建

如果您希望对本项目进行二次开发，请遵循以下步骤。

**环境要求**: Python 3.x。如果需要使用或测试 Ghostscript 相关功能，请确保其已安装并已配置好系统 `PATH` 环境变量。

1.  **克隆仓库**
    ```bash
    git clone https://github.com/ourpurple/PDFOptimizer.git
    cd PDFOptimizer
    ```

2.  **创建并激活虚拟环境**
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    # source venv/bin/activate  # macOS/Linux
    ```

3.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

4.  **运行程序 (开发模式)**
    ```bash
    python main.py
    ```

5.  **打包成单文件 .exe (使用 PyInstaller)**
    ```bash
    pyinstaller main.py --onefile --windowed --name PDFOptimizer --add-data "ui/style.qss;." --add-data "app.ico;."
    ```
    最终的可执行文件会生成在 `dist` 目录下。

---

## 📝 授权协议

本项目基于 [MIT 授权协议](LICENSE) 开源。
