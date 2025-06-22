# PDF Optimizer - PDF文件优化工具

一个功能强大的PDF文件优化工具，支持PDF压缩、合并和文本转曲（印刷级）等功能。

## 主要功能

- 📦 PDF文件压缩优化
  - 支持三种质量预设：低质量(最大压缩)、中等质量(推荐)、高质量(轻度优化)
  - 同时支持pikepdf和Ghostscript两种优化引擎

- 🔄 PDF文件合并
  - 支持多个PDF文件合并
  - 支持拖拽排序确定合并顺序

- ✏️ PDF文本转曲
  - 使用Ghostscript将文本转换为曲线
  - 确保字体显示一致性

- 🎨 友好的用户界面
  - 简洁直观的操作界面
  - 支持文件拖拽
  - 实时显示处理进度
  - 详细的处理结果反馈
  
  ## 界面截图
  
  ![界面截图](http://pic.mathe.cn/2025/06/21/054a212c338bd.jpg)
  
  ## 系统要求

- Windows操作系统
- Python 3.7+
- Ghostscript (可选，但推荐安装以使用全部功能)

## 安装说明

1. 克隆或下载本项目代码
```bash
git clone https://github.com/yourusername/PDFOptimizer.git
```

2. 安装依赖包
```bash
pip install -r requirements.txt
```

3. 安装Ghostscript（可选）
- 从[Ghostscript官网](https://www.ghostscript.com/releases/gsdnld.html)下载并安装
- 确保Ghostscript已添加到系统环境变量PATH中

## 使用方法

1. 运行程序
```bash
python main.py
```

2. PDF文件优化
   - 点击"添加文件"或直接拖拽PDF文件到程序窗口
   - 选择期望的质量预设
   - 选择优化引擎（pikepdf或Ghostscript）
   - 点击"开始优化"

3. PDF文件合并
   - 添加多个PDF文件
   - 通过拖拽调整文件顺序
   - 点击"合并PDF"

4. PDF文本转曲
   - 添加需要处理的PDF文件
   - 点击"转曲处理"
   - 等待处理完成

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

- **图形界面 (PySide6)**  
  - 使用 `QMainWindow` 和 `QTabWidget` 构建主窗口及三个功能页。  
  - 采用自定义 `SortableTableWidget`，重写拖拽事件 (`dragEnterEvent`, `dragMoveEvent`, `dropEvent`) 和右键菜单 (`contextMenuEvent`)，支持文件列表的拖拽排序、删除、上移/下移和打开文件所在位置。
  - 基于 `QThread`（封装为 `BaseWorker`）实现多线程处理，使用 `Signal` 实时更新进度条和表格状态。  
  - 资源路径通过 `resource_path` 处理，兼容开发环境与 PyInstaller 打包的 `_MEIPASS` 目录。

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
- Ghostscript

## 反馈与建议

如果您在使用过程中遇到任何问题，或有任何功能建议，欢迎提出Issue或Pull Request。

## 许可证

本项目采用MIT许可证。详见[LICENSE](LICENSE)文件。
