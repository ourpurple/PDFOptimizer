# -*- coding: utf-8 -*-
"""
应用中使用的所有常量。
"""

# Window Titles
MAIN_WINDOW_TITLE = "PDF Optimizer"
ABOUT_DIALOG_TITLE = "关于 PDF Optimizer"
OCR_CONFIG_DIALOG_TITLE = "OCR 配置"

# Status Messages
GS_STATUS_LABEL_OK = "✅ Ghostscript 已安装"
GS_STATUS_LABEL_FAIL = "❌ 未找到 Ghostscript (转曲和GS优化不可用)"
PANDOC_STATUS_LABEL_OK = "✅ Pandoc 已安装"
PANDOC_STATUS_LABEL_FAIL = "❌ 未找到 Pandoc (部分功能受限)"
DEFAULT_STATUS_TEXT = "请先选择文件..."

# Common Button Texts
SELECT_PDF_BUTTON_TEXT = "选择PDF文件"
SELECT_SINGLE_PDF_BUTTON_TEXT = "选择PDF文件 (仅限单个)"
CLEAR_LIST_BUTTON_TEXT = "清空列表"
START_BUTTON_TEXT = "开始处理"
STOP_BUTTON_TEXT = "停止"
ABOUT_BUTTON_TEXT = "关于"

# Optimize Tab
OPTIMIZE_TAB_NAME = "PDF优化"
OPTIMIZE_QUALITY_LOW = "低质量 (最大压缩)"
OPTIMIZE_QUALITY_MEDIUM = "中等质量 (推荐)"
OPTIMIZE_QUALITY_HIGH = "高质量 (轻度优化)"
OPTIMIZE_ENGINE_PIKEPDF = "Pikepdf 引擎"
OPTIMIZE_ENGINE_GS = "Ghostscript 引擎"
OPTIMIZE_HEADERS = ["文件名", "原始大小", "优化后大小", "压缩率", "状态"]
OPTIMIZE_BUTTON_TEXT = "开始优化"
OPTIMIZE_SUCCESS_MSG = "PDF优化完成！"

# Merge Tab
MERGE_TAB_NAME = "PDF合并"
MERGE_HEADERS = ["文件名", "状态"]
MERGE_BUTTON_TEXT = "开始合并"
MERGE_SUCCESS_MSG = "PDF合并完成！"

# Curves Tab
CURVES_TAB_NAME = "PDF转曲"
CURVES_HEADERS = ["文件名", "原始大小", "状态"]
CURVES_BUTTON_TEXT = "开始转曲"
CURVES_SUCCESS_MSG = "PDF转曲完成！"

# PDF to Image Tab
PDF_TO_IMAGE_TAB_NAME = "PDF转图片"
PDF_TO_IMAGE_HEADERS = ["文件名", "状态"]
PDF_TO_IMAGE_BUTTON_TEXT = "开始转换"
PDF_TO_IMAGE_FORMATS = ["JPG", "PNG"]
PDF_TO_IMAGE_DPIS = ["72", "96", "150", "300", "600"]
PDF_TO_IMAGE_SUCCESS_MSG = "PDF转图片完成！"

# Split Tab
SPLIT_TAB_NAME = "PDF分割"
SPLIT_HEADERS = ["文件名", "状态"]
SPLIT_BUTTON_TEXT = "开始分割"
SPLIT_SUCCESS_MSG = "PDF分割完成！"

# Bookmark Tab
BOOKMARK_TAB_NAME = "PDF加书签"
BOOKMARK_HEADERS = ["文件名", "书签数", "状态"]
BOOKMARK_BUTTON_TEXT = "开始添加"
BOOKMARK_ADD_NEW_BUTTON = "新增书签"
BOOKMARK_EDIT_BUTTON = "编辑书签"
BOOKMARK_IMPORT_BUTTON = "导入配置"
BOOKMARK_EXPORT_BUTTON = "导出配置"
BOOKMARK_USE_COMMON_CHECKBOX = "为所有文件添加同一组书签"
BOOKMARK_SUCCESS_MSG = "书签批量添加完成！"

# OCR Tab
OCR_TAB_NAME = "PDF OCR"
OCR_HEADERS = ["文件名", "状态"]
OCR_BUTTON_TEXT = "开始识别"
OCR_CONFIG_BUTTON_TEXT = "配置..."
OCR_RESULT_PLACEHOLDER = "OCR识别结果将显示在这里..."
OCR_SUCCESS_MSG = "OCR成功！结果已自动保存为 MD 和 DOCX。"
OCR_SUCCESS_MD_ONLY_MSG = "OCR成功！结果已自动保存为 MD。"
OCR_SAVE_FAIL_MSG = "OCR识别完成，但自动保存失败。"
OCR_FAIL_MSG = "OCR识别失败。"
ENABLE_PROFILING_CHECKBOX = "启用性能分析 (结果将保存到日志)"
# Bookmark Tab
IMPORTING_CONFIG = "正在导入配置..."
EXPORTING_CONFIG = "正在导出配置..."
IMPORT_SUCCESS_TITLE = "导入成功"
EXPORT_SUCCESS_TITLE = "导出成功"
NOT_APPLICABLE = "N/A"