import os
import shutil
import subprocess
import sys

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

def _get_gs_executable():
    """
    查找 Ghostscript 可执行文件。
    优先级: 环境变量 -> 打包路径 -> 系统 PATH。
    """
    # 1. 从环境变量中查找
    gs_exe = os.environ.get("GHOSTSCRIPT_EXECUTABLE")
    if gs_exe and shutil.which(gs_exe):
        return gs_exe

    # 2. PyInstaller 运行的临时路径中查找
    if hasattr(sys, '_MEIPASS'):
        # 对于 PyInstaller，gs 可能被打包在 _MEIPASS 目录
        bundled_gs = os.path.join(sys._MEIPASS, "gs", "gswin64c.exe") # 假设是64位
        if os.path.exists(bundled_gs):
            return bundled_gs

    # 3. 在系统 PATH 中查找
    return shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c")

def is_ghostscript_installed():
    return _get_gs_executable() is not None