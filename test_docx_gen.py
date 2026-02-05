
import sys

print("Starting verification script...")

try:
    print("Attempting to import markdown...")
    import markdown
    print(f"Markdown imported: {markdown.__version__}")
    
    print("Attempting to import docx...")
    import docx
    print("Docx imported")
    
    print("Attempting to import htmldocx...")
    from htmldocx import HtmlToDocx
    print("HtmlToDocx imported")
    
    from docx_generator import convert_markdown_to_docx
    print("docx_generator imported")

except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    print("Trying to install dependencies automatically...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown", "htmldocx", "python-docx"])
    print("Dependencies installed. Please re-run.")
    sys.exit(1)
except Exception as e:
    print(f"UNEXPECTED ERROR during imports: {e}")
    sys.exit(1)

# Create a dummy markdown text with a table
markdown_text = """
# Test Document

Here is a table:

| Name | Role | Score |
|---|---|---|
| Alice | Admin | 100 |
| Bob | User | 85 |

* List item 1
* List item 2
"""

try:
    print("Converting markdown...")
    docx_bytes = convert_markdown_to_docx(markdown_text)
    
    output_filename = "test_output.docx"
    with open(output_filename, "wb") as f:
        f.write(docx_bytes)
        
    print(f"Successfully created {output_filename}")
    
    import os
    size = os.path.getsize(output_filename)
    print(f"File size: {size} bytes")
    
except Exception as e:
    print(f"EXECUTION ERROR: {e}")
