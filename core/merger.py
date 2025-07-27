import pikepdf
import subprocess
from .utils import _get_gs_executable, get_subprocess_startup_info, handle_exception, logger

@handle_exception
def merge_pdfs(input_paths: list, output_path: str, progress_callback=None):
    """
    Merges multiple PDF files into a single PDF file using pikepdf.
    """
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

@handle_exception
def merge_pdfs_with_ghostscript(input_paths: list, output_path: str, progress_callback=None):
    """
    使用 Ghostscript 命令行合并多个 PDF 文件。
    :param input_paths: PDF 文件路径列表
    :param output_path: 合并后输出文件路径
    :param progress_callback: 进度回调函数，接收 0-100 整数
    :return: dict 合并结果
    """
    gs_executable = _get_gs_executable()
    if not gs_executable:
        return {"success": False, "message": "未找到 Ghostscript 可执行文件，请安装 Ghostscript 并确保其在系统 PATH 中。"}

    cmd = [
        gs_executable,
        "-dBATCH",
        "-dNOPAUSE",
        "-q",
        "-sDEVICE=pdfwrite",
        f"-sOutputFile={output_path}"
    ] + input_paths

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=get_subprocess_startup_info())
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        error_message = f"Ghostscript 合并失败，返回码：{process.returncode}，错误信息：{stderr.strip()}"
        logger.error(error_message)
        return {"success": False, "message": error_message}

    if progress_callback:
        progress_callback(100)

    return {"success": True, "merged_files_count": len(input_paths), "output_path": output_path, "message": "PDF 合并成功！"}