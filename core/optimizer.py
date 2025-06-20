import os
import pikepdf
import fitz  # PyMuPDF
from PIL import Image
import io
import subprocess
import sys

# 定义优化预设
# (dpi, jpeg_quality)
OPTIMIZATION_PRESETS = {
    "低质量 (最大压缩)": (96, 75),
    "中等质量 (推荐)": (150, 85),
    "高质量 (轻度优化)": (225, 95)
}

def optimize_pdf(input_path: str, output_path: str, quality_preset: str, progress_callback=None):
    """
    Optimizes a PDF file by re-compressing images and saving with pikepdf.

    :param input_path: Path to the input PDF file.
    :param output_path: Path to save the optimized PDF file.
    :param quality_preset: A string key for OPTIMIZATION_PRESETS.
    :param progress_callback: A function to call with progress updates (0-100).
    """
    try:
        dpi, jpeg_quality = OPTIMIZATION_PRESETS[quality_preset]
        
        # 使用 PyMuPDF 打开文档
        pdf_doc = fitz.open(input_path)
        
        num_pages = len(pdf_doc)
        
        for page_num, page in enumerate(pdf_doc):
            if progress_callback:
                progress_callback(int((page_num / num_pages) * 50)) # 0-50% for image processing
                
            img_list = page.get_images(full=True)
            for img_index, img_info in enumerate(img_list):
                xref = img_info[0]
                base_image = pdf_doc.extract_image(xref)
                
                image_bytes = base_image["image"]
                
                # 将图片读入Pillow
                pil_image = Image.open(io.BytesIO(image_bytes))

                # 如果是 CMYK，转为 RGB
                if pil_image.mode == 'CMYK':
                    pil_image = pil_image.convert('RGB')
                
                # 重新压缩图片
                output_buffer = io.BytesIO()
                pil_image.save(output_buffer, format="JPEG", quality=jpeg_quality, optimize=True)
                
                # 替换旧图片
                page.replace_image(xref, stream=output_buffer.getvalue())

        if progress_callback:
            progress_callback(75) # 75% after image processing
            
        # 保存到一个临时文件
        temp_path = output_path + ".tmp"
        pdf_doc.save(temp_path, garbage=4, deflate=True, clean=True)
        pdf_doc.close()

        # 使用 pikepdf 进行无损压缩和修复
        pdf = pikepdf.open(temp_path)
        pdf.save(output_path,
                 min_version=pdf.pdf_version,
                 object_stream_mode=pikepdf.ObjectStreamMode.generate,
                 compress_streams=True,
                 linearize=True)
        pdf.close()
        
        # 删除临时文件
        os.remove(temp_path)

        if progress_callback:
            progress_callback(100) # 100% done

        original_size = os.path.getsize(input_path)
        optimized_size = os.path.getsize(output_path)
        
        return {
            "success": True,
            "original_size": original_size,
            "optimized_size": optimized_size,
            "message": "优化成功！"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"优化失败: {str(e)}"
        }

import shutil

def is_ghostscript_installed():
    """Checks if Ghostscript is installed and in the system's PATH."""
    return shutil.which("gswin64c") is not None or shutil.which("gs") is not None

