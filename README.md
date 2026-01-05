# PDF Optimizer - PDF优化大师

一个功能强大、界面友好的PDF处理工具，支持PDF压缩、合并、分割、图像转换、字体转曲、书签管理和AI驱动的OCR识别等功能。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Version](https://img.shields.io/badge/version-3.4.2-green.svg)
![PixPin_2025-08-06_17-42-38.jpg](http://pic.mathe.cn/2025/08/06/f4a4242695d10.jpg)

## 🌟 功能特性

PDF Optimizer 提供了全方位的PDF处理解决方案：

### 📊 PDF优化（压缩）
- **三种压缩级别**：低质量（最大压缩）、中等质量（推荐）、高质量（轻度优化）
- **双引擎支持**：Pikepdf引擎（轻量级）和 Ghostscript引擎（专业级）
- **实时压缩率显示**：直观展示优化效果

### 📑 PDF合并
- **批量合并**：支持任意数量的PDF文件合并
- **可视化排序**：拖拽调整文件顺序，右键菜单快速操作
- **智能命名**：自动生成包含文件数量的合并文件名

### ✂️ PDF分割
- **按页分割**：将多页PDF分割为单页文件
- **智能命名**：自动添加页码标识，支持批量处理
- **保持质量**：分割过程不损失原始质量

### 🖼️ PDF转图片
- **多格式支持**：JPG、PNG格式输出
- **分辨率可调**：72/96/150/300/600 DPI可选
- **批量转换**：支持同时处理多个PDF文件

### 🎨 PDF转曲（字体轮廓化）
- **Ghostscript集成**：专业级字体转曲处理
- **跨平台兼容**：确保PDF在任何设备上显示一致
- **防止字体缺失**：彻底解决字体兼容性问题

### 🔖 PDF书签管理
- **可视化编辑**：图形化书签编辑界面
- **批量操作**：支持为多个文件添加相同书签
- **配置导入导出**：JSON格式书签配置，便于重复使用
- **智能跳转**：精确的书签定位功能

### 🤖 AI驱动的OCR识别
- **双AI引擎**：
  - **OpenAI兼容API**：支持GPT-4o、Claude-3.5-Sonnet等视觉模型
  - **Mistral API**：专用OCR模型，高精度识别
- **实时预览**：识别过程中实时显示结果
- **智能输出**：自动生成Markdown和Word文档
- **温度控制**：可调节AI输出的随机性（0.0-2.0）
- **智能命名**：文件名包含模型名称和时间戳

## 🛠️ 技术架构

### 核心技术栈
- **Python 3.10+**：现代Python语法，性能优化
- **PySide6**：Qt6的Python绑定，现代化GUI框架
- **Pikepdf**：高性能PDF处理库，支持PDF 2.0标准
- **PyMuPDF**：专业级PDF渲染和图像处理
- **Ghostscript**：业界标准的PDF处理引擎
- **httpx**：现代化HTTP客户端，支持异步请求

### 架构设计
- **模块化设计**：清晰的core和ui模块分离
- **异步处理**：QThread后台处理，界面零卡顿
- **跨平台支持**：Windows、macOS、Linux全平台兼容
- **插件式扩展**：易于添加新的PDF处理功能

## 📦 安装指南

### 系统要求
- **Python**：3.10或更高版本
- **操作系统**：Windows 10/11、macOS 10.15+、Linux
- **可选依赖**：
  - **Ghostscript**：用于转曲和GS引擎优化
  - **Pandoc**：用于OCR结果转换为Word文档

### 快速安装

#### 1. 克隆项目
```bash
git clone https://github.com/ourpurple/PDFOptimizer.git
cd PDFOptimizer
```

#### 2. 安装依赖
```bash
# 使用pip
pip install -r requirements.txt

# 或使用uv（推荐）
uv pip install -r requirements.txt
```

#### 3. 运行应用
```bash
python main.py
```

### 可选依赖安装

#### Windows
- **Ghostscript**：从[官网](https://www.ghostscript.com/download/gsdnld.html)下载安装
- **Pandoc**：从[官网](https://pandoc.org/installing.html)下载安装

#### macOS
```bash
# 使用Homebrew安装
brew install ghostscript pandoc
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install ghostscript pandoc

# CentOS/RHEL
sudo yum install ghostscript pandoc
```

## 🚀 使用指南

### 界面概览
应用采用标签页设计，每个功能都有独立的操作界面：

### 📊 PDF优化
1. 切换到"PDF优化"标签页
2. 点击"选择PDF文件"或拖拽文件到列表
3. 选择压缩质量（推荐"中等质量"）
4. 选择处理引擎（推荐"Pikepdf引擎"）
5. 点击"开始优化"

### 📑 PDF合并
1. 切换到"PDF合并"标签页
2. 添加需要合并的PDF文件
3. 拖拽调整文件顺序（可选）
4. 选择合并引擎
5. 点击"开始合并"并选择保存位置

### ✂️ PDF分割
1. 切换到"PDF分割"标签页
2. 选择要分割的PDF文件
3. 点击"开始分割"
4. 选择分割后文件的保存文件夹

### 🖼️ PDF转图片
1. 切换到"PDF转图片"标签页
2. 选择PDF文件
3. 设置图片格式（JPG/PNG）和分辨率（推荐300 DPI）
4. 选择图片保存文件夹
5. 点击"开始转换"

### 🎨 PDF转曲
1. 切换到"PDF转曲"标签页
2. 选择PDF文件（需要已安装Ghostscript）
3. 点击"开始转曲"

### 🔖 PDF书签
1. 切换到"PDF加书签"标签页
2. 选择PDF文件
3. 编辑书签（支持单个文件或共用书签）
4. 点击"开始添加书签"

### 🤖 PDF OCR
1. 切换到"PDF OCR"标签页
2. 选择单个PDF文件
3. 点击"配置"设置API参数
4. 点击"开始识别"
5. 结果自动保存为Markdown和Word文档

## ⚙️ 高级配置

### OCR配置
1. 点击OCR标签页的"配置"按钮
2. 选择API提供商（OpenAI兼容或Mistral）
3. 输入API密钥和基础URL
4. 选择AI模型（支持获取模型列表）
5. 调整温度参数（影响输出随机性）
6. 自定义提示词（高级用户）

### 环境变量
应用使用`.env`文件存储配置，位于：
- **Windows**: `%USERPROFILE%\.pdfoptimizer\.env`
- **macOS/Linux**: `~/.pdfoptimizer/.env`

## 📁 项目结构

```
PDFOptimizer/
├── core/                    # 核心功能模块
│   ├── __init__.py         # 模块导出
│   ├── optimizer.py        # PDF优化核心
│   ├── merger.py          # PDF合并核心
│   ├── division.py        # PDF分割核心
│   ├── pdf2img.py         # PDF转图片核心
│   ├── converter.py       # PDF转曲核心
│   ├── add_bookmark.py    # PDF书签核心
│   ├── ocr.py            # OCR识别核心
│   ├── utils.py          # 工具函数
│   └── version.py        # 版本信息
├── ui/                     # 用户界面
│   ├── main_window.py     # 主窗口
│   ├── custom_dialog.py   # 自定义对话框
│   ├── ocr_config_dialog.py  # OCR配置对话框
│   └── style.qss         # 样式表
├── main.py               # 程序入口
├── requirements.txt      # 依赖列表
├── pyproject.toml       # 项目配置
├── README.md           # 英文说明
├── README_CN.md        # 中文说明（本文件）
├── LICENSE             # 许可证
└── CHANGELOG.md        # 更新日志
```

## 🔄 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细的版本更新信息。

## 📦 发布新版本

项目使用 GitHub Actions 自动构建和发布。当推送版本 tag 时，会自动构建 Windows 可执行文件并创建 Release。

### 发布步骤

1. 更新版本号（`core/version.py`）
2. 更新 CHANGELOG.md
3. 提交更改并推送 tag：

```bash
git add .
git commit -m "Release vX.X.X"
git tag vX.X.X
git push origin main --tags
```

GitHub Actions 会自动：
- 在 Windows 环境下构建可执行文件
- 创建 Release 并上传 `PDFOptimizer.exe`

## 🤝 贡献指南

欢迎提交Issue和Pull Request！在贡献代码前，请：

1. 阅读项目代码规范
2. 确保所有测试通过
3. 更新相关文档
4. 遵循MIT许可证

## 📄 许可证

本项目采用MIT许可证，详情请见 [LICENSE](LICENSE) 文件。

## 👨‍💻 作者信息

- **作者**：WanderInDoor
- **邮箱**：76757488@qq.com
- **项目地址**：[https://github.com/ourpurple/PDFOptimizer](https://github.com/ourpurple/PDFOptimizer)
- **问题反馈**：[提交Issue](https://github.com/ourpurple/PDFOptimizer/issues)

## 💡 使用技巧

### 批量处理
- 支持多文件同时处理
- 拖拽文件到界面快速添加
- 右键菜单提供快捷操作

### 性能优化
- 大文件建议使用Ghostscript引擎
- OCR识别建议使用高性能AI模型
- 批量处理时避免同时运行多个任务

### 故障排除
- 检查Ghostscript和Pandoc是否安装
- 查看日志文件`app_log.log`获取详细错误信息
- OCR失败时检查API密钥和网络连接