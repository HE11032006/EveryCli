#!/usr/bin/env python3
"""
Translate EveryCli command corpus into English (adding explanation_en, description_en, warning_en).
Handles arbitrary indentation (2, 4, 6 spaces), skips already translated items, and preserves formatting.

Usage:
    pip install deep-translator
    python tools/translate_corpus.py
"""

import re
import sys
from pathlib import Path

# Force UTF-8 on Windows terminals
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO_ROOT / "everycli" / "data" / "commands"

def get_translator():
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='fr', target='en')
        return translator.translate
    except ImportError:
        print("Pour traduire gratuitement, installe: pip install deep-translator")
        sys.exit(1)

def translate_yaml_file(file_path: Path, translate_fn):
    print(f"Traduction de {file_path.name}...")
    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines = []
    
    i = 0
    translated_count = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Match any field with any indentation: e.g. "  description: ..." or "      explanation: ..."
        match = re.match(r'^(\s*)(description|explanation|warning):\s*(.+)$', line)
        if match:
            indent = match.group(1)
            field = match.group(2)
            val_raw = match.group(3).strip()
            
            # Don't process multiline indicator | or > or empty values
            if val_raw and val_raw not in ("|", ">", "|-", ">-"):
                en_field = f"{field}_en"
                
                # Check if the next line already has en_field
                has_en_already = False
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith(f"{en_field}:"):
                        has_en_already = True
                
                if not has_en_already:
                    # Clean scalar quotes
                    text_to_translate = val_raw.strip('"').strip("'")
                    if text_to_translate:
                        try:
                            translated_text = translate_fn(text_to_translate)
                            # Escape internal quotes
                            safe_text = translated_text.replace('"', "'")
                            new_lines.append(f'{indent}{en_field}: "{safe_text}"')
                            translated_count += 1
                        except Exception as e:
                            print(f"  Warning [{file_path.name}:{i+1}]: {e}")
        i += 1

    file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"  [OK] {file_path.name} : {translated_count} nouveaux champs traduits.")

def main():
    if not COMMANDS_DIR.exists():
        print(f"Dossier introuvable : {COMMANDS_DIR}")
        sys.exit(1)
        
    translate_fn = get_translator()
    yaml_files = sorted(COMMANDS_DIR.glob("*.yaml"))
    
    print(f"=== Début de la traduction de {len(yaml_files)} fichiers de commandes ===")
    for yf in yaml_files:
        translate_yaml_file(yf, translate_fn)
    print("=== Traduction terminée avec succès ! ===")

if __name__ == "__main__":
    main()
