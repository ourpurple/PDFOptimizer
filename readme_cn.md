# PDF Optimizer - PDF文件优化工具

一个功能强大的PDF文件优化工具，支持PDF压缩、合并和文本转曲等功能。

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

## 系统要求

- Windows操作系统
- Python 3.7+
- Ghostscript（可选，用于高级优化功能）

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
- 对于大文件处理可能需要较长时间，请耐心等待
- Ghostscript引擎可能提供更好的压缩效果，但处理速度相对较慢

## 技术栈

- Python 3
- PySide6 (Qt for Python)
- pikepdf
- Ghostscript

## 反馈与建议

如果您在使用过程中遇到任何问题，或有任何功能建议，欢迎提出Issue或Pull Request。

## 许可证

本项目采用MIT许可证。详见[LICENSE](LICENSE)文件。
