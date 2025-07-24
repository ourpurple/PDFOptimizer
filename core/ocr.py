import base64
import httpx
import os
from typing import List, Dict, Any, Optional

from .utils import handle_exception

def encode_image_to_base64(image_path: str) -> Optional[str]:
    """将图片文件编码为 Base64 字符串"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception:
        return None

@handle_exception
def process_images_with_model(
    image_paths: List[str],
    api_key: str,
    model_name: str,
    api_base_url: str = "https://api.openai.com/v1",
    prompt_text: str = "这是一个PDF页面。请准确识别所有内容，并将其转换为结构良好的Markdown格式。",
    timeout: int = 120,
    progress_callback=None
) -> Dict[str, Any]:
    """
    将一系列图片发送给兼容OpenAI的视觉模型，并将结果合并为一个Markdown文档。

    :param image_paths: 图片文件路径列表
    :param api_key: API 密钥
    :param model_name: 模型名称 (e.g., gpt-4o)
    :param api_base_url: API 的基础 URL
    :param prompt_text: 指导模型处理图片的提示词
    :param timeout: 请求超时时间（秒）
    :param progress_callback: 进度回调函数
    :return: 包含合并后 Markdown 文本的字典
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    full_markdown_content = []
    total_images = len(image_paths)

    for i, image_path in enumerate(image_paths):
        base64_image = encode_image_to_base64(image_path)
        if not base64_image:
            error_message = f"无法编码图片: {os.path.basename(image_path)}"
            full_markdown_content.append(f"\n\n--- 页面 {i+1} 处理失败: {error_message} ---\n\n")
            if progress_callback:
                progress_callback(i + 1, total_images, error_message)
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
            "max_tokens": 4096 
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    f"{api_base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()  # 如果状态码是 4xx 或 5xx，则引发异常
            
            page_content = response.json()["choices"][0]["message"]["content"]
            full_markdown_content.append(page_content)
            
            if progress_callback:
                progress_callback(i + 1, total_images)

        except httpx.HTTPStatusError as e:
            error_message = f"API返回错误 (页面 {i+1}): {e.response.status_code} - {e.response.text}"
            full_markdown_content.append(f"\n\n--- {error_message} ---\n\n")
            if progress_callback:
                progress_callback(i + 1, total_images, error_message)
        except Exception as e:
            error_message = f"处理页面 {i+1} 时发生未知错误: {str(e)}"
            full_markdown_content.append(f"\n\n--- {error_message} ---\n\n")
            if progress_callback:
                progress_callback(i + 1, total_images, error_message)

    final_markdown = "\n\n---\n\n".join(full_markdown_content)
    return {
        "success": True,
        "markdown_content": final_markdown,
        "message": f"成功处理 {total_images} 张图片。"
    }