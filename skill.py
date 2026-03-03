#!/usr/bin/env python3
"""TTS Skill v1 - Text-to-Speech for evo-engine"""
import subprocess, sys, json, os, tempfile

def get_info():
    return {"name":"tts","version":"v1",
            "description":"Text-to-Speech: converts text to spoken audio",
            "capabilities":["speak","tts","voice","mowa","glos"]}

def health_check():
    return True

def _pip(pkg):
    try:
        __import__(pkg)
        return True
    except ImportError:
        try:
            subprocess.check_call([sys.executable,"-m","pip","install",pkg,"-q",
                                   "--break-system-packages"],
                                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

def _speak_pyttsx3(text, lang="pl"):
    if not _pip("pyttsx3"):
        return False, "unavailable"
    import pyttsx3
    e = pyttsx3.init()
    e.setProperty("rate", 160)
    for v in e.getProperty("voices"):
        if lang in v.id.lower():
            e.setProperty("voice", v.id)
            break
    e.say(text)
    e.runAndWait()
    return True, "pyttsx3"

def _speak_gtts(text, lang="pl"):
    if not _pip("gtts"):
        return False, "unavailable"
    from gtts import gTTS
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    try:
        gTTS(text=text, lang=lang).save(tmp)
        for p in ["mpv --no-video --really-quiet", "ffplay -nodisp -autoexit -loglevel quiet", "aplay"]:
            try:
                parts = p.split() + [tmp]
                subprocess.run(parts, timeout=30, capture_output=True)
                return True, "gtts+" + parts[0]
            except Exception:
                continue
        return False, "no player"
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass

def _speak_espeak(text, lang="pl"):
    try:
        subprocess.run(["espeak", "-v", lang, "-s", "150", text],
                       capture_output=True, timeout=15)
        return True, "espeak"
    except Exception:
        return False, "unavailable"

class TTSSkill:
    def execute(self, input_data):
        text = input_data.get("text", "")
        lang = input_data.get("lang", "pl")
        if not text:
            return {"spoken": False, "error": "No text", "method": None}
        for fn in [_speak_pyttsx3, _speak_espeak, _speak_gtts]:
            ok, name = fn(text, lang)
            if ok:
                return {"spoken": True, "method": name, "text": text}
        print(f"\n[TTS] {text}\n")
        return {"spoken": False, "method": "print_fallback", "text": text,
                "note": "Install: pip install pyttsx3 or gtts, or apt install espeak"}

def execute(input_data):
    return TTSSkill().execute(input_data)

if __name__ == "__main__":
    print(json.dumps(execute({"text": "Witaj!", "lang": "pl"}), indent=2, ensure_ascii=False))
