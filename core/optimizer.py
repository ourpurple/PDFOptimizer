import os
import pikepdf
import subprocess
from .utils import _get_gs_executable, get_subprocess_startup_info, handle_exception, logger

@handle_exception
def optimize_pdf(input_path, output_path, quality_preset, progress_callback=None):
    """
    使用 pikepdf 进行 PDF 优化。
    :param input_path: 输入 PDF 文件路径
    :param output_path: 输出 PDF 文件路径
    :param quality_preset: 质量预设字符串，如 "低质量 (最大压缩)", "中等质量 (推荐)", "高质量 (轻度优化)"
    :param progress_callback: 进度回调函数，接收 0-100 整数
    :return: dict 优化结果
    """
    pdf = pikepdf.open(input_path)
    # 根据质量预设设置压缩参数
    if quality_preset == "低质量 (最大压缩)":
        compress_streams = True
        object_stream_mode = pikepdf.ObjectStreamMode.generate
        linearize = False
    elif quality_preset == "中等质量 (推荐)":
        compress_streams = True
        object_stream_mode = pikepdf.ObjectStreamMode.generate
        linearize = True
    else:  # 高质量 (轻度优化)
        compress_streams = False
        object_stream_mode = pikepdf.ObjectStreamMode.disable
        linearize = True

    pdf.save(
        output_path,
        min_version=pdf.pdf_version,
        object_stream_mode=object_stream_mode,
        compress_streams=compress_streams,
        linearize=linearize
    )
    pdf.close()

    original_size = os.path.getsize(input_path)
    optimized_size = os.path.getsize(output_path)

    if progress_callback:
        progress_callback(100)

    return {
        "success": True,
        "original_size": original_size,
        "optimized_size": optimized_size,
        "message": "优化成功！"
    }

@handle_exception
def optimize_pdf_with_ghostscript(input_path, output_path, quality_preset):
    """
    使用 Ghostscript 命令行优化 PDF 文件。
    :param input_path: 输入 PDF 文件路径
    :param output_path: 输出 PDF 文件路径
    :param quality_preset: 质量预设字符串，如 "低质量 (最大压缩)", "中等质量 (推荐)", "高质量 (轻度优化)"
    :return: dict 优化结果
    """
    gs_executable = _get_gs_executable()
    if not gs_executable:
        return {"success": False, "message": "未找到 Ghostscript 可执行文件，请安装 Ghostscript 并确保其在系统 PATH 中。"}

    quality_map = {
        "低质量 (最大压缩)": "/screen",
        "中等质量 (推荐)": "/ebook",
        "高质量 (轻度优化)": "/prepress"
    }
    pdf_setting = quality_map.get(quality_preset, "/ebook")

    cmd = [
        gs_executable,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={pdf_setting}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=get_subprocess_startup_info())
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        error_message = f"Ghostscript 优化失败，返回码：{process.returncode}，错误信息：{stderr.strip()}"
        logger.error(error_message)
        return {"success": False, "message": error_message}

    original_size = os.path.getsize(input_path)
    optimized_size = os.path.getsize(output_path)

    return {
        "success": True,
        "original_size": original_size,
        "optimized_size": optimized_size,
        "message": "优化成功！"
    }