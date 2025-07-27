import os
import subprocess
from .utils import _get_gs_executable, get_subprocess_startup_info, handle_exception, logger

@handle_exception
def convert_to_curves_with_ghostscript(input_path, output_path):
    """
    使用 Ghostscript 将 PDF 文件中的文本转换为曲线。
    :param input_path: 输入 PDF 文件路径
    :param output_path: 输出 PDF 文件路径
    :return: dict 转换结果
    """
    gs_executable = _get_gs_executable()
    if not gs_executable:
        return {"success": False, "message": "未找到 Ghostscript 可执行文件，请安装 Ghostscript 并确保其在系统 PATH 中。"}

    cmd = [
        gs_executable,
        "-sDEVICE=pdfwrite",
        "-o", output_path,
        "-dNOPAUSE",
        "-dBATCH",
        "-dQUIET",
        "-dNoOutputFonts",
        input_path
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=get_subprocess_startup_info())
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        error_message = f"Ghostscript 转曲失败，返回码：{process.returncode}，错误信息：{stderr.strip()}"
        logger.error(error_message)
        return {"success": False, "message": error_message}

    original_size = os.path.getsize(input_path)
    converted_size = os.path.getsize(output_path)

    return {
        "success": True,
        "original_size": original_size,
        "optimized_size": converted_size,
        "message": "转曲成功！"
    }