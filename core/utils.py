import os
import shutil
import subprocess
import sys
import logging
import functools
import re

# 配置日志
LOG_FILE = "app_log.log"
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    filename=LOG_FILE,
    filemode='a',
    encoding='utf-8'
)
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
    主要功能：将代码块中的LaTeX公式“解放”出来。
    
    :param markdown_content: 原始的Markdown字符串。
    :return: 处理后的Markdown字符串。
    """
    # 正则表达式，用于匹配被错误地包裹在```...```代码块中的$$...$$公式
    # 它会捕获语言标识符（如latex, tex）以及公式本身
    # re.DOTALL 使得 . 可以匹配换行符
    pattern = re.compile(r"```[a-zA-Z]*\s*(\${2}.*?\${2})\s*```", re.DOTALL)
    
    # 使用一个函数来替换找到的匹配项
    def replacer(match):
        # 提取并返回捕获的公式内容（第一个捕获组）
        # .strip() 用于移除可能存在于公式前后的多余空白字符
        return match.group(1).strip()
        
    # 执行替换
    processed_content = pattern.sub(replacer, markdown_content)
    
    return processed_content


@handle_exception
def convert_markdown_to_docx_with_pandoc(markdown_content, docx_path):
    """
    使用 pandoc 将 Markdown 字符串转换为 DOCX 文件。
    :param markdown_content: Markdown 格式的字符串内容。
    :param docx_path: 输出的 DOCX 文件路径。
    :return: 包含 success 标志和消息的字典。
    """
    if not is_pandoc_installed():
        return {"success": False, "message": "未找到 Pandoc，请确保已正确安装并添加到系统PATH。"}

    try:
        # 使用 pandoc 将标准输入转换为 docx
        # 这避免了创建临时文件
        process = subprocess.Popen(
            ["pandoc", "-f", "markdown+tex_math_dollars", "-t", "docx", "-o", docx_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=get_subprocess_startup_info()
        )
        # 将 markdown 内容传递给 pandoc
        stdout, stderr = process.communicate(input=markdown_content.encode('utf-8'))

        if process.returncode != 0:
            error_message = f"Pandoc 转换失败: {stderr.decode('utf-8', 'ignore')}"
            logger.error(error_message)
            return {"success": False, "message": error_message}
            
        return {"success": True, "message": f"成功转换为: {docx_path}"}

    except FileNotFoundError:
        # 理论上 shutil.which 已经检查过，但作为备用
        return {"success": False, "message": "Pandoc 命令未找到。"}
    except Exception as e:
        error_message = f"使用 Pandoc 转换时发生未知错误: {str(e)}"
        logger.error(error_message, exc_info=True)
        return {"success": False, "message": error_message}