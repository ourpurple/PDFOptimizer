import os
import fitz  # PyMuPDF
from .utils import handle_exception


@handle_exception
def split_pdf(input_path, output_dir, page_progress_callback=None):
    """
    将 PDF 文件按页分割成多个单独的 PDF 文件。

    :param input_path: 输入 PDF 文件路径
    :param output_dir: 输出 PDF 存放目录
    :param page_progress_callback: 用于报告单个文件页面进度的回调函数
    :return: dict 分割结果
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with fitz.open(input_path) as doc:
        page_count = len(doc)
        base_name, _ = os.path.splitext(os.path.basename(input_path))
        num_digits = len(str(page_count))

        for page_num in range(page_count):
            page_str = str(page_num + 1).zfill(num_digits)
            output_filename = f"{base_name}[已分割][页面{page_str}].pdf"
            output_path = os.path.join(output_dir, output_filename)

            with fitz.open() as new_doc:
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                new_doc.save(output_path)

            if page_progress_callback:
                page_progress_callback(page_num + 1, page_count)

    return {"success": True, "message": f"成功将 PDF 分割成 {page_count} 个文件！"}


def batch_split_pdf(files, output_dir, worker_signals):
    total_files = len(files)
    for i, file_path in enumerate(files):
        if not worker_signals["is_running"]():
            break
        try:
            def page_progress_callback(current, total):
                if worker_signals.get("page_progress"):
                    worker_signals["page_progress"].emit(i, current, total)
            
            result = split_pdf(
                file_path,
                output_dir,
                page_progress_callback,
            )
            if result.get("success"):
                worker_signals["file_finished"].emit(
                    i, {"success": True, "message": result.get("message", "分割成功")}
                )
            else:
                worker_signals["file_finished"].emit(
                    i, {"success": False, "message": result.get("message", "未知错误")}
                )
        except Exception as e:
            worker_signals["file_finished"].emit(i, {"success": False, "message": str(e)})
        progress = int((i + 1) / total_files * 100)
        worker_signals["progress"].emit(progress)
