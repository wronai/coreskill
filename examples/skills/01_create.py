#!/usr/bin/env python3
"""
Skill creation example: Creating a custom skill programmatically
"""
import sys
sys.path.insert(0, '/home/tom/github/wronai/coreskill')

from pathlib import Path


SKILL_CODE = '''#!/usr/bin/env python3
"""
qr_generator - Generuje kody QR z tekstu
"""
import subprocess
import tempfile
from pathlib import Path


def get_info():
    return {
        "name": "qr_generator",
        "version": "v1",
        "description": "Generuje kody QR z podanego tekstu"
    }


def execute(params: dict) -> dict:
    """Generuje kod QR."""
    text = params.get("text")
    
    if not text:
        return {
            "success": False,
            "error": "Missing required parameter: text",
            "suggestion": "Provide text to encode"
        }
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            output_path = f.name
        
        result = subprocess.run(
            ['qrencode', '-s', '10', '-o', output_path, text],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"qrencode failed: {result.stderr}",
                "suggestion": "Install qrencode: sudo apt install qrencode"
            }
        
        return {
            "success": True,
            "result": {"path": output_path, "text": text},
            "message": f"QR code saved to: {output_path}"
        }
        
    except FileNotFoundError:
        return {
            "success": False,
            "error": "qrencode not found",
            "suggestion": "Install: sudo apt install qrencode"
        }


if __name__ == "__main__":
    result = execute({"text": "Hello World"})
    print(f"Result: {result}")
'''


def main():
    print("=== Skill Creation Example ===\n")
    
    # 1. Define skill
    skill_name = "qr_generator"
    skill_dir = Path(f"/home/tom/github/wronai/coreskill/skills/{skill_name}/v1")
    
    print(f"1. Creating skill: {skill_name}")
    print(f"   Path: {skill_dir}")
    
    # 2. Create directory
    skill_dir.mkdir(parents=True, exist_ok=True)
    print(f"   ✓ Directory created")
    
    # 3. Write skill.py
    skill_file = skill_dir / "skill.py"
    skill_file.write_text(SKILL_CODE)
    print(f"   ✓ skill.py written")
    
    # 4. Create meta.json
    meta_content = '''{
  "name": "qr_generator",
  "version": "v1",
  "description": "Generuje kody QR z podanego tekstu",
  "actions": ["generate"],
  "parameters": {
    "text": {"type": "string", "required": true}
  }
}'''
    meta_file = skill_dir / "meta.json"
    meta_file.write_text(meta_content)
    print(f"   ✓ meta.json written")
    
    # 5. Test import
    print(f"\n2. Testing skill import...")
    try:
        sys.path.insert(0, str(skill_dir.parent.parent))
        from skills.qr_generator.v1.skill import get_info, execute
        
        info = get_info()
        print(f"   ✓ Import successful")
        print(f"   Name: {info.get('name')}")
        print(f"   Description: {info.get('description')}")
    except Exception as e:
        print(f"   ✗ Import failed: {e}")
    
    # 6. Test execute (without qrencode)
    print(f"\n3. Testing skill execution...")
    try:
        result = execute({})  # Should fail - missing text
        print(f"   Test 1 (no params): {result.get('success')} (expected: False)")
        
        result = execute({"text": "test"})  # Should fail - qrencode not installed
        print(f"   Test 2 (with text): {result.get('success')} (expected: False - qrencode)")
    except Exception as e:
        print(f"   Test error: {e}")
    
    print(f"\n=== Done ===")
    print(f"\nTo use this skill:")
    print(f"  1. Install qrencode: sudo apt install qrencode")
    print(f"  2. In CoreSkill shell: /skills")
    print(f"  3. It should show: qr_generator")


if __name__ == "__main__":
    main()
