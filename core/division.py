import os
import fitz  # PyMuPDF
from .utils import handle_exception

@handle_exception
def split_pdf(input_path, output_dir, progress_callback=None):
    """
    将 PDF 文件按页分割成多个单独的 PDF 文件。

    :param input_path: 输入 PDF 文件路径
    :param output_dir: 输出 PDF 存放目录
    :param progress_callback: 用于报告进度的回调函数
    :return: dict 分割结果
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    doc = fitz.open(input_path)
    page_count = len(doc)
    base_name, _ = os.path.splitext(os.path.basename(input_path))
    num_digits = len(str(page_count))

    for page_num in range(page_count):
        page_str = str(page_num + 1).zfill(num_digits)
        output_filename = f"{base_name}[已分割][页面{page_str}].pdf"
        output_path = os.path.join(output_dir, output_filename)

        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        new_doc.save(output_path)
        new_doc.close()

        if progress_callback:
            progress_callback(page_num + 1, page_count)

    doc.close()

    return {
        "success": True,
        "message": f"成功将 PDF 分割成 {page_count} 个文件！"
    }