#!/usr/bin/env python3
"""
STT Auto-Test Pipeline — Chain of Responsibility pattern.

Replaces the monolithic _run_stt_autotest (CC=74) with a pipeline of small,
focused steps. Each step: DETECT → AUTO-FIX → RE-TEST → JOURNAL.

Usage:
    pipeline = STTAutoTestPipeline(sm, logger, llm)
    result = pipeline.run()
    # result.diagnostics dict same as old _run_stt_autotest return value
"""
import os
import sys
import shutil
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List

from .config import C, cpr


# ── Data structures ──────────────────────────────────────────────────

@dataclass
class TestContext:
    """Shared context flowing through the pipeline steps."""
    sm: object = None
    logger: object = None
    llm: object = None
    journal: object = None

    diagnostics: dict = field(default_factory=lambda: {
        "hw_diagnostics": {},
        "microphone": {"ok": False},
        "audio_level": {"ok": False},
        "transcription": {"ok": False},
        "fixes_applied": [],
        "llm_consulted": False,
    })
    abort: bool = False
    abort_reason: str = ""

    def add_fix(self, fix_desc: str):
        self.diagnostics["fixes_applied"].append(fix_desc)

    @property
    def fixes(self) -> list:
        return self.diagnostics["fixes_applied"]


@dataclass
class TestResult:
    """Final result of the STT autotest pipeline."""
    diagnostics: dict
    all_ok: bool
    fixes_applied: list

    @classmethod
    def from_context(cls, ctx: TestContext) -> "TestResult":
        d = ctx.diagnostics
        all_ok = all(d[k].get("ok") for k in ("microphone", "audio_level", "transcription"))
        return cls(diagnostics=d, all_ok=all_ok, fixes_applied=d["fixes_applied"])


# ── Audio utility functions ──────────────────────────────────────────

def record_test_wav(path: str, duration: int = 2) -> bool:
    """Record a test WAV file using arecord."""
    try:
        r = subprocess.run(
            ["arecord", "-q", "-d", str(duration), "-f", "S16_LE",
             "-r", "16000", "-c", "1", path],
            capture_output=True, timeout=duration + 8)
        return r.returncode == 0
    except Exception:
        return False


def measure_db(path: str) -> tuple:
    """Returns (has_sound: bool, db_level: float). Uses sox → ffmpeg → file size."""
    if shutil.which("sox"):
        try:
            sr = subprocess.run(
                ["sox", path, "-n", "stat"],
                capture_output=True, text=True, timeout=10)
            for line in sr.stderr.split('\n'):
                if 'RMS amplitude' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        amp = float(parts[1].strip())
                        if amp > 0:
                            db = 20 * (amp ** 0.5) - 60
                            return db > -40.0, db
        except Exception:
            pass
    if shutil.which("ffmpeg"):
        try:
            sr = subprocess.run(
                ["ffmpeg", "-i", path, "-af", "volumedetect",
                 "-f", "null", "-"],
                capture_output=True, text=True, timeout=10)
            for line in sr.stderr.split('\n'):
                if 'mean_volume' in line and 'dB' in line:
                    db = float(line.split(':')[1].split('dB')[0].strip())
                    return db > -40.0, db
        except Exception:
            pass
    try:
        sz = Path(path).stat().st_size
        return sz > 10000, -999.0 if sz <= 10000 else 0.0
    except Exception:
        return False, -999.0


def test_vosk(wav_path: str, model_path: Optional[Path] = None) -> tuple:
    """Test vosk transcription. Returns (ok: bool, error_msg: str)."""
    if not shutil.which("vosk-transcriber"):
        return False, "vosk-transcriber not found"
    fd2, out_path = tempfile.mkstemp(suffix=".txt", prefix="stt_autotest_out_")
    os.close(fd2)
    try:
        cmd = ["vosk-transcriber", "--input", wav_path,
               "--output", out_path, "--output-type", "txt"]
        if model_path:
            cmd.extend(["--model", str(model_path)])
        tr = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return tr.returncode == 0, (tr.stderr or "")[:300]
    except Exception as e:
        return False, str(e)
    finally:
        try:
            Path(out_path).unlink(missing_ok=True)
        except Exception:
            pass


