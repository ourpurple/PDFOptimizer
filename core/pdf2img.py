import os
import fitz  # PyMuPDF
from .utils import handle_exception


@handle_exception
def convert_pdf_to_images(
    input_path, output_dir, image_format="png", dpi=300, page_progress_callback=None
):
    """
    将 PDF 文件的每一页转换为图片。

    :param input_path: 输入 PDF 文件路径
    :param output_dir: 输出图片存放目录
    :param image_format: 图片格式 (png, jpg, etc.)
    :param dpi: 图片分辨率 (dots per inch)
    :param page_progress_callback: 用于报告单个文件页面进度的回调函数
    :return: dict 转换结果
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with fitz.open(input_path) as doc:
        page_count = len(doc)
        base_name, _ = os.path.splitext(os.path.basename(input_path))

        for page_num in range(page_count):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=dpi)
            num_digits = len(str(page_count))
            page_str = str(page_num + 1).zfill(num_digits)

            if page_count > 1:
                output_filename = f"{base_name}[DPI{dpi}][页面{page_str}].{image_format}"
            else:
                output_filename = f"{base_name}[DPI{dpi}].{image_format}"

            output_path = os.path.join(output_dir, output_filename)

            pix.save(output_path)
            if page_progress_callback:
                page_progress_callback(page_num + 1, page_count)

    return {"success": True, "message": f"成功将 PDF 转换为 {page_count} 张图片！"}


def batch_convert_pdf_to_images(files, output_dir, image_format, dpi, worker_signals):
    total_files = len(files)
    for i, file_path in enumerate(files):
        if not worker_signals["is_running"]():
            break
        try:
            
            def page_progress_callback(current, total):
                if worker_signals.get("page_progress"):
                    worker_signals["page_progress"].emit(i, current, total)

            result = convert_pdf_to_images(
                file_path,
                output_dir,
                image_format,
                dpi,
                page_progress_callback,
            )

            if result.get("success"):
                worker_signals["file_finished"].emit(
                    i,
                    {
                        "success": True,
                        "message": result.get("message", "转换成功"),
                    },
                )
            else:
                worker_signals["file_finished"].emit(
                    i,
                    {
                        "success": False,
                        "message": result.get("message", "未知错误"),
                    },
                )
        except Exception as e:
            worker_signals["file_finished"].emit(i, {"success": False, "message": str(e)})
        progress = int((i + 1) / total_files * 100)
        worker_signals["progress"].emit(progress)
