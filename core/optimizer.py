import os
import pikepdf
import subprocess
import shutil
import sys
import traceback

def get_subprocess_startup_info():
    """
    为 subprocess.Popen 创建启动信息，以便在 Windows 上隐藏控制台窗口。
    """
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo
    return None

def optimize_pdf(input_path, output_path, quality_preset, progress_callback=None):
    """
    使用 pikepdf 进行 PDF 优化。
    :param input_path: 输入 PDF 文件路径
    :param output_path: 输出 PDF 文件路径
    :param quality_preset: 质量预设字符串，如 "低质量 (最大压缩)", "中等质量 (推荐)", "高质量 (轻度优化)"
    :param progress_callback: 进度回调函数，接收 0-100 整数
    :return: dict 优化结果
    """
    try:
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
    except Exception as e:
        tb = traceback.format_exc()
        return {
            "success": False,
            "message": f"优化失败: {str(e)}\n详细信息:\n{tb}"
        }

def convert_to_curves_with_ghostscript(input_path, output_path):
    """
    使用 Ghostscript 将 PDF 文件中的文本转换为曲线。
    :param input_path: 输入 PDF 文件路径
    :param output_path: 输出 PDF 文件路径
    :return: dict 转换结果
    """
    gs_executable = shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c")
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

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=get_subprocess_startup_info())
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            return {"success": False, "message": f"Ghostscript 转曲失败: {stderr.strip()}"}

        original_size = os.path.getsize(input_path)
        converted_size = os.path.getsize(output_path)

        return {
            "success": True,
            "original_size": original_size,
            "optimized_size": converted_size,
            "message": "转曲成功！"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Ghostscript 转曲异常: {str(e)}"
        }

def is_ghostscript_installed():
    return shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c")

def optimize_pdf_with_ghostscript(input_path, output_path, quality_preset):
    """
    使用 Ghostscript 命令行优化 PDF 文件。
    :param input_path: 输入 PDF 文件路径
    :param output_path: 输出 PDF 文件路径
    :param quality_preset: 质量预设字符串，如 "低质量 (最大压缩)", "中等质量 (推荐)", "高质量 (轻度优化)"
    :return: dict 优化结果
    """
    if not is_ghostscript_installed():
        return {"success": False, "message": "未找到 Ghostscript 可执行文件，请安装 Ghostscript 并确保其在系统 PATH 中。"}

    gs_executable = shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c")

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

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=get_subprocess_startup_info())
        stdout, stderr = process.communicate()
    except Exception as e:
        return {"success": False, "message": f"Ghostscript 优化异常: {str(e)}"}

    if process.returncode != 0:
        return {"success": False, "message": f"Ghostscript 优化失败: {stderr.strip()}"}

    original_size = os.path.getsize(input_path)
    optimized_size = os.path.getsize(output_path)

    return {
        "success": True,
        "original_size": original_size,
        "optimized_size": optimized_size,
        "message": "优化成功！"
    }

def merge_pdfs(input_paths: list, output_path: str, progress_callback=None):
    """
    Merges multiple PDF files into a single PDF file using pikepdf.
    """
    try:
        if not input_paths:
            return {"success": False, "message": "没有选择任何PDF文件进行合并。"}

        pdf = pikepdf.Pdf.new()
        total_files = len(input_paths)
        for i, file_path in enumerate(input_paths):
            if progress_callback:
                progress_callback(int((i / total_files) * 100))
            with pikepdf.open(file_path) as src:
                pdf.pages.extend(src.pages)
        pdf.save(output_path)
        pdf.close()
        if progress_callback:
            progress_callback(100)
        return {
            "success": True,
            "merged_files_count": total_files,
            "output_path": output_path,
            "message": "PDF 合并成功！"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"PDF 合并失败: {str(e)}"
        }

def merge_pdfs_with_ghostscript(input_paths: list, output_path: str, progress_callback=None):
    """
    使用 Ghostscript 命令行合并多个 PDF 文件。
    :param input_paths: PDF 文件路径列表
    :param output_path: 合并后输出文件路径
    :param progress_callback: 进度回调函数，接收 0-100 整数
    :return: dict 合并结果
    """
    if not is_ghostscript_installed():
        return {"success": False, "message": "未找到 Ghostscript 可执行文件，请安装 Ghostscript 并确保其在系统 PATH 中。"}

    gs_executable = shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c")

    cmd = [
        gs_executable,
        "-dBATCH",
        "-dNOPAUSE",
        "-q",
        "-sDEVICE=pdfwrite",
        f"-sOutputFile={output_path}"
    ] + input_paths

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=get_subprocess_startup_info())
        stdout, stderr = process.communicate()
    except Exception as e:
        return {"success": False, "message": f"Ghostscript 合并异常: {str(e)}"}

    if process.returncode != 0:
        return {"success": False, "message": f"Ghostscript 合并失败: {stderr.strip()}"}

    if progress_callback:
        progress_callback(100)

    return {"success": True, "merged_files_count": len(input_paths), "output_path": output_path, "message": "PDF 合并成功！"}