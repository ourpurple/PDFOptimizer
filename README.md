# PDF Optimizer

一个简单易用的桌面工具，用于压缩和优化PDF文件，减小文件体积。


## ✨ 功能特性

- **双优化引擎**:
    - **标准引擎**: 基于 `PyMuPDF` 和 `Pikepdf`，对图片进行有损压缩，并对PDF结构进行无损优化，平衡了速度和优化率。
    - **Ghostscript 引擎**: 调用强大的 Ghostscript 工具进行深度优化，提供与标准引擎不同的优化策略和效果。
- **多种优化预设**: 提供“低质量”、“中等质量”和“高质量”三种优化选项，以满足不同场景的需求。
- **批量处理**: 支持一次选择并优化多个PDF文件。
- **实时进度反馈**: 直观地显示每个文件的优化状态、进度和最终的压缩率。
- **PDF文本转曲 (需 Ghostscript)**: 新增功能，可将PDF中的所有文本转换为矢量路径（曲线）。此功能依赖于外部工具 Ghostscript，程序会自动检测其是否安装。
- **Ghostscript 状态检测**: 程序启动时会自动检测系统中是否安装了 Ghostscript，并在主界面右下角给出明确的状态提示。
- **跨平台**: 使用 PySide6 构建，理论上可以打包成在 Windows, macOS, Linux 上运行的程序。
- **无需安装**: 提供单文件绿色版，下载即用，无需安装。

## 🚀 使用方法

1.  从 `dist` 目录下载 `PDFOptimizer.exe` 文件。
2.  双击运行 `PDFOptimizer.exe`。
3.  在程序界面顶部的同一行中，选择您需要的“优化质量”和“优化引擎”（如果 Ghostscript 已安装，将默认选择“Ghostscript 引擎”）。
4.  点击“选择 PDF 文件”按钮，选择一个或多个需要优化的文件。
5.  根据您的需求，点击“开始优化”或“开始转曲 (Ghostscript)”按钮，程序将开始处理。
6.  优化或转曲完成后，新的文件将以 `_optimized` 或 `_curved` 后缀保存在原始文件所在的目录。

## 🔧 技术实现细节

本工具的PDF处理核心包含两个主要功能：优化（减小体积）和转曲（文本转为路径）。

### PDF 优化过程
本工具提供两种不同的优化引擎：

#### 1. 标准引擎 (Standard Engine)
此引擎的优化核心是一个两阶段的过程，结合了 **PyMuPDF (fitz)** 和 **Pikepdf** 两个强大的库的优点。它主要通过重新压缩图片和整理PDF结构来减小文件体积。

### 第一阶段：图像的重新压缩 (有损)

此阶段的目标是减小PDF中内嵌图片的体积，这是PDF文件体积的主要来源。

1.  **遍历页面与图片**: 使用 `PyMuPDF` 库打开PDF文件，逐一遍历其中的每一个页面。
2.  **提取图片**: 在每个页面上，提取出所有的图片对象。
3.  **色彩空间转换**: 使用 `Pillow (PIL)` 库读取图片数据。由于JPEG格式不支持CMYK色彩空间，程序会检查图片的模式，如果为 `CMYK`，则会先将其转换为更通用的 `RGB` 模式。
4.  **JPEG 重新编码**: 将转换后的图片以指定的质量参数（例如，中等质量为85%）重新编码为JPEG格式。JPEG是一种有损压缩格式，这是减小文件体积最关键的一步。
5.  **替换图片**: 使用 `PyMuPDF` 的 `page.replace_image()` 方法，将PDF中的原始图片替换为我们刚刚重新压缩过的新图片。

### 第二阶段：PDF结构的无损优化

此阶段的目标是整理和优化PDF文件本身的结构，进一步减小体积。

1.  **中间保存**: 在完成所有图片的替换后，`PyMuPDF` 会将修改后的文档保存到一个临时文件中。在此过程中，它会执行一些清理操作，例如移除未使用的对象 (`garbage=4`) 和压缩数据流 (`deflate=True`)。
2.  **Pikepdf 线性化处理**: 使用 `Pikepdf` 库打开上一步生成的临时文件。Pikepdf 非常擅长理解和重建PDF的内部结构。
3.  **保存最终文件**: 调用 `pikepdf.save()` 方法保存最终的优化文件。在此过程中，执行了几个关键的无损优化操作：
    *   `object_stream_mode=pikepdf.ObjectStreamMode.generate`: 将PDF中的多个对象打包到“对象流”中，可以显著减少对象开销，减小文件体积。
    *   `compress_streams=True`: 确保所有的数据流都得到了压缩。
    *   `linearize=True`: 对PDF进行“线性化”处理（也称为“Web优化”）。这会重新组织文件结构，使得浏览器或PDF阅读器可以不必下载整个文件就开始显示第一页，虽然对本地文件体积影响不大，但这是一个很好的实践。

通过这两个阶段的处理，PDF Optimizer 能够在保证内容基本可读的前提下，最大限度地减小PDF文件的体积。

#### 2. Ghostscript 引擎 (Ghostscript Engine)
此引擎直接调用外部的 Ghostscript 程序来完成优化。它使用 Ghostscript 内置的 `dPDFSETTINGS` 参数，这些参数是为不同的输出目的（如屏幕阅读、电子书、印刷）而精心配置的优化策略集。例如：
-   `/screen`: 低分辨率、高压缩率，适用于屏幕显示。
-   `/ebook`: 中等分辨率和压缩率，适用于电子书。
-   `/printer`: 高质量，适用于印刷。
这提供了一个与标准引擎完全不同的优化途径，有时能在特定类型的PDF上取得更好的效果。

### PDF 转曲过程 (基于 Ghostscript)

为了达到印刷级别的稳定性和可靠性，本工具的转曲功能现在依赖于强大的行业标准工具——**Ghostscript**。

**重要提示**: 程序启动时会自动检测 Ghostscript 是否已安装并配置正确。如果未检测到，转曲功能将被禁用。请根据主界面右下角的状态提示，确保您的计算机上已安装 Ghostscript，并且其可执行文件（如 `gswin64c.exe` 或 `gs`）已添加至系统的 `PATH` 环境变量中。

转曲过程如下：

1.  **调用子进程**: 程序通过 Python 的 `subprocess` 模块，在后台启动一个 Ghostscript 进程。
2.  **执行命令**: 执行一个精确构造的 Ghostscript 命令，该命令的核心是 `-dNoOutputFonts` 参数。这个参数会指示 Ghostscript 读取输入的PDF，并将其中所有的字体都转换为矢量轮廓，然后生成一个新的PDF文件。
3.  **保存文件**: Ghostscript 直接处理并保存转曲后的文件，文件名以 `_curved` 后缀结尾。

这个方法将复杂的PDF处理任务完全委托给了最专业的工具，从而确保了转曲结果的最高质量和稳定性。

## 🛠️ 开发与构建

如果您希望对本项目进行二次开发，请遵循以下步骤：
(转曲功能额外要求: 请确保您的开发环境中已安装 Ghostscript 并已配置好 PATH 环境变量。)

1.  **克隆仓库**
    ```bash
    git clone [your-repo-url]
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

4.  **安装打包工具**
    ```bash
    pip install pyinstaller
    ```

5.  **运行程序 (开发模式)**
    ```bash
    python main.py
    ```

6.  **打包成单文件exe**
    ```bash
    pyinstaller main.py --onefile --windowed --name PDFOptimizer --add-data "ui/style.qss;."
    ```    最终的可执行文件会生成在 `dist` 目录下。
