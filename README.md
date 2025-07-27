# PDF Optimizer

一个功能强大的PDF处理工具，支持PDF压缩、合并、分割、图像转换、文本转曲线转换和书签管理等功能。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)

## 功能特性

PDF Optimizer 提供了丰富的PDF处理功能：

1. **PDF优化** - 支持三种优化级别（低、中、高），可选择Pikepdf或Ghostscript引擎
2. **PDF合并** - 支持合并多个PDF文件，可通过拖拽调整文件顺序
3. **PDF分割** - 将多页PDF文件按页分割成多个独立的PDF文件
4. **PDF转图片** - 将PDF的每一页转换为JPG或PNG格式，支持自定义分辨率(DPI)
5. **PDF转曲** - 使用Ghostscript将PDF中的字体轮廓化，保证跨设备显示效果一致
6. **PDF书签** - 支持为PDF文件添加书签，支持批量添加和配置导入导出
7. **PDF OCR** - 使用AI模型进行OCR识别，支持OpenAI兼容API和Mistral API

## 技术栈

- **Python 3.10+**
- **PySide6** - 用于构建图形用户界面
- **Pikepdf** - 用于PDF处理
- **PyMuPDF** - 用于PDF和图像处理
- **Ghostscript** - 用于PDF优化和转曲功能（可选）
- **Pandoc** - 用于OCR结果转换为DOCX文件（可选）

## 安装说明

### 系统要求

- Python 3.10 或更高版本
- Ghostscript（用于转曲和GS引擎优化功能，可选）
- Pandoc（用于OCR结果转换为DOCX文件，可选）

### 安装步骤

1. 克隆项目仓库：
   ```bash
   git clone https://github.com/ourpurple/PDFOptimizer.git
   cd PDFOptimizer
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

### 运行应用

```bash
python main.py
```

## 使用方法

1. **PDF优化**：
   - 选择要优化的PDF文件
   - 选择优化质量（低质量、中等质量、高质量）
   - 选择优化引擎（Pikepdf或Ghostscript）
   - 点击"开始优化"按钮

2. **PDF合并**：
   - 选择要合并的PDF文件
   - 通过拖拽调整文件顺序
   - 选择合并引擎（Pikepdf或Ghostscript）
   - 点击"开始合并"按钮

3. **PDF分割**：
   - 选择要分割的PDF文件
   - 选择分割后文件的保存文件夹
   - 点击"开始分割"按钮

4. **PDF转图片**：
   - 选择要转换的PDF文件
   - 选择图片格式（JPG或PNG）
   - 设置分辨率（DPI）
   - 选择图片保存文件夹
   - 点击"开始转换"按钮

5. **PDF转曲**：
   - 选择要转曲的PDF文件
   - 点击"开始转曲"按钮（需要安装Ghostscript）

6. **PDF书签**：
   - 选择要添加书签的PDF文件
   - 编辑书签或导入书签配置
   - 点击"开始添加书签"按钮

7. **PDF OCR**：
   - 选择要进行OCR识别的PDF文件
   - 配置OCR参数（API提供商、API Key、模型名称等）
   - 点击"开始识别"按钮

## 项目结构

```
PDFOptimizer/
├── core/                 # 核心功能模块
│   ├── optimizer.py      # PDF优化功能
│   ├── merger.py         # PDF合并功能
│   ├── division.py       # PDF分割功能
│   ├── pdf2img.py        # PDF转图片功能
│   ├── converter.py      # PDF转曲功能
│   ├── add_bookmark.py   # PDF书签功能
│   ├── ocr.py            # PDF OCR功能
│   ├── utils.py          # 工具函数
│   └── version.py        # 版本信息
├── ui/                   # 用户界面文件
│   ├── main_window.py    # 主窗口界面
│   ├── custom_dialog.py  # 自定义对话框
│   ├── ocr_config_dialog.py  # OCR配置对话框
│   └── style.qss         # 样式表
├── main.py               # 程序入口
├── requirements.txt      # 依赖列表
└── README.md             # 项目说明文件
```

## 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细的版本更新信息。

## 许可证

本项目采用MIT许可证，详情请见 [LICENSE](LICENSE) 文件。

## 作者

WanderInDoor - 76757488@qq.com

项目地址: [https://github.com/ourpurple/PDFOptimizer](https://github.com/ourpurple/PDFOptimizer)