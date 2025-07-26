import base64
import httpx
import os
import time
import re
import shutil
import logging
import abc
import cProfile
import pstats
import io
from typing import List, Dict, Any, Optional, Callable
from mistralai import Mistral

from .utils import handle_exception
from ui import constants as const


def encode_image_to_base64(image_path: str) -> Optional[str]:
    """将图片文件编码为 Base64 字符串"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception:
        return None


class OcrProvider(abc.ABC):
    """OCR 提供商的抽象基类"""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        prompt_text: str,
        logger: logging.Logger,
        api_base_url: Optional[str] = None,
        timeout: int = 120,
        progress_callback: Optional[Callable] = None,
        check_running: Optional[Callable] = lambda: True,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.prompt_text = prompt_text
        self.logger = logger
        self.api_base_url = api_base_url
        self.timeout = timeout
        self.progress_callback = progress_callback
        self.check_running = check_running

    @property
    @abc.abstractmethod
    def needs_images(self) -> bool:
        """提供商是否需要将PDF转换为图像"""
        pass

    @abc.abstractmethod
    def perform_ocr(
        self, file_path: Optional[str] = None, image_paths: Optional[List[str]] = None
    ) -> str:
        """
        执行OCR处理。
        子类必须实现此方法。
        :param file_path: PDF文件的路径 (例如给 Mistral)
        :param image_paths: 图像文件路径列表 (例如给 OpenAI)
        :return: Markdown格式的OCR结果字符串
        """
        pass


class OpenAICompatibleProvider(OcrProvider):
    """使用 OpenAI 兼容 API 的 OCR 提供商"""

    @property
    def needs_images(self) -> bool:
        return True

    def perform_ocr(
        self, file_path: Optional[str] = None, image_paths: Optional[List[str]] = None
    ) -> str:
        if not image_paths:
            raise ValueError("OpenAI-compatible provider requires image paths.")

        full_markdown_content = []
        total_images = len(image_paths)

        for i, image_path in enumerate(image_paths):
            if not self.check_running():
                raise InterruptedError("OCR task was stopped.")

            self.logger.info(
                f"Processing page {i+1}/{total_images}: {os.path.basename(image_path)}"
            )

            base64_image = encode_image_to_base64(image_path)
            if not base64_image:
                error_message = f"Failed to encode image: {os.path.basename(image_path)}"
                self.logger.error(f"Page {i+1} processing failed: {error_message}")
                page_content = f"\n\n--- Page {i+1} failed: {error_message} ---\n\n"
                full_markdown_content.append(page_content)
                if self.progress_callback:
                    self.progress_callback(i + 1, total_images, error_message, "")
                continue

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                "max_tokens": 4096,
            }

            page_content = ""
            max_retries = 3
            retry_delay = 2
            api_success = False

            for attempt in range(max_retries):
                if not self.check_running():
                    raise InterruptedError("OCR task was stopped.")
                try:
                    self.logger.info(
                        f"Page {i+1}: Attempting to call API (attempt {attempt + 1})..."
                    )
                    with httpx.Client(timeout=self.timeout) as client:
                        response = client.post(
                            f"{self.api_base_url}/chat/completions",
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {self.api_key}",
                            },
                            json=payload,
                        )
                        response.raise_for_status()
                    response_data = response.json()
                    if "choices" not in response_data or not response_data["choices"]:
                        raise ValueError("Invalid 'choices' field in API response")

                    first_choice = response_data["choices"]
                    message = first_choice.get("message", {})
                    page_content = message.get("content", "")

                    if not page_content:
                        self.logger.warning(f"Page {i+1}: API returned empty content.")
                    self.logger.info(
                        f"Page {i+1}: Attempt {attempt + 1} successful, content length: {len(page_content)}."
                    )
                    if self.progress_callback:
                        self.progress_callback(i + 1, total_images, "Success", page_content)
                    api_success = True
                    break
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    error_message = (
                        f"API request failed (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    self.logger.warning(f"Page {i+1}: {error_message}")
                    if self.progress_callback:
                        self.progress_callback(
                            i + 1, total_images, f"API Request Failed (Attempt {attempt + 1})", ""
                        )
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        page_content = f"\n\n--- API Error (Page {i+1}): Failed after {max_retries} attempts - {e} ---\n\n"
                        self.logger.error(page_content)
                except Exception as e:
                    page_content = f"\n\n--- Unknown error on page {i+1}: {e} ---\n\n"
                    self.logger.error(page_content, exc_info=True)
                    break
            
            if not api_success:
                 page_content = f"\n\n--- All retries failed for page {i+1} ---\n\n"
                 self.logger.error(page_content)


            full_markdown_content.append(page_content)

        return "\n\n---\n\n".join(full_markdown_content)


class MistralProvider(OcrProvider):
    """使用 Mistral API 的 OCR 提供商"""

    @property
    def needs_images(self) -> bool:
        return False

    def perform_ocr(
        self, file_path: Optional[str] = None, image_paths: Optional[List[str]] = None
    ) -> str:
        if not file_path:
            raise ValueError("Mistral provider requires a PDF file path.")

        self.logger.info(
            f"Processing PDF with Mistral API (model: {self.model_name}): {os.path.basename(file_path)}"
        )
        if not self.check_running():
            raise InterruptedError("OCR task was stopped.")

        try:
            if self.progress_callback:
                self.progress_callback(1, 1, "Preparing file...", "")
            
            client = Mistral(api_key=self.api_key)
            
            self.logger.info("Encoding PDF to Base64...")
            with open(file_path, "rb") as pdf_file:
                base64_pdf = base64.b64encode(pdf_file.read()).decode("utf-8")
            data_uri = f"data:application/pdf;base64,{base64_pdf}"
            self.logger.info("Data URI created successfully.")

            if not self.check_running():
                raise InterruptedError("OCR task was stopped.")

            if self.progress_callback:
                self.progress_callback(1, 1, "Calling Mistral OCR API...", "")
            self.logger.info("Calling client.ocr.process...")

            ocr_response = client.ocr.process(
                model=self.model_name,
                document={"type": "document_url", "document_url": data_uri},
                include_image_base64=False,
            )

            self.logger.info(f"API call successful, received {len(ocr_response.pages)} pages.")
            full_markdown_content = "\n\n---\n\n".join(
                [page.markdown for page in ocr_response.pages]
            )
            if self.progress_callback:
                self.progress_callback(1, 1, "Success", full_markdown_content)
            
            return full_markdown_content

        except Exception as e:
            error_message = f"An unexpected error occurred with Mistral provider: {e}"
            self.logger.error(error_message, exc_info=True)
            return f"\n\n--- Mistral API Failed: {error_message} ---\n\n"

def get_ocr_provider(
    api_provider: str, **kwargs
) -> OcrProvider:
    """
    OCR 提供商工厂函数。
    """
    providers = {
        const.OCR_PROVIDER_OPENAI: OpenAICompatibleProvider,
        const.OCR_PROVIDER_MISTRAL: MistralProvider,
    }
    provider_class = providers.get(api_provider)
    if not provider_class:
        raise ValueError(f"Unsupported API provider: {api_provider}")
    return provider_class(**kwargs)

def _setup_ocr_logger(file_path: str) -> logging.Logger:
    """为当前OCR任务配置独立的日志记录器"""
    log_filename = os.path.splitext(file_path) + ".log"
    logger_name = f"OcrLogger_{os.path.basename(file_path)}"
    
    logger = logging.getLogger(logger_name)
    
    # 防止重复添加handler
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_filename, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def run_ocr_on_file(**kwargs):
    """
    对单个文件执行完整的 OCR 流程，并根据需要进行性能分析。
    """
    file_path = kwargs.get("file_path")
    worker_signals = kwargs.get("worker_signals")
    temp_dir = kwargs.get("temp_dir")
    enable_profiling = kwargs.get("enable_profiling", False)

    if not all([file_path, worker_signals, temp_dir]):
        raise ValueError("OCR 任务缺少 file_path, worker_signals, 或 temp_dir。")

    is_running = worker_signals["is_running"]
    logger = _setup_ocr_logger(file_path)
    image_output_dir = None
    
    profiler = cProfile.Profile() if enable_profiling else None
    if profiler:
        profiler.enable()
        logger.info("性能分析已启动。")

    try:
        if not is_running(): return
        
        logger.info(f"===== {const.OCR_TASK_STARTED}: {os.path.basename(file_path)} =====")
        
        api_provider_name = kwargs.get("api_provider")
        logger.info(f"{const.OCR_PROVIDER_USED}: {api_provider_name}")

        provider = get_ocr_provider(
            api_provider=api_provider_name,
            api_key=kwargs.get("api_key"),
            model_name=kwargs.get("model_name"),
            prompt_text=kwargs.get("prompt_text"),
            logger=logger,
            api_base_url=kwargs.get("api_base_url"),
            check_running=is_running,
            progress_callback=lambda current, total, msg, content="": worker_signals["preview_updated"].emit(content) or worker_signals["status_updated"].emit(f"{const.OCR_AI_PROCESSING}: {current}/{total} {const.PAGE_UNIT} - {msg}") or worker_signals["progress"].emit(int(current/total*100))
        )

        image_paths = []
        if provider.needs_images:
            worker_signals["status_updated"].emit(const.OCR_CONVERTING_PDF_TO_IMAGES)
            logger.info(const.OCR_STEP_1_CONVERT_TO_IMAGES)
            
            from core.images import convert_pdf_to_images
            
            file_name_without_ext = os.path.splitext(os.path.basename(file_path))
            image_output_dir = os.path.join(temp_dir, file_name_without_ext)
            if os.path.exists(image_output_dir): shutil.rmtree(image_output_dir)
            os.makedirs(image_output_dir)
            
            convert_result = convert_pdf_to_images(file_path, image_output_dir, dpi=200)
            if not convert_result["success"]:
                raise Exception(f"{const.OCR_PDF_TO_IMAGE_FAILED}: {convert_result['message']}")
                
            logger.info(const.OCR_PDF_TO_IMAGE_SUCCESS)
            image_paths = sorted([os.path.join(image_output_dir, f) for f in os.listdir(image_output_dir) if f.lower().endswith(".png")], key=lambda x: int(re.search(r'(\d+)', os.path.basename(x)).group(1)) if re.search(r'(\d+)', os.path.basename(x)) else 0)
            if not image_paths: raise Exception(const.OCR_NO_IMAGES_GENERATED)

        worker_signals["status_updated"].emit(const.OCR_CALLING_AI_MODEL)
        logger.info(const.OCR_STEP_2_CALL_CORE_MODULE)

        markdown_content = provider.perform_ocr(file_path=file_path, image_paths=image_paths)
        
        if not is_running(): raise InterruptedError(const.OCR_TASK_STOPPED)

        ocr_result = {"success": True, "message": "OCR 成功完成。", "markdown_content": markdown_content}
        worker_signals["file_finished"].emit(0, ocr_result)
        logger.info(f"===== {const.OCR_TASK_SUCCESS} =====")

    except InterruptedError:
        message = const.TASK_MANUALLY_STOPPED
        logger.warning(message)
        worker_signals["file_finished"].emit(0, {"success": False, "message": message})
        logger.info(f"===== {const.OCR_TASK_STOPPED_INFO} =====")
    except Exception as e:
        message = f"{const.OCR_UNKNOWN_ERROR_DETAIL}: {e}"
        logger.error(message, exc_info=True)
        worker_signals["file_finished"].emit(0, {"success": False, "message": str(e), "logger": logger})
        logger.info(f"===== {const.OCR_TASK_TERMINATED_WITH_ERROR} =====")
    finally:
        if profiler:
            profiler.disable()
            logger.info("性能分析已停止。")
            s = io.StringIO()
            sortby = pstats.SortKey.CUMULATIVE
            ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
            ps.print_stats(30) # 打印前30个最耗时的函数
            logger.info("\n===== 性能分析结果 =====\n")
            logger.info(s.getvalue())
            logger.info("\n=========================\n")

        if image_output_dir and os.path.exists(image_output_dir):
            try:
                shutil.rmtree(image_output_dir)
                logger.info(f"{const.TEMP_DIR_CLEANED}: {image_output_dir}")
            except Exception as e:
                logger.warning(f"{const.TEMP_DIR_CLEANUP_FAILED}: {e}")
        worker_signals["progress"].emit(100)
