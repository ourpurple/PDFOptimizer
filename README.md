
# PDF Optimizer - A Powerful PDF Optimization Tool

A powerful PDF utility that supports PDF compression, merging, splitting, image conversion, text-to-curves conversion, and bookmark management.

## Key Features

- 📦 **PDF File Compression and Optimization**
  - Supports three quality presets: Low Quality (Maximum Compression), Medium Quality (Recommended), High Quality (Light Optimization)
  - Supports both `pikepdf` and `Ghostscript` optimization engines

- 🔄 **PDF File Merging**
  - Supports merging multiple PDF files
  - Supports drag-and-drop sorting to determine the merge order
  - Supports both `pikepdf` and `Ghostscript` merging engines

- ✂️ **PDF Splitting**
  - Splits a multi-page PDF into individual pages
  - Uses `PyMuPDF` for fast and efficient splitting

- 🖼️ **PDF to Image Conversion**
  - Converts each page of a PDF into an image
  - Supports custom DPI and image formats (PNG, JPG)
  - Uses `PyMuPDF` for high-quality conversion

- ✏️ **PDF Text to Curves**
  - Uses Ghostscript to convert text into curves
  - Ensures font display consistency

- 📑 **PDF Bookmark Management**
  - Add bookmarks to PDF files
  - Support batch bookmark addition
  - Support using the same bookmark configuration for multiple files
  - Support importing and exporting bookmark configurations
  - Support bookmark editing and preview

- 🎨 **User-Friendly Interface**
  - Clean and intuitive user interface with tabbed navigation
  - Supports file drag-and-drop for all functions
  - Real-time display of processing progress
  - Detailed feedback on processing results
  
  ## Screenshot
  
  ![Screenshot](http://pic.mathe.cn/2025/06/21/054a212c338bd.jpg)
  
  ## System Requirements

- Windows Operating System
- Python 3.7+
- Ghostscript (Optional, but recommended for full functionality)

## Installation

1. Clone or download this project
```bash
git clone https://github.com/yourusername/PDFOptimizer.git
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Install Ghostscript (Optional)
- Download and install from the [Ghostscript official website](https://www.ghostscript.com/releases/gsdnld.html)
- Make sure Ghostscript is added to the system's PATH environment variable

## Usage

1. Run the program
```bash
python main.py
```

2. PDF File Optimization
   - Click "Select Files" or drag and drop PDF files into the program window
   - Select the desired quality preset
   - Select the optimization engine (pikepdf or Ghostscript)
   - Click "Start Optimization"

3. PDF File Merging
   - Add multiple PDF files
   - Adjust the file order by dragging and dropping
   - Click "Start Merging"

4. PDF Splitting
   - Switch to the "PDF Splitting" tab
   - Add the PDF file to be split
   - Click "Start Splitting" and select a folder to save the output files

5. PDF to Image Conversion
   - Switch to the "PDF to Image" tab
   - Add the PDF files to be converted
   - Select the desired image format and DPI
   - Click "Start Conversion" and select a folder to save the output images

6. PDF Text to Curves
   - Switch to the "PDF Text to Curves" tab
   - Add the PDF files to be processed
   - Click "Start Conversion to Curves"
   - Wait for the process to complete

## Notes

- It is recommended to back up important files before processing.
- Processing large files may take a long time, please be patient.
- The Ghostscript engine may provide better compression results in some cases, but it may be slower than pikepdf.
- The text-to-curves feature depends on Ghostscript; it cannot be used if Ghostscript is not installed.

## Implementation Details

- **PDF Optimization (pikepdf Engine)**
  - Uses `pikepdf.open(input_path)` to open the source file, and sets `compress_streams`, `object_stream_mode`, and `linearize` parameters based on three quality presets (Low/Medium/High).
  - Calls `pdf.save(output_path, ...)` to write the optimized PDF.

- **PDF Optimization (Ghostscript Engine)**
  - Uses `_get_gs_executable` to find the Ghostscript executable, with the following priority: `GHOSTSCRIPT_EXECUTABLE` environment variable > PyInstaller bundled path > `shutil.which` in system PATH.
  - Calls `subprocess.Popen` to execute the Ghostscript command line:
    ```bash
    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/screen|/ebook|/prepress -dNOPAUSE -dBATCH -dQUIET -sOutputFile=output.pdf input.pdf
    ```
  - Determines the optimization result based on the return code and calculates the file sizes before and after compression using `os.path.getsize`.

- **PDF Merging (pikepdf Engine)**
  - Uses `pikepdf.Pdf.new()` to create an empty PDF, iterates through the input file list, appends all pages to the target PDF using `pdf.pages.extend(src.pages)`, and finally saves with `pdf.save(output_path)`.

- **PDF Merging (Ghostscript Engine)**
  - Calls Ghostscript to execute the command line:
    ```bash
    gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile=merged.pdf file1.pdf file2.pdf ...
    ```
  - Determines the merge result based on the return code and file size.

- **PDF Text to Curves**
  - Based on the Ghostscript command line, adds the `-dNoOutputFonts` parameter to convert all text to curves, ensuring cross-platform font consistency:
    ```bash
    gs -sDEVICE=pdfwrite -o curves.pdf -dNOPAUSE -dBATCH -dQUIET -dNoOutputFonts input.pdf
    ```

- **PDF Splitting (PyMuPDF Engine)**
  - Uses `fitz.open()` to open the source PDF, iterates through each page, and creates a new single-page PDF for each page using `new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)`.

- **PDF to Image Conversion (PyMuPDF Engine)**
  - Uses `fitz.open()` to open the PDF, iterates through each page, and converts each page to a pixmap using `page.get_pixmap(dpi=dpi)`.
  - Saves the pixmap to the specified image format (PNG/JPG).

- **Graphical User Interface (PySide6)**
  - Uses `QMainWindow` and `QTabWidget` to build the main window and five functional tabs (Optimize, Merge, Split, To Image, To Curves).
  - Employs a custom `SortableTableWidget` that overrides drag-and-drop events (`dragEnterEvent`, `dragMoveEvent`, `dropEvent`) and the context menu (`contextMenuEvent`) to support drag-and-drop sorting, deletion, moving up/down, and opening the file location.
  - Implements multithreading with `QThread` (encapsulated in `BaseWorker` and its subclasses like `OptimizeWorker`, `MergeWorker`, etc.) and uses `Signal` to update the progress bar and table status in real-time without blocking the UI.
  - Resource paths are handled by `resource_path` to be compatible with both the development environment and the PyInstaller `_MEIPASS` directory.

- **Packaging as an Executable (PyInstaller)**
  - Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```
  - Run in the project root directory:
    ```bash
     venv\Scripts\pyinstaller --name PDFOptimizer --noconfirm --onefile --windowed --icon="ui/app.ico" --add-data "ui/style.qss;ui" --add-data "ui/app.ico;ui" main.py
    ```
  - To ensure Ghostscript is available after packaging, you can copy its `bin` and `lib` folders to the project root and add them via `--add-data` during packaging.
  - The packaged result is located at `dist/PDFOptimizer.exe`, which is a single-file executable containing all dependencies.

## Technology Stack

- Python 3
- PySide6 (Qt for Python)
- pikepdf
- PyMuPDF
- Ghostscript

## Feedback and Suggestions

If you encounter any problems during use, or have any suggestions for features, please feel free to open an Issue or Pull Request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
