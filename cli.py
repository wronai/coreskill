#!/usr/bin/env python3
"""
CoreSkill CLI - Command line interface for managing CoreSkill system
Usage: coreskill [command] [options]
"""
import argparse
import os
import sys
import shutil
import json
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cores.v1.config import ROOT, LOGS_DIR, STATE_FILE, load_state, save_state


def print_color(color, message):
    """Print colored message."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "dim": "\033[2m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{message}{colors['reset']}")


def cmd_logs_reset(args):
    """Reset/remove all log files."""
    print_color("cyan", "🗑️  Resetowanie logów...")
    
    removed = []
    errors = []
    
    # Main logs directory
    if LOGS_DIR.exists():
        for item in LOGS_DIR.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                    removed.append(f"logs/{item.name}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    removed.append(f"logs/{item.name}/")
            except Exception as e:
                errors.append(f"logs/{item.name}: {e}")
    
    # NFO logs
    nfo_logs = ROOT / "logs" / "nfo"
    if nfo_logs.exists():
        for item in nfo_logs.iterdir():
            try:
                if item.suffix in ['.db', '.jsonl', '.log']:
                    item.unlink()
                    removed.append(f"logs/nfo/{item.name}")
            except Exception as e:
                errors.append(f"logs/nfo/{item.name}: {e}")
    
    # Old log files in root
    for pattern in ['*.log', '*.log.*', 'evo_*.json']:
        for f in ROOT.glob(pattern):
            try:
                f.unlink()
                removed.append(f.name)
            except Exception as e:
                errors.append(f"{f.name}: {e}")
    
    if removed:
        print_color("green", f"✓ Usunięto {len(removed)} plików:")
        for r in removed[:10]:  # Show first 10
            print_color("dim", f"  - {r}")
        if len(removed) > 10:
            print_color("dim", f"  ... i {len(removed) - 10} więcej")
    
    if errors:
        print_color("yellow", f"⚠ Błędy przy usuwaniu ({len(errors)}):")
        for e in errors[:5]:
            print_color("dim", f"  - {e}")
    
    if not removed and not errors:
        print_color("dim", "Brak logów do usunięcia")
    
    return 0


def cmd_cache_reset(args):
    """Reset/remove cache files."""
    print_color("cyan", "🗑️  Resetowanie cache...")
    
    removed = []
    errors = []
    
    # Code2llm cache
    cache_dirs = [
        ROOT / ".code2llm_cache",
        ROOT / ".cache",
        ROOT / "__pycache__",
    ]
    
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            try:
                if cache_dir.is_file():
                    cache_dir.unlink()
                    removed.append(str(cache_dir.relative_to(ROOT)))
                else:
                    shutil.rmtree(cache_dir)
                    removed.append(f"{cache_dir.relative_to(ROOT)}/")
            except Exception as e:
                errors.append(f"{cache_dir.name}: {e}")
    
    # Python cache files
    for pattern in ['**/*.pyc', '**/*.pyo', '**/__pycache__']:
        for f in ROOT.glob(pattern):
            try:
                if f.is_file():
                    f.unlink()
                    removed.append(str(f.relative_to(ROOT)))
                elif f.is_dir():
                    shutil.rmtree(f)
                    removed.append(f"{f.relative_to(ROOT)}/")
            except Exception as e:
                pass  # Ignore errors for cache files
    
    # Model cache
    model_cache = ROOT / ".model_cache"
    if model_cache.exists():
        try:
            shutil.rmtree(model_cache)
            removed.append(".model_cache/")
        except Exception as e:
            errors.append(f".model_cache: {e}")
    
    # Clear .evo_state.json cache entries but preserve state
    if STATE_FILE.exists() and not args.full:
        try:
            state = load_state()
            # Remove cache-related entries
            cache_keys = ['model_cooldowns', '_cache', 'temp_data', 'last_errors']
            modified = False
            for key in cache_keys:
                if key in state:
                    del state[key]
                    modified = True
            
            if modified:
                save_state(state)
                removed.append(".evo_state.json (cache entries)")
        except Exception as e:
            errors.append(f"state cache: {e}")
    
    if removed:
        print_color("green", f"✓ Wyczyszczono {len(removed)} elementów:")
        for r in removed[:10]:
            print_color("dim", f"  - {r}")
    
    if errors:
        print_color("yellow", f"⚠ Błędy ({len(errors)})")
    
    if not removed and not errors:
        print_color("dim", "Cache był pusty")
    
    return 0


def cmd_state_reset(args):
    """Reset state file (dangerous - removes all state)."""
    if not args.force:
        print_color("yellow", "⚠ UWAGA: To usunie cały stan systemu (API keys, ustawienia, pamięć)")
        print_color("dim", "Użyj --force aby potwierdzić")
        return 1
    
    print_color("cyan", "🗑️  Resetowanie stanu systemu...")
    
    if STATE_FILE.exists():
        try:
            # Backup before deletion
            backup = STATE_FILE.with_suffix('.json.bak')
            shutil.copy2(STATE_FILE, backup)
            
            STATE_FILE.unlink()
            print_color("green", f"✓ Usunięto {STATE_FILE.name}")
            print_color("dim", f"  Kopia zapasowa: {backup.name}")
        except Exception as e:
            print_color("red", f"❌ Błąd: {e}")
            return 1
    else:
        print_color("dim", "Brak pliku stanu do usunięcia")
    
    return 0


def cmd_status(args):
    """Show system status."""
    print_color("cyan", "📊 Status CoreSkill")
    print()
    
    # Project info
    print_color("dim", f"ROOT: {ROOT}")
    print()
    
    # State file
    if STATE_FILE.exists():
        try:
            state = load_state()
            print_color("green", f"✓ Stan: {len(state)} kluczy")
            if 'model' in state:
                print_color("dim", f"  Model: {state['model']}")
            if 'api_key' in state:
                masked = state['api_key'][:8] + "..." if len(state['api_key']) > 12 else "***"
                print_color("dim", f"  API key: {masked}")
            if 'user_memory' in state:
                directives = len(state['user_memory'].get('directives', []))
                print_color("dim", f"  Pamięć: {directives} dyrektyw")
        except Exception as e:
            print_color("red", f"✗ Błąd odczytu stanu: {e}")
    else:
        print_color("yellow", "⚠ Brak pliku stanu")
    
    print()
    
    # Logs
    if LOGS_DIR.exists():
        log_count = sum(1 for _ in LOGS_DIR.rglob('*') if _.is_file())
        print_color("green" if log_count < 100 else "yellow", f"{'✓' if log_count < 100 else '⚠'} Logi: {log_count} plików")
    else:
        print_color("dim", "• Brak logów")
    
    # Cache
    cache_size = 0
    for cache_dir in [ROOT / ".code2llm_cache", ROOT / ".cache", ROOT / "__pycache__"]:
        if cache_dir.exists():
            try:
                cache_size += sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
            except:
                pass
    
    if cache_size > 0:
        size_mb = cache_size / (1024 * 1024)
        print_color("yellow" if size_mb > 100 else "dim", f"• Cache: {size_mb:.1f} MB")
    else:
        print_color("dim", "• Cache: pusty")
    
    return 0


def cmd_shell(args):
    """Start interactive shell (main.py)."""
    print_color("cyan", "🚀 Uruchamianie CoreSkill...")
    
    # Import and run main
    try:
        from main import main
        sys.argv = [sys.argv[0]]  # Reset args
        return main()
    except Exception as e:
        print_color("red", f"❌ Błąd uruchamiania: {e}")
        return 1


def main_cli():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='coreskill',
        description='CoreSkill - Ewolucyjny system AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  coreskill                    Uruchom interaktywną powłokę
  coreskill status             Pokaż status systemu
  coreskill logs reset         Usuń wszystkie logi
  coreskill cache reset        Wyczyść cache
  coreskill state reset --force  Zresetuj stan systemu
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Dostępne komendy')
    
    # logs command
    logs_parser = subparsers.add_parser('logs', help='Zarządzanie logami')
    logs_sub = logs_parser.add_subparsers(dest='logs_action')
    logs_reset = logs_sub.add_parser('reset', help='Usuń wszystkie logi')
    
    # cache command
    cache_parser = subparsers.add_parser('cache', help='Zarządzanie cache')
    cache_sub = cache_parser.add_subparsers(dest='cache_action')
    cache_reset = cache_sub.add_parser('reset', help='Wyczyść cache')
    cache_reset.add_argument('--full', action='store_true', help='Pełne czyszczenie (z cache w stanie)')
    
    # state command
    state_parser = subparsers.add_parser('state', help='Zarządzanie stanem')
    state_sub = state_parser.add_subparsers(dest='state_action')
    state_reset = state_sub.add_parser('reset', help='Zresetuj stan systemu')
    state_reset.add_argument('--force', action='store_true', required=True, help='Potwierdź usunięcie')
    
    # status command
    status_parser = subparsers.add_parser('status', help='Pokaż status systemu')
    
    # shell command (default)
    shell_parser = subparsers.add_parser('shell', help='Uruchom interaktywną powłokę')
    
    args = parser.parse_args()
    
    # Default to shell if no command
    if not args.command:
        return cmd_shell(args)
    
    # Route to appropriate handler
    if args.command == 'logs' and args.logs_action == 'reset':
        return cmd_logs_reset(args)
    elif args.command == 'cache' and args.cache_action == 'reset':
        return cmd_cache_reset(args)
    elif args.command == 'state' and args.state_action == 'reset':
        return cmd_state_reset(args)
    elif args.command == 'status':
        return cmd_status(args)
    elif args.command == 'shell':
        return cmd_shell(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main_cli())
