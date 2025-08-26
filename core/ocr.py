import base64
import httpx
import os
import re
import time
from typing import List, Dict, Any, Optional, Callable
from mistralai import Mistral

from .utils import handle_exception, convert_markdown_to_docx_with_pandoc, preprocess_markdown_for_pandoc

def encode_image_to_base64(image_path: str) -> Optional[str]:
    """将图片文件编码为 Base64 字符串"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception:
        return None

def _process_with_openai_compatible(
    image_paths: List[str],
    api_key: str,
    model_name: str,
    api_base_url: str,
    prompt_text: str,
    timeout: int,
    logger: Any,
    temperature: float = 1.0,  # 添加温度参数，默认值为1.0
    progress_callback: Optional[Callable] = None,
    check_running: Optional[Callable] = lambda: True,
    pdf_path: Optional[str] = None,  # 添加PDF文件路径参数
    save_mode: str = "per_page",  # 添加保存模式参数
) -> str:
    """使用 OpenAI 兼容的 API 处理图片，并根据保存模式决定是否逐页保存结果"""
    
    full_markdown_content = []
    total_images = len(image_paths)
    
    # 创建输出目录
    md_dir = None
    word_dir = None
    base_name = None
    
    # 对于OpenAI-Compatible模式，使用第一个图片路径来推导基础信息
    if pdf_path:
        pdf_dir = os.path.dirname(pdf_path)
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    elif image_paths:
        # OpenAI-Compatible模式：从第一个图片路径推导
        first_image = image_paths[0]
        image_dir = os.path.dirname(first_image)
        # 尝试从图片文件名中提取基础名称（移除页码等后缀）
        image_name = os.path.basename(first_image)
        # 移除常见的页码后缀，如 _page001.png 或 -1.png
        base_name = re.sub(r'[_-]?(page)?\d+(\.png)?$', '', image_name)
        base_name = os.path.splitext(base_name)[0]
        pdf_dir = image_dir
    else:
        logger.warning("无法确定输出目录，将跳过逐页保存")
        pdf_dir = None
        base_name = None
    
    if pdf_dir and base_name:
        if save_mode == "per_page":
            md_dir = os.path.join(pdf_dir, f"{base_name}_md")
            word_dir = os.path.join(pdf_dir, f"{base_name}_word")
            
            # 创建目录
            os.makedirs(md_dir, exist_ok=True)
            logger.info(f"创建Markdown输出目录: {md_dir}")
            os.makedirs(word_dir, exist_ok=True)
            logger.info(f"创建Word输出目录: {word_dir}")
        
        logger.info(f"使用保存模式: {save_mode}，基础名称: {base_name}")

    for i, image_path in enumerate(image_paths):
        if not check_running():
            raise InterruptedError("OCR task was stopped.")
            
        logger.info(f"正在处理第 {i+1}/{total_images} 页: {os.path.basename(image_path)}")
            
        base64_image = encode_image_to_base64(image_path)
        if not base64_image:
            error_message = f"无法编码图片: {os.path.basename(image_path)}"
            logger.error(f"页面 {i+1} 处理失败: {error_message}")
            page_content = f"\n\n--- 页面 {i+1} 处理失败: {error_message} ---\n\n"
            full_markdown_content.append(page_content)
            if progress_callback:
                progress_callback(i + 1, total_images, error_message, "")
            continue
            
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
"temperature": temperature,  # 添加温度参数
            "max_tokens": 4096
        }
        
        page_content = ""
        max_retries = 3
        retry_delay = 2
        api_success = False

        for attempt in range(max_retries):
            if not check_running():
                raise InterruptedError("OCR task was stopped.")
            
            try:
                logger.info(f"页面 {i+1}: 第 {attempt + 1} 次尝试调用API...")
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(
                        f"{api_base_url}/chat/completions",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}"
                        },
                        json=payload
                    )
                    response.raise_for_status()
                    
                response_data = response.json()
                if "choices" not in response_data or not response_data["choices"]:
                    raise ValueError("API响应中缺少有效的 'choices' 字段")
                
                # 健壮地获取 content
                # 正确地从 'choices' 列表中获取第一个元素
                first_choice = response_data["choices"][0]  # 修复：获取列表的第一个元素
                message = first_choice.get("message", {})
                page_content = message.get("content", "")

                if not page_content:
                    logger.warning(f"页面 {i+1}: API返回了空的内容。")
                    # 如果内容为空，继续重试而不是标记为成功
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                else:
                    logger.info(f"页面 {i+1}: 第 {attempt + 1} 次尝试成功，内容长度: {len(page_content)} 字符。")
                    if progress_callback:
                        progress_callback(i + 1, total_images, "成功", page_content)
                    api_success = True
                    break
                    
                # 如果到达这里，说明内容为空且已达到最大重试次数
                logger.warning(f"页面 {i+1}: API返回空内容，已达到最大重试次数 {max_retries}。")
                
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                error_message = f"API请求失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
                logger.warning(f"页面 {i+1}: {error_message}")
                if progress_callback:
                    progress_callback(i + 1, total_images, f"API请求失败 (尝试 {attempt + 1})", "")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    final_error_message = f"API返回错误 (页面 {i+1}): {max_retries}次尝试后失败 - {str(e)}"
                    logger.error(f"页面 {i+1}: {final_error_message}")
                    page_content = f"\n\n--- {final_error_message} ---\n\n"
                    if progress_callback:
                        progress_callback(i + 1, total_images, "API 错误", "")

            except Exception as e:
                error_message = f"处理页面 {i+1} 时发生未知错误: {str(e)}"
                logger.error(f"页面 {i+1}: {error_message}", exc_info=True)
                page_content = f"\n\n--- {error_message} ---\n\n"
                if progress_callback:
                    progress_callback(i + 1, total_images, "未知错误", "")
                break
        
        if not api_success and not page_content:
            error_message = f"页面 {i+1}: 所有重试均失败，未能获取OCR内容"
            page_content = f"\n\n--- {error_message} ---\n\n"
            logger.error(f"页面 {i+1}: {error_message}")
        
        # 根据保存模式决定是否逐页保存结果
        if save_mode == "per_page" and pdf_path and base_name and md_dir:
            page_number = i + 1
            
            # 保存Markdown文件
            md_filename = f"{base_name}[P{page_number}].md"
            md_path = os.path.join(md_dir, md_filename)
            try:
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(page_content)
                logger.info(f"页面 {page_number} 的Markdown已保存: {md_path}")
            except Exception as e:
                logger.error(f"保存页面 {page_number} 的Markdown失败: {str(e)}")
            
            # 保存Word文件（如果安装了Pandoc）
            if word_dir:
                from .utils import is_pandoc_installed
                if is_pandoc_installed():
                    docx_filename = f"{base_name}[P{page_number}].docx"
                    docx_path = os.path.join(word_dir, docx_filename)
                    try:
                        processed_content = preprocess_markdown_for_pandoc(page_content)
                        conversion_result = convert_markdown_to_docx_with_pandoc(processed_content, docx_path)
                        if conversion_result["success"]:
                            logger.info(f"页面 {page_number} 的Word文件已保存: {docx_path}")
                        else:
                            logger.error(f"转换页面 {page_number} 的Word文件失败: {conversion_result['message']}")
                    except Exception as e:
                        logger.error(f"保存页面 {page_number} 的Word文件失败: {str(e)}")
                else:
                    logger.warning("未安装Pandoc，跳过Word文件转换")
        
        full_markdown_content.append(page_content)
    
    # 如果使用了逐页保存模式，额外创建合并文件
    if save_mode == "per_page" and pdf_path and base_name and md_dir:
        try:
            # 收集所有逐页Markdown文件
            md_files = []
            for i in range(len(image_paths)):
                page_number = i + 1
                md_filename = f"{base_name}[P{page_number}].md"
                md_path = os.path.join(md_dir, md_filename)
                if os.path.exists(md_path):
                    with open(md_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 添加页眉标识
                        md_files.append(f"<!-- 第 {page_number} 页 -->\n{content}")
            
            if md_files:
                # 创建合并的Markdown文件
                merged_md_content = "\n\n---\n\n".join(md_files)
                merged_md_filename = f"{base_name}[完整合并].md"
                merged_md_path = os.path.join(os.path.dirname(pdf_path), merged_md_filename)
                
                with open(merged_md_path, 'w', encoding='utf-8') as f:
                    f.write(merged_md_content)
                logger.info(f"合并的Markdown文件已保存: {merged_md_path}")
                
                # 创建合并的Word文件
                if word_dir and os.path.exists(word_dir):
                    from .utils import is_pandoc_installed
                    if is_pandoc_installed():
                        merged_docx_filename = f"{base_name}[完整合并].docx"
                        merged_docx_path = os.path.join(os.path.dirname(pdf_path), merged_docx_filename)
                        
                        processed_content = preprocess_markdown_for_pandoc(merged_md_content)
                        conversion_result = convert_markdown_to_docx_with_pandoc(processed_content, merged_docx_path)
                        
                        if conversion_result["success"]:
                            logger.info(f"合并的Word文件已保存: {merged_docx_path}")
                        else:
                            logger.error(f"合并Word文件转换失败: {conversion_result['message']}")
        
        except Exception as e:
            logger.error(f"创建合并文件时出错: {str(e)}")
    
    return "\n\n---\n\n".join(full_markdown_content)

def _process_with_mistral(
    pdf_path: str,
    api_key: str,
    model_name: str,
    prompt_text: str,
    timeout: int,
    logger: Any,
    progress_callback: Optional[Callable] = None,
    check_running: Optional[Callable] = lambda: True,
) -> str:
    """使用 Mistral API 直接处理 PDF 文件。"""
    logger.info(f"使用 Mistral API (模型: {model_name}) 处理 PDF: {os.path.basename(pdf_path)}")
    
    if not check_running():
        raise InterruptedError("OCR task was stopped.")
        
    try:
        if progress_callback:
            progress_callback(1, 1, "正在准备文件...", "")

        client = Mistral(api_key=api_key)
        
        logger.info("正在将PDF文件编码为Base64...")
        with open(pdf_path, "rb") as pdf_file:
            base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
        
        data_uri = f"data:application/pdf;base64,{base64_pdf}"
        logger.info("Data URI 创建成功。")

        if not check_running():
            raise InterruptedError("OCR task was stopped.")
            
        if progress_callback:
            progress_callback(1, 1, "正在调用 Mistral OCR API...", "")
        
        logger.info("正在调用 client.ocr.process...")
        
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": data_uri
            },
            include_image_base64=False  # Assuming we don't need images for now
        )

        logger.info(f"API 调用成功，收到 {len(ocr_response.pages)} 页结果。")
        if progress_callback:
            progress_callback(1, 1, "成功", "\n\n---\n\n".join([page.markdown for page in ocr_response.pages]))
            
        # 将所有页面的内容合并
        full_markdown_content = "\n\n---\n\n".join([page.markdown for page in ocr_response.pages])
        
        return full_markdown_content

    except Exception as e:
        error_message = f"调用 Mistral API 时发生错误: {str(e)}"
        logger.error(error_message, exc_info=True)
        # 返回一个包含错误信息的Markdown片段，以便在UI中显示
        return f"\n\n--- 调用 Mistral API 失败: {error_message} ---\n\n"

@handle_exception
def process_images_with_model(
    image_paths: List[str],
    pdf_path: Optional[str],
    api_provider: str,
    api_key: str,
    model_name: str,
    api_base_url: str,
    prompt_text: str,
    logger: Any,
    timeout: int = 120,
    temperature: float = 1.0,  # 添加温度参数，默认值为1.0
    save_mode: str = "per_page",  # 添加保存模式参数
    progress_callback: Optional[Callable] = None,
    check_running: Optional[Callable] = lambda: True,
) -> Dict[str, Any]:
    """
    将一系列图片或单个PDF发送给指定的视觉模型，并将结果合并为一个Markdown文档。
    这是一个分发器函数，会根据 api_provider 调用相应的实现。

    :param image_paths: 图片文件路径列表 (用于类OpenAI模型)
    :param pdf_path: PDF文件路径 (用于Mistral)
    :param api_provider: API 提供商名称 ("OpenAI-Compatible" or "Mistral API")
    :param api_key: API 密钥
    :param model_name: 模型名称 (e.g., gpt-4o)
    :param api_base_url: API 的基础 URL
    :param prompt_text: 指导模型处理图片的提示词
    :param logger: 日志记录器实例
    :param timeout: 请求超时时间（秒）
    :param progress_callback: 进度回调函数
    :param check_running: 用于检查任务是否应继续运行的回调函数
    :return: 包含处理结果的字典
    """
    
    final_markdown = ""
    processed_item_count = 0
    item_type = ""

    if api_provider == "Mistral API":
        if not pdf_path:
            raise ValueError("Mistral API 需要一个有效的 pdf_path。")
        item_type = "个PDF文件"
        processed_item_count = 1
        final_markdown = _process_with_mistral(
            pdf_path=pdf_path,
            api_key=api_key,
            model_name=model_name,
            prompt_text=prompt_text,
            timeout=timeout,
            logger=logger,
            progress_callback=progress_callback,
            check_running=check_running,
        )
    elif api_provider == "OpenAI-Compatible":
        item_type = "张图片"
        processed_item_count = len(image_paths)
        final_markdown = _process_with_openai_compatible(
            image_paths=image_paths,
            api_key=api_key,
            model_name=model_name,
            api_base_url=api_base_url,
            prompt_text=prompt_text,
            temperature=temperature,  # 传递温度参数
            timeout=timeout,
            logger=logger,
            progress_callback=progress_callback,
            check_running=check_running,
            pdf_path=pdf_path,  # 传递PDF路径用于创建输出目录
            save_mode=save_mode,  # 传递保存模式参数
        )
    else:
        raise ValueError(f"不支持的 API 提供商: {api_provider}")

    return {
        "success": True,
        "markdown_content": final_markdown,
        "message": f"成功调用 {api_provider} 模型处理了 {processed_item_count} {item_type}。"
    }