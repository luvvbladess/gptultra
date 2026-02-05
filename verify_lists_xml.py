
import zipfile
import re
import os

docx_path = "test_lists.docx"

if not os.path.exists(docx_path):
    print("Error: test_lists.docx not found. Run reproduce_list.py first.")
    exit(1)

print(f"Inspecting {docx_path}...")

with zipfile.ZipFile(docx_path, 'r') as z:
    # Check numbering.xml
    try:
        numbering_xml = z.read('word/numbering.xml').decode('utf-8')
        print("--- numbering.xml stats ---")
        num_count = len(re.findall(r'<w:num ', numbering_xml))
        print(f"Found {num_count} <w:num> definitions.")
    except KeyError:
        print("No numbering.xml found!")
        num_count = 0

    # Check document.xml
    document_xml = z.read('word/document.xml').decode('utf-8')
    print("\n--- document.xml stats ---")
    
    # Find all numIds used in paragraphs
    # Pattern: <w:numId w:val="X"/>
    num_ids = re.findall(r'<w:numId w:val="(\d+)"/>', document_xml)
    print(f"Found used numIds: {num_ids}")
    
    unique_ids = set(num_ids)
    print(f"Unique numIds used: {unique_ids}")
    
    if len(unique_ids) > 1:
        print("\nSUCCESS: Multiple numbering IDs detected. Lists are likely independent.")
    else:
        print("\nFAILURE: Only one numbering ID used. Lists likely continuous.")

