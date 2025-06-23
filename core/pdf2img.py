import os
import fitz  # PyMuPDF

def convert_pdf_to_images(input_path, output_dir, image_format="png", dpi=300, progress_callback=None):
    """
    将 PDF 文件的每一页转换为图片。

    :param input_path: 输入 PDF 文件路径
    :param output_dir: 输出图片存放目录
    :param image_format: 图片格式 (png, jpg, etc.)
    :param dpi: 图片分辨率 (dots per inch)
    :param progress_callback: 用于报告进度的回调函数
    :return: dict 转换结果
    """
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        doc = fitz.open(input_path)
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
            if progress_callback:
                progress_callback(page_num + 1, page_count)

        doc.close()

        return {
            "success": True,
            "message": f"成功将 PDF 转换为 {page_count} 张图片！"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"PDF 转图片异常: {str(e)}"
        }