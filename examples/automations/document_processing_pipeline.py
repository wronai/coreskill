#!/usr/bin/env python3
"""
Pipeline 1: Automated Document Processing Workflow

Automatyzuje przepływ pracy dokumentów biurowych:
1. Wyszukuje wszystkie dokumenty w folderze
2. Konwertuje je do HTML z indeksem
3. Tworzy wersję backup
4. Generuje raport podsumowujący

Użycie:
  python3 examples/automations/document_processing_pipeline.py /home/user/documents
"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime


def run_skill(skill_name, action, params):
    """Execute a skill via the pipeline."""
    input_data = {"action": action, **params}
    cmd = [
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, 'skills/{skill_name}/v1')
from skill import execute, get_info
result = execute({json.dumps(input_data)})
print(json.dumps(result))
"""
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/home/tom/github/wronai/coreskill')
        return json.loads(result.stdout.strip().split('\n')[-1])
    except Exception as e:
        return {"success": False, "error": str(e)}


def document_processing_pipeline(source_dir):
    """Complete document processing workflow."""
    print(f"🔍 Starting document processing for: {source_dir}")
    print("=" * 60)

    # Step 1: Index all documents
    print("\n📁 Step 1: Creating document index...")
    index_result = run_skill("document_publisher", "create_index", {
        "source_dir": source_dir,
        "recursive": True
    })
    print(f"   Found {index_result.get('documents_count', 0)} documents")
    print(f"   Index saved to: {index_result.get('index_file', 'N/A')}")

    # Step 2: Search for specific document types
    print("\n🔍 Step 2: Searching for invoices and reports...")
    search_result = run_skill("document_search", "search_by_name", {
        "path": source_dir,
        "pattern": "*faktura*.*"
    })
    print(f"   Found {len(search_result.get('results', []))} matching documents")

    # Step 3: Generate HTML versions
    print("\n🌐 Step 3: Generating HTML versions...")
    docs = index_result.get('documents', [])
    html_generated = 0
    for doc in docs[:5]:  # Limit to first 5 for demo
        if doc.get('extension') in ['.md', '.txt']:
            result = run_skill("document_publisher", "generate_html", {
                "source_file": str(Path(source_dir) / doc['path']),
                "template": "default",
                "include_toc": True
            })
            if result.get('success'):
                html_generated += 1
    print(f"   Generated {html_generated} HTML documents")

    # Step 4: Create version snapshot
    print("\n💾 Step 4: Creating version snapshot...")
    version_result = run_skill("document_publisher", "version_document", {
        "file_path": index_result.get('index_file', ''),
        "comment": f"Automated processing {datetime.now().isoformat()}"
    })
    if version_result.get('success'):
        print(f"   Version ID: {version_result.get('version_id', 'N/A')}")

    # Final summary
    print("\n" + "=" * 60)
    print("✅ Document processing completed!")
    print(f"   Total documents: {index_result.get('documents_count', 0)}")
    print(f"   HTML generated: {html_generated}")
    print(f"   Version created: {version_result.get('version_id', 'N/A')}")

    return {
        "success": True,
        "documents_found": index_result.get('documents_count', 0),
        "html_generated": html_generated,
        "version_id": version_result.get('version_id')
    }


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "/home/user/documents"
    result = document_processing_pipeline(source)
    print(f"\nResult: {json.dumps(result, indent=2)}")
