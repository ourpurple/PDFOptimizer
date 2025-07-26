import pikepdf
import os
from typing import List, Dict, Union
from .utils import handle_exception, logger  # 导入 handle_exception 和 logger
import concurrent.futures  # 导入 concurrent.futures


@handle_exception
def add_bookmarks_to_pdf(
    input_path: str, output_path: str, bookmarks: List[Dict[str, Union[int, str]]]
) -> dict:
    """
    为单个PDF添加多条书签。
    :param input_path: 输入PDF路径
    :param output_path: 输出PDF路径
    :param bookmarks: 书签列表，每项为{"page": int, "title": str}，页码为1基
    :return: dict 结果
    """
    if not bookmarks:
        return {"success": False, "message": "没有有效的书签数据"}

    with pikepdf.open(input_path) as pdf:
        # 获取PDF总页数
        total_pages = len(pdf.pages)

        # 过滤无效的书签
        valid_bookmarks = []
        for bm in bookmarks:
            page = bm.get("page", 0)
            title = bm.get("title", "").strip()
            if not title:
                logger.warning(f"书签标题为空，已跳过。书签信息：{bm}")
                continue
            if page <= 0 or page > total_pages:
                logger.warning(
                    f"书签页码超出范围或无效，已跳过。页码: {page}, 总页数: {total_pages}，书签信息：{bm}"
                )
                continue
            valid_bookmarks.append({"page": page, "title": title})

        if not valid_bookmarks:
            return {"success": False, "message": "所有书签都无效"}

        # 创建新的大纲
        with pdf.open_outline() as outline:
            for bm in valid_bookmarks:
                page_num = bm["page"] - 1  # 转换为0基页码
                page = pdf.pages[page_num].obj

                # 创建目标位置（页面顶部）
                dest = [
                    page,
                    pikepdf.Name("/XYZ"),  # 使用XYZ模式，可以指定具体位置
                    0,  # left
                    page.MediaBox,  # top (页面高度)
                    1.0,  # zoom (100%)
                ]

                # 创建书签项并设置目标位置
                outline_item = pikepdf.OutlineItem(bm["title"], dest)
                outline.root.append(outline_item)

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 保存文件
        pdf.save(output_path)

        return {
            "success": True,
            "message": f"成功添加 {len(valid_bookmarks)} 个书签",
            "bookmarks_count": len(valid_bookmarks),
        }


@handle_exception
def batch_add_bookmarks_to_pdfs(
    file_bookmarks: Dict[str, List[Dict[str, Union[int, str]]]],
    output_dir: str,
    use_common: bool = False,
    common_bookmarks: List[Dict[str, Union[int, str]]] = None,
    worker_signals=None,
) -> None:
    """
    批量为多个PDF添加书签。
    :param file_bookmarks: {文件路径: 书签列表}
    :param output_dir: 输出文件夹
    :param use_common: 是否为所有文件使用同一组书签
    :param common_bookmarks: 公共书签列表
    :param worker_signals: 用于报告进度的信号
    """
    os.makedirs(output_dir, exist_ok=True)
    
    files = list(file_bookmarks.keys())
    total_files = len(files)

    for i, file_path in enumerate(files):
        if worker_signals and not worker_signals["is_running"]():
            break

        bookmarks = (
            common_bookmarks
            if use_common and common_bookmarks
            else file_bookmarks.get(file_path, [])
        )
        
        name, ext = os.path.splitext(os.path.basename(file_path))
        output_path = os.path.join(output_dir, f"{name}[已加书签]{ext}")

        result = add_bookmarks_to_pdf(file_path, output_path, bookmarks)
        result["file"] = file_path
        result["output"] = output_path
        
        if worker_signals:
            try:
                original_index = files.index(file_path)
                worker_signals["file_finished"].emit(original_index, result)
            except ValueError:
                pass
            worker_signals["progress"].emit(int((i + 1) / total_files * 100))
