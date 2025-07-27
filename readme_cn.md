# PDF Optimizer - PDF文件优化工具

[![版本](https://img.shields.io/badge/version-3.10-blue.svg)](https://github.com/ourpurple/PDFOptimizer/releases)

一个功能强大的PDF工具集，支持PDF压缩、合并、分割、图片转换、文本转曲和书签管理等功能。

## 主要功能

- 📦 **PDF文件压缩优化**
  - 支持三种质量预设：低质量(最大压缩)、中等质量(推荐)、高质量(轻度优化)
  - 同时支持 `pikepdf` 和 `Ghostscript` 两种优化引擎

- 🔄 **PDF文件合并**
  - 支持多个PDF文件合并
  - 支持拖拽排序确定合并顺序
  - 支持 `pikepdf` 和 `Ghostscript` 两种合并引擎

- ✂️ **PDF分割**
  - 将多页PDF按页分割为独立的单页文件
  - 使用 `PyMuPDF` 实现快速高效的分割

- 🖼️ **PDF转图片**
  - 将PDF的每一页转换为图片
  - 支持自定义DPI和图片格式（PNG、JPG）
  - 使用 `PyMuPDF` 实现高质量转换

- ✏️ **PDF文本转曲**
  - 使用Ghostscript将文本转换为曲线
  - 确保字体显示一致性

- 📑 **PDF书签管理**
  - 支持为PDF文件添加书签
  - 支持批量添加书签
  - 支持为多个文件使用相同的书签配置
  - 支持书签配置的导入导出
  - 支持书签的编辑和预览

- 🧠 **PDF智能识别 (OCR)**
 - 将PDF页面转换为图片，并调用兼容OpenAI格式的大语言模型（如GPT-4o）进行内容识别。
 - 将识别结果转换为结构化的Markdown文本。
 - 支持自定义API地址、模型名称和提示词 (Prompt)。
 - 安全地保存API配置，无需重复输入。
 - **自动生成DOCX**：利用[Pandoc](https://pandoc.org/)，将识别出的Markdown内容（包含LaTeX公式）自动转换为高质量的`.docx`文件。

- 🎨 **友好的用户界面**
  - 简洁直观的标签式操作界面
  - 全功能支持文件拖拽
  - 实时显示处理进度
  - 详细的处理结果反馈
  
  ## 界面截图
  
  ![界面截图](http://pic.mathe.cn/2025/07/17/79d439f3b098b.png)
  
  ## 系统要求

- Windows操作系统
- Python 3.7+
- Ghostscript (可选，但推荐安装以使用全部功能)

## 安装说明

1. 克隆或下载本项目代码
```bash
git clone https://github.com/yourusername/PDFOptimizer.git
```

2. 安装 uv (通用虚拟环境管理工具)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. 创建虚拟环境并安装依赖
```bash
uv venv
uv pip install -r requirements.txt
```

4. （可选）安装开发依赖
```bash
uv pip install -r requirements-dev.txt
```

5. 安装Ghostscript（可选）
- 从[Ghostscript官网](https://www.ghostscript.com/releases/gsdnld.html)下载并安装
- 确保Ghostscript已添加到系统环境变量PATH中

## 使用方法

1. 运行程序
```bash
uv run main.py
```

2. PDF文件优化
   - 点击"添加文件"或直接拖拽PDF文件到程序窗口
   - 选择期望的质量预设
   - 选择优化引擎（pikepdf或Ghostscript）
   - 点击"开始优化"
   
   3. PDF文件合并
      - 添加多个PDF文件
      - 通过拖拽调整文件顺序
      - 点击"开始合并"
   
   4. PDF分割
      - 切换到"PDF分割"标签页
      - 添加需要分割的PDF文件
      - 点击"开始分割"并选择保存输出文件的文件夹
   
   5. PDF转图片
      - 切换到"PDF转图片"标签页
      - 添加需要转换的PDF文件
      - 选择期望的图片格式和DPI
      - 点击"开始转换"并选择保存输出图片的文件夹
   
   6. PDF文本转曲
      - 切换到"PDF转曲"标签页
      - 添加需要处理的PDF文件
      - 点击"开始转曲"
      - 等待处理完成
  
  7. PDF智能识别 (OCR)
     - 切换到"PDF OCR"标签页。
     - 首次使用时，请填入您的API Base URL、API Key，然后点击"获取模型列表"按钮来获取可用的模型列表。选择合适的模型后，点击“保存配置”。此配置将安全地保存在本地，未来无需再次输入。
     - 注意："获取模型列表"按钮只有在API Base URL和API Key都填写后才会变为可用状态。
     - 点击“选择PDF文件”按钮，选择一个需要识别的PDF文档。
     - 点击“开始识别”按钮，程序会将PDF逐页转换为图片并交由AI模型处理。
     - 识别完成后，结果将以Markdown格式显示在文本框中，并自动保存为同名的`.md`和`.docx`文件。
  
  ## 注意事项

- 建议在处理重要文件前先进行备份
- 对于大文件处理可能需要较长时间，请耐心等待。
- Ghostscript 引擎在某些情况下能提供更好的压缩效果，但处理速度可能慢于 pikepdf。
- 转曲功能依赖于 Ghostscript，未安装则无法使用。

## 实现细节

- **PDF 优化 (pikepdf 引擎)**  
  - 使用 `pikepdf.open(input_path)` 打开源文件，基于三种质量预设（低质量/中等质量/高质量）设置 `compress_streams`、`object_stream_mode`、`linearize` 参数。  
  - 调用 `pdf.save(output_path, min_version=..., object_stream_mode=..., compress_streams=..., linearize=...)` 写出优化后的 PDF。

- **PDF 优化 (Ghostscript 引擎)**  
  - 通过 `_get_gs_executable` 查找 Ghostscript，优先级为：环境变量 `GHOSTSCRIPT_EXECUTABLE` > PyInstaller 打包路径 > `shutil.which` 系统 PATH。
  - 调用 `subprocess.Popen` 执行 Ghostscript 命令行：  
    ```bash
    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/screen|/ebook|/prepress -dNOPAUSE -dBATCH -dQUIET -sOutputFile=output.pdf input.pdf
    ```  
  - 根据返回码判断优化结果，并通过 `os.path.getsize` 计算压缩前后文件大小。

- **PDF 合并 (pikepdf 引擎)**  
  - 使用 `pikepdf.Pdf.new()` 创建空 PDF，遍历输入文件列表，使用 `pdf.pages.extend(src.pages)` 将所有页面追加到目标 PDF，最后 `pdf.save(output_path)`。

- **PDF 合并 (Ghostscript 引擎)**  
  - 调用 Ghostscript 执行命令行：  
    ```bash
    gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile=merged.pdf file1.pdf file2.pdf ...
    ```  
  - 通过返回码和文件大小判断合并结果。

- **PDF 文本转曲**  
  - 基于 Ghostscript 命令行，增加 `-dNoOutputFonts` 参数，将所有文本转换为曲线以保证跨平台字体一致性：  
    ```bash
    gs -sDEVICE=pdfwrite -o curves.pdf -dNOPAUSE -dBATCH -dQUIET -dNoOutputFonts input.pdf
    ```

- **PDF 分割 (PyMuPDF 引擎)**
  - 使用 `fitz.open()` 打开源 PDF，遍历每一页，通过 `new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)` 为每一页创建一个新的单页 PDF。

- **PDF 转图片 (PyMuPDF 引擎)**
  - 使用 `fitz.open()` 打开 PDF，遍历每一页，并使用 `page.get_pixmap(dpi=dpi)` 将页面转换为位图。
  - 将位图保存为指定的图片格式 (PNG/JPG)。

- **图形界面 (PySide6)**
  - 使用 `QMainWindow` 和 `QTabWidget` 构建主窗口及五个功能页（优化、合并、分割、转图片、转曲）。
  - 采用自定义 `SortableTableWidget`，重写拖拽事件 (`dragEnterEvent`, `dragMoveEvent`, `dropEvent`) 和右键菜单 (`contextMenuEvent`)，支持文件列表的拖拽排序、删除、上移/下移和打开文件所在位置。
  - 基于 `QThread`（封装为 `BaseWorker` 及其子类如 `OptimizeWorker`, `MergeWorker` 等）实现多线程处理，使用 `Signal` 实时更新进度条和表格状态，避免UI阻塞。
  - 资源路径通过 `resource_path` 处理，兼容开发环境与 PyInstaller 打包的 `_MEIPASS` 目录。

- **PDF智能识别 (OCR)**
 - **PDF转图片**: 复用 `core.pdf2img` 模块，将PDF页面转换为200 DPI的PNG图片，并保存到临时目录。
 - **调用AI模型**: 新增 `core.ocr` 模块，包含 `process_images_with_model` 函数。该函数负责：
   - 将每张图片进行Base64编码。
   - 构建符合OpenAI Vision API格式的JSON payload，将图片和用户自定义的提示词（Prompt）发送到指定的API端点。
   - 使用 `httpx` 库发送POST请求，并处理API返回的JSON数据。
 - **配置管理**:
   - 使用 `python-dotenv` 库管理API配置。
   - 在用户主目录下的 `.pdfoptimizer/.env` 文件中安全地加载和保存`OCR_API_BASE_URL`, `OCR_API_KEY`等信息。
 - **UI集成**:
   - 在 `ui.main_window` 中新增一个 "PDF OCR" 标签页。
   - 创建新的 `OcrWorker` 线程，在后台执行PDF转换和API调用，避免UI阻塞。
   - 通过信号和槽机制 (`Signal`, `Slot`) 更新界面状态和进度。

- **Markdown转DOCX (Pandoc)**
  - 在OCR流程的最后，调用Pandoc命令行工具。
  - 通过 `subprocess.Popen` 将预处理和修复后的Markdown内容作为标准输入传递给Pandoc。
  - 明确启用 `+tex_math_dollars` 扩展，以确保行内和块级LaTeX公式都能被正确解析。
  - 命令示例: `pandoc -f markdown+tex_math_dollars -t docx -o output.docx`
- **打包为可执行文件 (PyInstaller)**
  - 安装 PyInstaller：  
    ```bash
    pip install pyinstaller
    ```  
  - 在项目根目录运行：  
    ```bash
     venv\Scripts\pyinstaller --name PDFOptimizer --noconfirm --onefile --windowed --icon="ui/app.ico" --add-data "ui/style.qss;ui" --add-data "ui/app.ico;ui" main.py
    ```
  - 为确保 `Ghostscript` 在打包后可用，可以将其安装目录下的 `bin` 和 `lib` 文件夹复制到项目根目录，并在打包时通过 `--add-data` 添加。
  - 打包结果位于 `dist/PDFOptimizer.exe`，是一个包含所有依赖的单文件可执行程序。
## 技术栈

- Python 3
- PySide6 (Qt for Python)
- pikepdf
- PyMuPDF
- Ghostscript
- Pandoc

## 反馈与建议

如果您在使用过程中遇到任何问题，或有任何功能建议，欢迎提出Issue或Pull Request。

## 许可证

本项目采用MIT许可证。详见[LICENSE](LICENSE)文件。
