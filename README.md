# PDF Optimizer - A Powerful PDF Optimization Tool

[![Version](https://img.shields.io/badge/version-4.0.0-blue.svg)](https://github.com/one-lazy-cat/PDF-Optimizer/releases)

A powerful PDF utility that supports PDF compression, merging, splitting, image conversion, text-to-curves conversion, bookmark management, and intelligent OCR.

[中文说明](README_CN.md)

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

- 🧠 **PDF Intelligent Recognition (OCR)**
 - Convert PDF pages to images and call compatible OpenAI-format large language models (such as GPT-4o) for content recognition.
 - Convert recognition results into structured Markdown text.
 - Support custom API addresses, model names, and prompts.
 - Securely save API configurations without repeated input.
 - **Auto-generate DOCX**: Leverage [Pandoc](https://pandoc.org/) to automatically convert the recognized Markdown content (including LaTeX formulas) into high-quality `.docx` files.

- 🎨 **User-Friendly Interface**
  - Clean and intuitive user interface with tabbed navigation
  - Supports file drag-and-drop for all functions
  - Real-time display of processing progress
  - Detailed feedback on processing results

## Screenshot

![Screenshot](http://pic.mathe.cn/2025/07/17/79d439f3b098b.png)

## System Requirements

- Windows Operating System
- Python 3.10+
- Ghostscript (Optional, but recommended for full functionality)
- Pandoc (Required for exporting OCR results to .docx format)

## Installation

1. Clone or download this project
```bash
git clone https://github.com/one-lazy-cat/PDF-Optimizer.git
```

2. Install uv (Universal Virtualenv)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Create virtualenv and install dependencies
```bash
uv venv
uv pip install -r requirements.txt
```

4. (Optional) Install development dependencies
```bash
uv pip install -r requirements-dev.txt
```

5. Install Ghostscript (Optional)
- Download and install from the [Ghostscript official website](https://www.ghostscript.com/releases/gsdnld.html)
- Make sure Ghostscript is added to the system's PATH environment variable

6. Install Pandoc (Required for OCR to DOCX)
- Download and install from the [Pandoc official website](https://pandoc.org/installing.html)
- Make sure Pandoc is added to the system's PATH environment variable

## Usage

1. Run the program
```bash
uv run main.py
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

7. PDF Intelligent Recognition (OCR)
   - Switch to the "PDF OCR" tab.
   - For first-time use, enter your API Base URL and API Key, then click the "Fetch Model List" button to get the available models. Select the appropriate model and click "Save Configuration". This configuration will be securely saved locally, so you won't need to enter it again in the future.
   - Note: The "Fetch Model List" button will only become enabled after both the API Base URL and API Key are filled in.
   - Click the "Select PDF File" button and choose a PDF document you want to recognize.
   - Click the "Start Recognition" button. The program will convert the PDF pages to images and submit them to the AI model for processing.
   - After recognition is complete, the results will be displayed in Markdown format in the text box and automatically saved as a .md and .docx file with the same name.
   - **Note**: Exporting to .docx format requires **Pandoc** to be installed and accessible in the system's PATH. If Pandoc is not detected, the application will prompt you and only generate a .md file.

## Notes

- It is recommended to back up important files before processing.
- Processing large files may take a long time, please be patient.
- The Ghostscript engine may provide better compression results in some cases, but it may be slower than pikepdf.
- The text-to-curves feature depends on Ghostscript; it cannot be used if Ghostscript is not installed.

## Implementation Details

### Major Refactoring in v4.0.0

This version represents a significant internal refactoring focused on improving code quality, maintainability, and performance, laying a solid foundation for future feature iterations. Most changes are reflected in the code structure rather than direct user-facing features.

- **Architecture Refactoring**:
    - **UI Decoupling**: The previously monolithic `MainWindow` has been completely dismantled. The UI and logic for each function (optimization, merging, OCR, etc.) are now encapsulated in independent `QWidget` subclasses, dramatically reducing code coupling.
    - **Logic Abstraction**: Introduced a `BaseTabWidget` base class to abstract common UI components and logic such as file lists, control buttons, etc., simplifying the development of new functional tabs.
    - **Thread Unification**: Multiple task-specific `Worker` threads (like `OptimizeWorker`, `CurvesWorker`) have been refactored into a single, generic `ProcessingWorker`. This worker can accept any function as a processing task, greatly reducing redundant threading code.

- **Code Quality**:
    - Fully adopted `Flake8`, `Black`, `isort`, `mypy` and other static analysis and formatting tools, and standardized the entire codebase.
    - Externalized most hardcoded strings and configuration items into the `constants.py` module to enhance maintainability.

- **Dependency Management**:
    - `pyproject.toml` is now the single source of truth for project dependencies.
    - `requirements.txt` will be kept in sync with `pyproject.toml` to ensure environment consistency.

- **Resource Management**:
    - Conducted a thorough review of file I/O and external process calls (such as Ghostscript, Pandoc), using `with` statements and `try...finally` blocks to ensure file handles and process resources are correctly released upon completion or in case of exceptions.

- **UI Responsiveness**:
    - Fixed potential UI blocking issues when adding files or importing/exporting configurations, ensuring all time-consuming I/O operations are performed in background threads.

### Core Function Implementations

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
  - **Modular UI with Tab Widgets**: The UI is built around a `QMainWindow` that hosts a `QTabWidget`. Each major function (Optimize, Merge, OCR, etc.) is encapsulated in its own dedicated `QWidget` class (e.g., `OptimizeTab`, `MergeTab`), which are then loaded as tabs. This decouples the UI logic of each function from the main window.
  - **Shared UI Logic with `BaseTabWidget`**: A `BaseTabWidget` class is used as a parent for most tabs. It abstracts common UI elements and logic, such as the file list table (`SortableTableWidget`), progress bars, control buttons, and status labels, significantly reducing code duplication.
  - **Generic Asynchronous Worker**: All time-consuming backend operations are executed in a separate thread to prevent UI freezing. A single, generic `ProcessingWorker` class (inheriting from `QThread`) is used for all tasks. This worker is instantiated with a target function (e.g., `core.optimizer.run_optimization`) and its arguments, eliminating the need for numerous specific worker classes.
  - **Signal-Based UI Updates**: The `ProcessingWorker` communicates with the UI thread using PySide6's signal and slot mechanism. It emits signals for progress updates (`progress_updated`), individual file completion (`file_finished`), and overall task completion (`finished`), allowing the UI to update reactively and safely.
  - **Drag-and-Drop and Context Menus**: A custom `SortableTableWidget` is used for file lists, providing intuitive drag-and-drop reordering and a right-click context menu for actions like deleting files or opening their location.

- **PDF Intelligent Recognition (OCR)**
 - **PDF to Images**: Reuse the `core.pdf2img` module to convert PDF pages to 200 DPI PNG images and save them to a temporary directory.
 - **Calling AI Models**: Add a new `core.ocr` module containing the `process_images_with_model` function. This function is responsible for:
   - Encoding each image to Base64.
   - Building a JSON payload in the OpenAI Vision API format, sending the image and user-defined prompts to the specified API endpoint.
   - Using the `httpx` library to send POST requests and process the JSON data returned by the API.
 - **Markdown to DOCX Conversion**:
   - Utilizes the `core.utils.convert_markdown_to_docx_with_pandoc` function.
   - This function calls the `pandoc` command-line tool via `subprocess.Popen` to convert the Markdown content generated by the AI into a .docx file.
   - It reliably handles complex structures, especially LaTeX mathematical formulas.
 - **Configuration Management**:
   - Use the `python-dotenv` library to manage API configurations.
   - Securely load and save `OCR_API_BASE_URL`, `OCR_API_KEY`, and other information in the `.pdfoptimizer/.env` file in the user's home directory.
 - **UI Integration**:
   - Add a new "PDF OCR" tab in `ui.main_window`.
   - Before starting the task, `check_pandoc` is called to verify its installation and provides user guidance if it's missing.
   - The generic `ProcessingWorker` thread is used to execute PDF conversion and API calls in the background, preventing UI blocking.
   - Update the interface status and progress through the signal and slot mechanism (`Signal`, `Slot`).

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
- Pandoc

## Feedback and Suggestions

If you encounter any problems during use, or have any suggestions for features, please feel free to open an Issue or Pull Request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
