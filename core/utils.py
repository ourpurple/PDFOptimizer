import os
import re
import shutil
import subprocess
import sys
import logging
import functools
import fitz  # PyMuPDF

# 日志配置已移除，使用默认logger
logger = logging.getLogger(__name__)

def handle_exception(func):
    """
    装饰器，用于捕获函数执行中的异常并记录日志。
    适用于返回字典结果的函数。
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_message = f"函数 '{func.__name__}' 执行异常: {str(e)}"
            logger.error(error_message, exc_info=True)
            return {"success": False, "message": error_message}
    return wrapper

def get_subprocess_startup_info():
    """
    为 subprocess.Popen 创建启动信息，以便在 Windows 上隐藏控制台窗口。
    在非 Windows 系统上返回 None。
    """
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    return startupinfo

# 缓存Ghostscript可执行文件路径
_GS_EXECUTABLE_PATH = None

def _get_gs_executable():
    """
    查找 Ghostscript 可执行文件。
    优先级: 环境变量 -> 打包路径 -> 系统 PATH。
    """
    global _GS_EXECUTABLE_PATH
    if _GS_EXECUTABLE_PATH:
        return _GS_EXECUTABLE_PATH

    # 1. 从环境变量中查找
    gs_exe = os.environ.get("GHOSTSCRIPT_EXECUTABLE")
    if gs_exe and shutil.which(gs_exe):
        _GS_EXECUTABLE_PATH = gs_exe
        return gs_exe

    # 2. PyInstaller 运行的临时路径中查找
    if hasattr(sys, '_MEIPASS'):
        # 对于 PyInstaller，gs 可能被打包在 _MEIPASS 目录
        bundled_gs = os.path.join(sys._MEIPASS, "gs", "gswin64c.exe") # 假设是64位
        if os.path.exists(bundled_gs):
            _GS_EXECUTABLE_PATH = bundled_gs
            return bundled_gs

    # 3. 在系统 PATH 中查找
    found_gs = shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c")
    _GS_EXECUTABLE_PATH = found_gs
    return found_gs

def is_ghostscript_installed():
    return _get_gs_executable() is not None

def is_pandoc_installed():
    """检查系统中是否安装了 pandoc"""
    return shutil.which("pandoc") is not None

def preprocess_markdown_for_pandoc(markdown_content: str) -> str:
    """
    预处理Markdown内容，以解决Pandoc转换的常见问题。
    此函数的唯一功能是将错误包裹在代码块（```）中的LaTeX数学公式（$$...$$）
    “解放”出来，使其能够被Pandoc正确识别。
    
    :param markdown_content: 原始的Markdown字符串。
    :return: 处理后的Markdown字符串，仅包含公式修正。
    """
    # 正则表达式，用于匹配被错误地包裹在```...```代码块中的$$...$$公式
    # 它会捕获语言标识符（如latex, tex）以及公式本身
    # re.DOTALL 使得 . 可以匹配换行符
    formula_pattern = re.compile(r"```[a-zA-Z]*\s*(\${2}.*?\${2})\s*```", re.DOTALL)
    
    # 使用一个函数来替换找到的匹配项
    def replacer(match):
        # 提取并返回捕获的公式内容（第一个捕获组）
        # .strip() 用于移除可能存在于公式前后的多余空白字符
        return match.group(1).strip()
        
    # 执行替换并返回结果
    return formula_pattern.sub(replacer, markdown_content)


@handle_exception
def convert_markdown_to_docx_with_pandoc(markdown_content, docx_path):
    """
    使用 pandoc 将 Markdown 字符串转换为 DOCX 文件。
    对于大文件，此方法通过写入临时文件来避免管道缓冲区问题。
    :param markdown_content: Markdown 格式的字符串内容。
    :param docx_path: 输出的 DOCX 文件路径。
    :return: 包含 success 标志和消息的字典。
    """
    if not is_pandoc_installed():
        return {"success": False, "message": "未找到 Pandoc，请确保已正确安装并添加到系统PATH。"}

    temp_md_path = None
    try:
        # 1. 创建一个临时 Markdown 文件
        # 在 docx 文件旁边创建临时文件，以确保权限一致
        base_name, _ = os.path.splitext(docx_path)
        temp_md_path = base_name + "_temp.md"
        with open(temp_md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        # 2. 调用 pandoc 读取临时文件进行转换
        cmd = [
            "pandoc",
            "-f", "markdown+tex_math_dollars+hard_line_breaks",
            "-t", "docx",
            "-o", docx_path,
            temp_md_path  # 从文件读取
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=get_subprocess_startup_info()
        )
        
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_message = f"Pandoc 转换失败: {stderr.decode('utf-8', 'ignore')}"
            logger.error(error_message)
            return {"success": False, "message": error_message}
            
        return {"success": True, "message": f"成功转换为: {docx_path}"}

    except FileNotFoundError:
        return {"success": False, "message": "Pandoc 命令未找到。"}
    except Exception as e:
        error_message = f"使用 Pandoc 转换时发生未知错误: {str(e)}"
        logger.error(error_message, exc_info=True)
        return {"success": False, "message": error_message}
    finally:
        # 3. 确保临时文件在操作结束后被删除
        if temp_md_path and os.path.exists(temp_md_path):
            try:
                os.remove(temp_md_path)
            except OSError as e:
                logger.error(f"删除临时文件 {temp_md_path} 失败: {e}")


@handle_exception
def convert_image_to_pdf(image_path, output_pdf_path):
    """
    将图片文件转换为PDF文件
    
    :param image_path: 图片文件路径
    :param output_pdf_path: 输出PDF文件路径
    :return: 包含 success 标志和消息的字典
    """
    try:
        # 创建一个新的PDF文档
        pdf_document = fitz.open()
        
        # 打开图片文件
        img_document = fitz.open(image_path)
        
        # 获取图片页面
        page = img_document[0]
        
        # 获取图片的尺寸
        img_rect = page.rect
        
        # 在PDF中创建一个新页面，尺寸与图片相同
        pdf_page = pdf_document.new_page(width=img_rect.width, height=img_rect.height)
        
        # 将图片插入到PDF页面中
        pdf_page.insert_image(img_rect, filename=image_path)
        
        # 保存PDF文件
        pdf_document.save(output_pdf_path)
        
        # 关闭文档
        pdf_document.close()
        img_document.close()
        
        return {
            "success": True,
            "message": f"图片已成功转换为PDF: {output_pdf_path}"
        }
        
    except Exception as e:
        error_message = f"图片转PDF失败: {str(e)}"
        logger.error(error_message, exc_info=True)
        return {
            "success": False,
            "message": error_message
        }