import os
import shutil
import subprocess
import sys
import logging
import functools

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