def find_vosk_models() -> tuple:
    """Find all vosk model directories and stale zip files.
    Returns (models: list[Path], stale_zips: list[Path])."""
    cache_dirs = [
        Path.home() / ".cache" / "vosk",
        Path.home() / ".local" / "share" / "vosk",
    ]
    models = []
    stale_files = []
    for cache_dir in cache_dirs:
        if not cache_dir.exists():
            continue
        for item in cache_dir.iterdir():
            if item.is_dir() and "model" in item.name.lower():
                models.append(item)
            elif item.is_file() and item.suffix == ".zip":
                stale_files.append(item)
    return models, stale_files


def find_best_model(models: list, prefer_lang: str = "pl") -> Optional[Path]:
    """Find the best vosk model, preferring a specific language."""
    for m in models:
        if prefer_lang in m.name.lower():
            return m
    return models[0] if models else None


# ── Pipeline Step base class ─────────────────────────────────────────

class PipelineStep(ABC):
    """Base class for a pipeline step."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def execute(self, ctx: TestContext) -> TestContext:
        ...


# ── Step 0: Deep Hardware Diagnostics ────────────────────────────────

class HardwareDiagnosticsStep(PipelineStep):
    name = "hw_diagnostics"

    def execute(self, ctx: TestContext) -> TestContext:
        cpr(C.DIM, "  [0/4] Diagnostyka sprzętowa (audio channels, drivers, devices)...")
        try:
            from skills.hw_test.v1.skill import HWTestSkill
            hw = HWTestSkill()

            # Run targeted audio + driver + skill_hw tests
            hw_result = hw.execute({"action": "full"})
            ctx.diagnostics["hw_diagnostics"] = hw_result

            hw_tests = hw_result.get("tests", {})

            # Show key findings
            for test_name, test_data in hw_tests.items():
                tok = test_data.get("ok", False)
                if tok:
                    cpr(C.GREEN, f"    ✓ {test_name}")
                else:
                    cpr(C.YELLOW, f"    ✗ {test_name}")
                    for issue in test_data.get("issues", []):
                        cpr(C.YELLOW, f"        ⚠ {issue}")

            # If hw_test found default source is a monitor, fix it proactively
            skill_hw = hw_tests.get("skill_hw", {})
            stt_hw = skill_hw.get("skills_tested", {}).get("stt", {})
            stt_details = stt_hw.get("details", {})
            default_src = stt_details.get("default_source", {})
            if default_src.get("is_monitor"):
                cpr(C.YELLOW, "    ⚠ Domyślne źródło to monitor (nie mikrofon) — naprawiam...")
                try_pulseaudio_fix(ctx.diagnostics)
            elif default_src.get("muted"):
                cpr(C.YELLOW, "    ⚠ Domyślne źródło jest wyciszone — naprawiam...")
                try_pulseaudio_fix(ctx.diagnostics)

        except Exception as e:
            cpr(C.DIM, f"    [hw_test] niedostępny: {e}")

        return ctx


# ── Step 1: Check Microphone Hardware ────────────────────────────────

class CheckMicrophoneStep(PipelineStep):
    name = "microphone"

    def execute(self, ctx: TestContext) -> TestContext:
        cpr(C.DIM, "  [1/4] Sprawdzam mikrofon...")

        # Try to install arecord if missing
        if not shutil.which("arecord"):
            cpr(C.YELLOW, "  ✗ arecord brak — próbuję zainstalować alsa-utils...")
            self._try_install_alsa(ctx)

        if not shutil.which("arecord"):
            ctx.diagnostics["microphone"] = {"ok": False, "error": "arecord unavailable"}
            ctx.abort = True
            ctx.abort_reason = "no_microphone_tools"
            cpr(C.RED, "[REFLECT] Brak arecord — nie mogę testować mikrofonu")
            return ctx

        # Detect capture devices
        try:
            r = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=5)
            lines = r.stdout.strip().split('\n')
            devices = [l for l in lines if l.strip().startswith('card') and 'device' in l]
            if devices:
                cpr(C.GREEN, f"  ✓ Mikrofon: {len(devices)} urządzenie(a)")
                ctx.diagnostics["microphone"] = {
                    "ok": True, "devices": len(devices),
                    "device_list": [d.strip() for d in devices]}
            else:
                cpr(C.RED, "  ✗ Brak urządzeń capture — sprzętowy problem")
                ctx.diagnostics["microphone"] = {"ok": False, "error": "no capture devices"}
        except Exception as e:
            cpr(C.RED, f"  ✗ Mikrofon: {e}")
            ctx.diagnostics["microphone"] = {"ok": False, "error": str(e)}

        if not ctx.diagnostics["microphone"]["ok"]:
            cpr(C.RED, "[REFLECT] Brak mikrofonu — nie mogę naprawić sprzętowego problemu")
            ctx.abort = True
            ctx.abort_reason = "no_microphone"

        return ctx

    def _try_install_alsa(self, ctx: TestContext):
        try:
            subprocess.run(["sudo", "apt-get", "install", "-y", "alsa-utils"],
                           capture_output=True, timeout=30)
            if shutil.which("arecord"):
                cpr(C.GREEN, "  ✓ alsa-utils zainstalowane!")
                ctx.add_fix("installed alsa-utils")
                ctx.journal.record_attempt("stt", "arecord missing",
                    "apt_install", "sudo apt install alsa-utils", True)
            else:
                cpr(C.RED, "  ✗ Nie udało się zainstalować alsa-utils")
                ctx.journal.record_attempt("stt", "arecord missing",
                    "apt_install", "sudo apt install alsa-utils", False)
        except Exception:
            cpr(C.RED, "  ✗ Nie udało się zainstalować alsa-utils")


# ── Step 2: Check Audio Level ────────────────────────────────────────

class CheckAudioLevelStep(PipelineStep):
    name = "audio_level"

    def execute(self, ctx: TestContext) -> TestContext:
        cpr(C.DIM, "  [2/4] Testuję poziom audio...")

        fd, test_wav = tempfile.mkstemp(suffix=".wav", prefix="stt_autotest_")
        os.close(fd)

        try:
            if not record_test_wav(test_wav):
                cpr(C.RED, "  ✗ Nagrywanie testowe nie powiodło się")
                ctx.diagnostics["audio_level"] = {"ok": False, "error": "arecord failed"}
                return ctx

            has_sound, db_level = measure_db(test_wav)
            fsize = Path(test_wav).stat().st_size

            if has_sound:
                cpr(C.GREEN, f"  ✓ Audio level: {db_level:.1f}dB (OK)")
                ctx.diagnostics["audio_level"] = {"ok": True, "db": db_level}
            else:
                cpr(C.YELLOW, f"  ✗ Audio level: {db_level:.1f}dB (cisza, {fsize}b)")
                self._try_audio_fixes(ctx, db_level)
        finally:
            try:
                Path(test_wav).unlink(missing_ok=True)
            except Exception:
                pass

        return ctx

    def _try_audio_fixes(self, ctx: TestContext, db_level: float):
        journal = ctx.journal

        # Check journal for known fixes first
        known = journal.get_known_fix(f"audio silence {db_level}dB")
        if known and known.confidence >= 0.7:
            cpr(C.CYAN, f"  [JOURNAL] Znany fix (conf={known.confidence:.0%}): {known.fix_type}")

        cpr(C.CYAN, "  [AUTOFIX] Próbuję naprawić ustawienia audio...")
        amixer_fixes = [
            (["amixer", "set", "Capture", "unmute"], "Capture unmute"),
            (["amixer", "set", "Capture", "100%"], "Capture 100%"),
            (["amixer", "-c", "0", "set", "Capture", "unmute"], "Card0 Capture unmute"),
            (["amixer", "-c", "0", "set", "Capture", "100%"], "Card0 Capture 100%"),
            (["amixer", "set", "Mic", "unmute"], "Mic unmute"),
            (["amixer", "set", "Mic", "100%"], "Mic 100%"),
            (["amixer", "set", "Capture", "cap"], "Capture cap"),
            (["amixer", "-c", "0", "set", "Capture", "cap"], "Card0 Capture cap"),
            (["amixer", "-c", "1", "set", "Capture", "unmute"], "Card1 Capture unmute"),
            (["amixer", "-c", "1", "set", "Capture", "100%"], "Card1 Capture 100%"),
        ]

        # Skip fixes that journal says always fail
        failed_types = journal.get_failed_fixes("audio silence")

        fixes_tried = []
        for cmd, desc in amixer_fixes:
            if desc in failed_types:
                continue
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    fixes_tried.append(desc)
                    cpr(C.DIM, f"    ✓ {desc}")
            except Exception:
                pass

        if not fixes_tried:
            ctx.diagnostics["audio_level"] = {"ok": False, "db": db_level,
                                               "error": "no amixer fixes worked"}
            return

        ctx.diagnostics["fixes_applied"].extend(fixes_tried)
        cpr(C.CYAN, f"  [AUTOFIX] Zastosowano {len(fixes_tried)} poprawek. Weryfikuję...")

        # Re-test after amixer fixes
        time.sleep(0.5)
        self._verify_audio_fix(ctx, fixes_tried, db_level)

    def _verify_audio_fix(self, ctx: TestContext, fixes_tried: list, original_db: float):
        journal = ctx.journal
        fd2, test_wav2 = tempfile.mkstemp(suffix=".wav", prefix="stt_retest_")
        os.close(fd2)
        try:
            if not record_test_wav(test_wav2):
                ctx.diagnostics["audio_level"] = {"ok": False, "db": original_db,
                                                   "error": "retest recording failed"}
                return

            has_sound2, db_level2 = measure_db(test_wav2)
            if has_sound2:
                cpr(C.GREEN, f"  ✓ NAPRAWIONE! Audio: {db_level2:.1f}dB (było {original_db:.1f}dB)")
                ctx.diagnostics["audio_level"] = {"ok": True, "db": db_level2,
                                                   "fixed_from": original_db}
                for ft in fixes_tried:
                    journal.record_attempt("stt", f"audio silence {original_db}dB",
                        ft, f"amixer {ft}", True, f"Naprawione: {db_level2:.1f}dB")
            else:
                cpr(C.YELLOW, f"  ✗ Nadal cisza ({db_level2:.1f}dB) po amixer fix")
                ctx.diagnostics["audio_level"] = {"ok": False, "db": db_level2,
                                                   "attempted_fixes": fixes_tried}
                for ft in fixes_tried:
                    journal.record_attempt("stt", f"audio silence {original_db}dB",
                        ft, f"amixer {ft}", False, f"Nadal cisza: {db_level2:.1f}dB")
                # Try PulseAudio as fallback
                if shutil.which("pactl"):
                    cpr(C.DIM, "  [AUTOFIX] Próbuję PulseAudio...")
                    try_pulseaudio_fix(ctx.diagnostics)
        finally:
            try:
                Path(test_wav2).unlink(missing_ok=True)
            except Exception:
                pass


# ── Step 3: Check Vosk Transcription ─────────────────────────────────

class CheckTranscriptionStep(PipelineStep):
    name = "transcription"

    def execute(self, ctx: TestContext) -> TestContext:
        cpr(C.DIM, "  [3/4] Testuję transkrypcję vosk...")

        # Ensure vosk-transcriber is available
        if not shutil.which("vosk-transcriber"):
            self._try_install_vosk(ctx)

        if not shutil.which("vosk-transcriber"):
            ctx.diagnostics["transcription"] = {"ok": False, "error": "vosk-transcriber unavailable"}
            return ctx

        # Pre-detect model and clean stale zips
        models, stale_zips = find_vosk_models()
        self._clean_stale_zips(ctx, stale_zips)

        detected_model = find_best_model(models)
        if detected_model:
            cpr(C.DIM, f"    Model: {detected_model.name}")

        # Record and test
        fd3, test_wav3 = tempfile.mkstemp(suffix=".wav", prefix="stt_vosk_test_")
        os.close(fd3)
        try:
            if not record_test_wav(test_wav3, duration=2):
                ctx.diagnostics["transcription"] = {"ok": False, "error": "recording failed"}
                return ctx

            vosk_ok, vosk_err = test_vosk(test_wav3, model_path=detected_model)
            if vosk_ok:
                cpr(C.GREEN, "  ✓ vosk-transcriber: działa")
                ctx.diagnostics["transcription"] = {"ok": True}
                ctx.journal.record_success("stt", "vosk transcription OK")
            else:
                cpr(C.YELLOW, f"  ✗ vosk-transcriber błąd: {vosk_err[:100]}")
                self._deep_fix_vosk(ctx, test_wav3, vosk_err, stale_zips)
        finally:
            try:
                Path(test_wav3).unlink(missing_ok=True)
            except Exception:
                pass

        return ctx

    def _try_install_vosk(self, ctx: TestContext):
        cpr(C.YELLOW, "  ✗ vosk-transcriber brak — próbuję zainstalować...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "vosk"],
                           capture_output=True, timeout=60)
            if shutil.which("vosk-transcriber"):
                cpr(C.GREEN, "  ✓ vosk zainstalowany!")
                ctx.add_fix("pip install vosk")
                ctx.journal.record_attempt("stt", "vosk-transcriber missing",
                    "pip_install", "pip install vosk", True)
        except Exception:
            pass

    def _clean_stale_zips(self, ctx: TestContext, stale_zips: list):
        for zf in stale_zips:
            try:
                zf.unlink()
                cpr(C.DIM, f"    Usunięto stary zip: {zf.name}")
                ctx.add_fix(f"removed stale {zf.name}")
            except Exception:
                pass

    def _deep_fix_vosk(self, ctx: TestContext, test_wav: str, vosk_err: str,
                       stale_zips: list):
        """Deep vosk fix: stale zip removal → explicit model path → download model."""
        journal = ctx.journal
        models, new_stale = find_vosk_models()

        # Fix 1: Remove stale zip files confusing vosk
        if new_stale:
            for zf in new_stale:
                cpr(C.CYAN, f"  [AUTOFIX] Usuwam nierozpakowany zip: {zf.name}")
                try:
                    zf.unlink()
                    ctx.add_fix(f"removed stale {zf.name}")
                    journal.record_attempt("stt", vosk_err,
                        "remove_stale_zip", f"rm {zf}", True,
                        f"Usunięto plik myłący vosk: {zf.name}")
                except Exception as e:
                    cpr(C.YELLOW, f"  ✗ Nie mogę usunąć: {e}")

        # Fix 2: Find correct PL model and test with explicit path
        pl_model = find_best_model(models)

        if pl_model:
            cpr(C.CYAN, f"  [AUTOFIX] Test z jawną ścieżką modelu: {pl_model.name}")
            vosk_ok2, vosk_err2 = test_vosk(test_wav, model_path=pl_model)
            if vosk_ok2:
                cpr(C.GREEN, f"  ✓ NAPRAWIONE! vosk działa z --model {pl_model.name}")
                ctx.diagnostics["transcription"] = {"ok": True, "fixed": True,
                                                    "model_path": str(pl_model)}
                ctx.add_fix(f"explicit model path: {pl_model.name}")
                journal.record_attempt("stt", vosk_err,
                    "explicit_model_path", f"--model {pl_model}", True,
                    "vosk działa z jawną ścieżką modelu")
                return

            cpr(C.YELLOW, f"  ✗ Nadal nie działa z jawnym modelem: {vosk_err2[:80]}")
            journal.record_attempt("stt", vosk_err,
                "explicit_model_path", f"--model {pl_model}", False,
                vosk_err2[:100])

            # Fix 3: Re-test after stale zip removal (default path now clean)
            if stale_zips:
                cpr(C.DIM, "  [AUTOFIX] Ponowny test vosk (po czyszczeniu cache)...")
                vosk_ok3, vosk_err3 = test_vosk(test_wav)
                if vosk_ok3:
                    cpr(C.GREEN, "  ✓ NAPRAWIONE! vosk działa po czyszczeniu cache")
                    ctx.diagnostics["transcription"] = {"ok": True, "fixed": True}
                    ctx.add_fix("cleaned vosk cache")
                    journal.record_attempt("stt", vosk_err,
                        "clean_cache", "rm stale zips", True)
                    return
                ctx.diagnostics["transcription"] = {"ok": False, "error": vosk_err3[:200]}
            else:
                ctx.diagnostics["transcription"] = {"ok": False, "error": vosk_err2[:200]}
        else:
            # No model found at all — download
            self._download_vosk_model(ctx, test_wav)

    def _download_vosk_model(self, ctx: TestContext, test_wav: str):
        journal = ctx.journal
        cpr(C.CYAN, "  [AUTOFIX] Brak modelu vosk — pobieram PL...")
        try:
            cache_dir = Path.home() / ".cache" / "vosk"
            cache_dir.mkdir(parents=True, exist_ok=True)
            dl_cmd = (
                f"cd {cache_dir} && "
                "curl -L -o model.zip "
                "'https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip' && "
                "unzip -q -o model.zip && rm -f model.zip"
            )
            r = subprocess.run(dl_cmd, shell=True, capture_output=True, timeout=120)
            if r.returncode == 0:
                cpr(C.GREEN, "  ✓ Model PL pobrany!")
                ctx.add_fix("downloaded vosk-model-small-pl-0.22")
                journal.record_attempt("stt", "no vosk model",
                    "download_model", dl_cmd[:80], True)
                # Re-test
                vosk_ok4, _ = test_vosk(test_wav)
                ctx.diagnostics["transcription"] = {"ok": vosk_ok4, "fixed": vosk_ok4}
            else:
                cpr(C.YELLOW, f"  ✗ Pobieranie modelu: exit {r.returncode}")
                journal.record_attempt("stt", "no vosk model",
                    "download_model", dl_cmd[:80], False)
                ctx.diagnostics["transcription"] = {"ok": False,
                    "error": "model download failed"}
        except Exception as e:
            ctx.diagnostics["transcription"] = {"ok": False, "error": str(e)[:200]}


# ── Step 4: LLM Consultation ────────────────────────────────────────

class LLMConsultationStep(PipelineStep):
    name = "llm_consultation"

    def execute(self, ctx: TestContext) -> TestContext:
        still_broken = [k for k in ("microphone", "audio_level", "transcription")
                        if not ctx.diagnostics[k].get("ok")]

        if not still_broken:
            return ctx

        if not ctx.llm:
            cpr(C.DIM, "  [4/4] Brak LLM — pomijam konsultację")
            return ctx

        cpr(C.CYAN, f"  [4/4] Konsultuję LLM o {', '.join(still_broken)}...")
        ctx.diagnostics["llm_consulted"] = True

        for problem_area in still_broken:
            self._consult_for_area(ctx, problem_area)

        return ctx

    def _consult_for_area(self, ctx: TestContext, problem_area: str):
        journal = ctx.journal
        err_detail = ctx.diagnostics[problem_area].get("error", "unknown")
        attempted = ctx.fixes

        sys_ctx = (f"Linux system. Microphone: {ctx.diagnostics['microphone']}. "
                   f"Audio: {ctx.diagnostics['audio_level']}. "
                   f"Transcription: {ctx.diagnostics['transcription']}")

        llm_result = journal.ask_llm_and_try(
            skill_name="stt",
            error=f"{problem_area}: {err_detail}",
            system_context=sys_ctx,
            attempted_fixes=attempted,
        )

        if llm_result.get("success"):
            ctx.add_fix(f"llm_fix_{problem_area}")
            cpr(C.GREEN, f"  [LLM] ✓ {problem_area} naprawione przez LLM!")
            # Re-check transcription specifically
            if problem_area == "transcription":
                self._recheck_transcription(ctx)
        else:
            cpr(C.DIM, f"  [LLM] Nie udało się naprawić {problem_area}: "
                       f"{llm_result.get('diagnosis', '')[:80]}")

    def _recheck_transcription(self, ctx: TestContext):
        fd_re, wav_re = tempfile.mkstemp(suffix=".wav", prefix="stt_llm_retest_")
        os.close(fd_re)
        try:
            if record_test_wav(wav_re, 2):
                ok_re, _ = test_vosk(wav_re)
                ctx.diagnostics["transcription"] = {"ok": ok_re, "fixed": ok_re,
                                                    "fix_source": "llm"}
        finally:
            try:
                Path(wav_re).unlink(missing_ok=True)
            except Exception:
                pass


# ── Summary Step ─────────────────────────────────────────────────────

class SummaryStep(PipelineStep):
    name = "summary"

    def execute(self, ctx: TestContext) -> TestContext:
        d = ctx.diagnostics
        all_ok = all(d[k].get("ok") for k in ("microphone", "audio_level", "transcription"))
        fixes = ctx.fixes

        if all_ok:
            if fixes:
                cpr(C.GREEN, f"[REFLECT] STT autotest: NAPRAWIONO ({len(fixes)} fix(ów)) ✓")
            else:
                cpr(C.GREEN, "[REFLECT] STT autotest: WSZYSTKO OK — problem w otoczeniu (cisza w pokoju)")
        else:
            failed = [k for k, v in d.items()
                      if isinstance(v, dict) and not v.get("ok")]
            cpr(C.YELLOW, f"[REFLECT] STT autotest: nadal problemy — {', '.join(failed)}")
            if fixes:
                cpr(C.DIM, f"  Zastosowano {len(fixes)} fix(ów): {', '.join(fixes)}")

        # Show journal stats
        stats = ctx.journal.get_stats()
        if stats["total_attempts"] > 0:
            cpr(C.DIM, f"  [JOURNAL] Łączne próby: {stats['total_attempts']} "
                       f"(✓{stats['successes']}/✗{stats['fails']}), "
                       f"znane wzorce: {stats['known_fix_patterns']}")

        cpr(C.CYAN, "[REFLECT] === Koniec autotestu ===\n")
        ctx.logger.core("stt_autotest", d)
        return ctx


# ── PulseAudio fix (standalone helper) ───────────────────────────────

# Sources with these patterns are digital inputs (S/PDIF, HDMI) — NOT microphones
_DIGITAL_INPUT_PATTERNS = ("iec958", "spdif", "s/pdif", "hdmi", ".monitor")


def _score_source(src_name: str) -> int:
    """Score a PulseAudio source for microphone suitability.
    Higher = more likely to be a real microphone.
    Returns -1 for sources that should never be used as mic."""
    sl = src_name.lower()
    # Reject digital inputs and monitors
    if any(p in sl for p in _DIGITAL_INPUT_PATTERNS):
        return -1
    score = 0
    # Prefer USB devices (external mics/headsets)
    if "usb" in sl:
        score += 10
    # Prefer analog inputs (real audio)
    if "analog" in sl:
        score += 5
    # Prefer mono (typical for headset mics)
    if "mono" in sl:
        score += 3
    # Prefer named devices (headsets, known brands)
    if any(kw in sl for kw in ("headset", "headphone", "plantronics", "poly",
                                "jabra", "logitech", "blue", "yeti", "microphone")):
        score += 8
    # Prefer fallback profiles (PipeWire creates these for headset mics)
    if "fallback" in sl:
        score += 2
    # Penalize "input" with "stereo" for USB (often S/PDIF disguised)
    if "input" in sl and "stereo" in sl and "analog" not in sl:
        score -= 3
    return score


def _test_source_audio(src_name: str, duration: int = 1) -> float:
    """Quick test: set source as default, record, measure dB. Returns dB level."""
    import struct
    import wave
    try:
        subprocess.run(["pactl", "set-default-source", src_name],
                       capture_output=True, timeout=3)
        time.sleep(0.2)  # Let PulseAudio settle
        fd, wav = tempfile.mkstemp(suffix=".wav", prefix="mic_test_")
        os.close(fd)
        try:
            # Record with arecord
            if not shutil.which("arecord"):
                return -999.0
            r = subprocess.run(
                ["arecord", "-q", "-d", str(duration), "-f", "S16_LE",
                 "-r", "16000", "-c", "1", wav],
                capture_output=True, timeout=duration + 5)
            if r.returncode != 0 or not Path(wav).exists():
                return -999.0
            # Measure dB from WAV
            with wave.open(wav, "rb") as wf:
                n_frames = wf.getnframes()
                if n_frames == 0:
                    return -999.0
                raw = wf.readframes(n_frames)
            samples = struct.unpack(f"<{n_frames}h", raw)
            max_amp = max(abs(s) for s in samples) if samples else 0
            if max_amp > 0:
                import math
                return round(20 * math.log10(max_amp / 32768.0), 1)
            return -999.0
        finally:
            try:
                Path(wav).unlink(missing_ok=True)
            except Exception:
                pass
    except Exception:
        pass
    return -999.0


def _classify_sources(sources):
    """Classify PulseAudio sources into candidates and monitors."""
    candidates, monitors = [], []
    for parts in sources:
        if len(parts) >= 2:
            src_name = parts[1]
            score = _score_source(src_name)
            if score < 0:
                monitors.append(src_name)
            else:
                candidates.append((score, src_name))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates, monitors


def _unmute_and_find_best(candidates, diagnostics):
    """Unmute all candidates and find the one with best audio level."""
    for _, src_name in candidates:
        subprocess.run(["pactl", "set-source-mute", src_name, "0"],
                       capture_output=True, timeout=3)
        subprocess.run(["pactl", "set-source-volume", src_name, "100%"],
                       capture_output=True, timeout=3)
        cpr(C.DIM, f"    PulseAudio input: unmute + 100% → {src_name}")
        diagnostics.setdefault("fixes_applied", []).append(f"pactl unmute {src_name}")

    if len(candidates) <= 1:
        return candidates[0][1] if candidates else None

    cpr(C.DIM, f"    Testowanie {len(candidates)} źródeł audio...")
    best_input, best_db = None, -999.0
    for score, src_name in candidates:
        db = _test_source_audio(src_name, duration=1)
        cpr(C.DIM, f"      {src_name}: {db:.1f}dB (score={score})")
        if db > best_db:
            best_db = db
            best_input = src_name
    return best_input


def try_pulseaudio_fix(diagnostics: dict):
    """Last resort: try PulseAudio source adjustments.
    Prioritizes actual analog input sources over S/PDIF and monitors.
    Tests each candidate to find one that actually picks up sound."""
    if not shutil.which("pactl"):
        return
    try:
        r = subprocess.run(["pactl", "list", "sources", "short"],
                           capture_output=True, text=True, timeout=5)
        sources = [l.split('\t') for l in r.stdout.strip().split('\n') if l.strip()]

        candidates, monitors = _classify_sources(sources)
        best_input = _unmute_and_find_best(candidates, diagnostics)

        if best_input:
            subprocess.run(["pactl", "set-default-source", best_input],
                           capture_output=True, timeout=3)
            cpr(C.CYAN, f"    PulseAudio: domyślne źródło → {best_input}")
            diagnostics.setdefault("fixes_applied", []).append(f"pactl default-source {best_input}")

        for src_name in monitors:
            if ".monitor" not in src_name:
                subprocess.run(["pactl", "set-source-mute", src_name, "0"],
                               capture_output=True, timeout=3)
    except Exception:
        pass


# ── Main Pipeline ────────────────────────────────────────────────────

class STTAutoTestPipeline:
    """Chain of Responsibility pipeline for STT auto-testing.

    Each step runs in sequence, modifying a shared TestContext.
    If any step sets ctx.abort = True, the pipeline stops early.
    """

    steps = [
        HardwareDiagnosticsStep,
        CheckMicrophoneStep,
        CheckAudioLevelStep,
        CheckTranscriptionStep,
        LLMConsultationStep,
        SummaryStep,
    ]

    def __init__(self, sm, logger, llm=None):
        self.sm = sm
        self.logger = logger
        self.llm = llm

    def run(self) -> TestResult:
        from .repair_journal import RepairJournal

        journal = RepairJournal(llm_client=self.llm)

        ctx = TestContext(
            sm=self.sm,
            logger=self.logger,
            llm=self.llm,
            journal=journal,
        )

        cpr(C.CYAN, "\n[REFLECT] === Autotest STT (detect → fix → verify → learn) ===")

        for step_cls in self.steps:
            step = step_cls()
            ctx = step.execute(ctx)
            if ctx.abort:
                # Still run summary for logging
                SummaryStep().execute(ctx)
                break

        return TestResult.from_context(ctx)


# ── Backward-compatible wrapper ──────────────────────────────────────

def run_stt_autotest(sm, logger, llm=None) -> dict:
    """Drop-in replacement for the old _run_stt_autotest function.
    Returns the same diagnostics dict for backward compatibility."""
    pipeline = STTAutoTestPipeline(sm, logger, llm)
    result = pipeline.run()
    return result.diagnostics