def convert_to_curves_with_ghostscript(input_path: str, output_path: str, progress_callback=None):
    """
    Converts all text in a PDF to curves using Ghostscript.
    This is a very reliable method suitable for printing.
    """
    try:
        # Ghostscript command
        # -o output file
        # -sDEVICE=pdfwrite : sets the output device
        # -dNoOutputFonts : converts fonts to outlines
        # input file
        gs_command = [
            "gswin64c",  # Or "gs" on Linux/macOS
            "-o", output_path,
            "-sDEVICE=pdfwrite",
            "-dNoOutputFonts",
            input_path
        ]

        # Using subprocess to run the command
        # Using subprocess to run the command, hiding the console window on Windows
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        process = subprocess.run(gs_command, check=True, capture_output=True, text=True, startupinfo=startupinfo)
        
        # If we are here, it means Ghostscript ran successfully.
        if progress_callback:
            progress_callback(100)

        original_size = os.path.getsize(input_path)
        final_size = os.path.getsize(output_path)

        return {
            "success": True,
            "original_size": original_size,
            "optimized_size": final_size,
            "message": "文件转曲成功 (使用 Ghostscript)！"
        }
    except FileNotFoundError:
        # This error occurs if Ghostscript is not installed or not in the system's PATH
        return {
            "success": False,
            "message": "错误：找不到 Ghostscript。请确保它已安装并已添加到系统环境变量 PATH 中。"
        }
    except subprocess.CalledProcessError as e:
        # This error occurs if Ghostscript returns a non-zero exit code
        return {
            "success": False,
            "message": f"Ghostscript 执行失败: {e.stderr}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"发生未知错误: {str(e)}"
        }

def optimize_pdf_with_ghostscript(input_path: str, output_path: str, quality_preset: str, progress_callback=None):
    """
    Optimizes a PDF file using Ghostscript.
    """
    try:
        # Map our quality presets to Ghostscript's -dPDFSETTINGS
        # See: https://www.ghostscript.com/doc/current/VectorDevices.htm#PDFSETTINGS
        gs_quality_map = {
            "低质量 (最大压缩)": "/screen",
            "中等质量 (推荐)": "/ebook",
            "高质量 (轻度优化)": "/printer"
        }
        
        pdf_settings = gs_quality_map.get(quality_preset, "/ebook") # Default to ebook

        gs_command = [
            "gswin64c",  # Or "gs" on Linux/macOS
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={pdf_settings}",
            "-dNOPAUSE",
            "-dBATCH",
            "-dQUIET",
            f"-o{output_path}",
            input_path
        ]

        # Using subprocess to run the command, hiding the console window on Windows
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        process = subprocess.run(gs_command, check=True, capture_output=True, text=True, startupinfo=startupinfo)
        
        if progress_callback:
            progress_callback(100)

        original_size = os.path.getsize(input_path)
        optimized_size = os.path.getsize(output_path)
        
        return {
            "success": True,
            "original_size": original_size,
            "optimized_size": optimized_size,
            "message": "使用 Ghostscript 优化成功！"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": "错误：找不到 Ghostscript。请确保它已安装并已添加到系统环境变量 PATH 中。"
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "message": f"Ghostscript 执行失败: {e.stderr}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"发生未知错误: {str(e)}"
        }



if __name__ == '__main__':
    # For testing purposes
    # Create a dummy PDF with an image to test optimization
    # This part requires a sample image file 'sample_image.png'
    if not os.path.exists("test_in.pdf"):
        # Create a dummy image
        try:
            img = Image.new('RGB', (1024, 768), color = 'red')
            img.save('sample_image.png', 'PNG')
            
            doc = fitz.open()
            page = doc.new_page()
            rect = fitz.Rect(50, 50, 450, 450)
            page.insert_image(rect, "sample_image.png")
            doc.save("test_in.pdf")
            doc.close()
            print("Created a dummy 'test_in.pdf' for testing.")

        except Exception as e:
            print(f"Could not create dummy PDF. Please provide 'test_in.pdf'. Error: {e}")


    if os.path.exists("test_in.pdf"):
        print("Testing PDF optimization...")
        result = optimize_pdf("test_in.pdf", "test_out.pdf", "中等质量 (推荐)", lambda p: print(f"Progress: {p}%"))
        
        if result["success"]:
            orig_size_kb = result['original_size'] / 1024
            opt_size_kb = result['optimized_size'] / 1024
            reduction = ((orig_size_kb - opt_size_kb) / orig_size_kb) * 100
            print(f"Optimization successful!")
            print(f"Original size: {orig_size_kb:.2f} KB")
            print(f"Optimized size: {opt_size_kb:.2f} KB")
            print(f"Size reduction: {reduction:.2f}%")
        else:
            print(result["message"])