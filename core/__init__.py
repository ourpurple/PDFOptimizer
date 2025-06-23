from .optimizer import optimize_pdf, optimize_pdf_with_ghostscript
from .converter import convert_to_curves_with_ghostscript
from .merger import merge_pdfs, merge_pdfs_with_ghostscript
from .utils import is_ghostscript_installed
from .version import __version__

__all__ = [
    "optimize_pdf",
    "optimize_pdf_with_ghostscript",
    "convert_to_curves_with_ghostscript",
    "merge_pdfs",
    "merge_pdfs_with_ghostscript",
    "is_ghostscript_installed",
    "__version__",
]