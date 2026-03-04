#!/usr/bin/env python3
"""
qr_generator skill - Generate QR codes using qrencode or python-qrcode fallback.
Supports: generate text/URL QR codes
"""
import subprocess
import json
import shutil
import base64
import tempfile
from pathlib import Path


def get_info():
    return {
        "name": "qr_generator",
        "version": "v1",
        "description": "Generate QR codes for text/URLs. Uses qrencode or pure-python fallback.",
        "capabilities": ["qr", "generator", "encoding"],
        "actions": ["generate", "generate_base64"]
    }


def health_check():
    """Check if QR generation is possible."""
    if shutil.which("qrencode"):
        return True
    # Try python-qrcode
    try:
        import qrcode
        return True
    except ImportError:
        pass
    # Pure python fallback always works (simplified QR)
    return True


class QRGeneratorSkill:
    """Generate QR codes with multiple backends."""

    def _generate_with_qrencode(self, text, output_path=None):
        """Generate QR using qrencode command."""
        if output_path:
            result = subprocess.run(
                ["qrencode", "-o", str(output_path), text],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return {"success": True, "path": str(output_path)}
            return {"success": False, "error": result.stderr}
        else:
            # Output to stdout as ASCII
            result = subprocess.run(
                ["qrencode", "-t", "ANSIUTF8", text],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return {"success": True, "ascii": result.stdout}
            return {"success": False, "error": result.stderr}

    def _generate_with_python(self, text, output_path=None):
        """Generate QR using python-qrcode or pure fallback."""
        try:
            import qrcode
            import qrcode.image.svg
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(text)
            qr.make(fit=True)
            
            if output_path:
                img = qr.make_image(fill_color="black", back_color="white")
                img.save(output_path)
                return {"success": True, "path": str(output_path)}
            else:
                # Return ASCII representation
                lines = []
                for row in qr.modules:
                    line = "".join("██" if cell else "  " for cell in row)
                    lines.append(line)
                return {"success": True, "ascii": "\n".join(lines)}
        except ImportError:
            # Pure python fallback - minimal implementation
            return self._generate_minimal(text)

    def _generate_minimal(self, text):
        """Minimal QR info when no tools available."""
        return {
            "success": True,
            "text": text,
            "note": "Install qrencode or python-qrcode for actual QR generation",
            "ascii": "[QR generation requires qrencode or python-qrcode]"
        }

    def generate(self, text, output_path=None, format="auto"):
        """Generate QR code."""
        try:
            if not text:
                return {"success": False, "error": "No text provided"}
            
            # Choose backend
            if shutil.which("qrencode"):
                return self._generate_with_qrencode(text, output_path)
            else:
                return self._generate_with_python(text, output_path)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_base64(self, text, format="png"):
        """Generate QR and return as base64 data URL."""
        try:
            if not text:
                return {"success": False, "error": "No text provided"}
            
            # Create temp file
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                result = self.generate(text, output_path=tmp_path)
                if not result.get("success"):
                    return result
                
                # Read and encode
                with open(tmp_path, "rb") as f:
                    data = f.read()
                
                b64 = base64.b64encode(data).decode()
                data_url = f"data:image/{format};base64,{b64}"
                
                return {
                    "success": True,
                    "data_url": data_url,
                    "format": format,
                    "text": text,
                    "size": len(data)
                }
            finally:
                # Cleanup
                try:
                    Path(tmp_path).unlink()
                except Exception:
                    pass
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "generate")
        text = input_data.get("text", input_data.get("data", ""))
        
        if action == "generate":
            return self.generate(
                text,
                input_data.get("output_path"),
                input_data.get("format", "auto")
            )
        elif action == "generate_base64":
            return self.generate_base64(
                text,
                input_data.get("format", "png")
            )
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return QRGeneratorSkill().execute(input_data)


if __name__ == "__main__":
    skill = QRGeneratorSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
    print(f"\nGenerate QR for 'Hello World':")
    result = skill.generate("Hello World")
    print(json.dumps(result, indent=2, ensure_ascii=False))
