import sys
import logging
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("wiki-mcp")

WIKI_ROOT = Path("H:/AESC/kinematics-wiki")
FOLDERS = [".", "concepts", "methods", "examples", "exercises", "sources", "sources/pdf", "sources/src", "article", "article-src"]

mcp = FastMCP("KinematicsWiki")

@mcp.tool()
def read_record(name: str) -> str:
    """Прочитать конкретную запись"""
    if not WIKI_ROOT.exists():
        return f"❌ Ошибка: директория {WIKI_ROOT} не существует"
    for folder in FOLDERS:
        for ext in [".md", ".tex", ".sty"]:
            filepath = WIKI_ROOT / folder / f"{name}{ext}"
            if filepath.exists():
                try:
                    content = filepath.read_text(encoding="utf-8")
                    if not content.strip():
                        return f"⚠️ Файл '{name}' пуст"
                    return content
                except Exception as e:
                    return f"❌ Ошибка при чтении {name}: {e}"
        pdf_filepath = WIKI_ROOT / folder / f"{name}.pdf"
        if pdf_filepath.exists():
            try:
                from pdfminer.high_level import extract_text
                content = extract_text(str(pdf_filepath))
                if not content.strip():
                    return f"⚠️ PDF файл '{name}' пуст или не содержит текста"
                return content
            except ImportError:
                return f"❌ pdfminer.six не установлена"
            except Exception as e:
                return f"❌ Ошибка при чтении PDF {name}: {e}"
    return f"❌ Запись '{name}' не найдена"

@mcp.tool()
def write_record(name: str, folder: str, content: str) -> str:
    """Создать или обновить запись."""
    filepath = WIKI_ROOT / folder / f"{name}.md"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"💾 Записано: {filepath}")
    return f"✅ Запись сохранена: {filepath}"

@mcp.tool()
def delete_record(name: str, folder: str) -> str:
    """Удалить запись."""
    for ext in [".md", ".tex", ".sty"]:
        filepath = WIKI_ROOT / folder / f"{name}{ext}"
        if filepath.exists():
            try:
                filepath.unlink()
                logger.info(f"🗑 Удалено: {filepath}")
                return f"✅ Удалено: {folder}/{name}{ext}"
            except Exception as e:
                return f"❌ Ошибка при удалении {name}: {e}"
    return f"❌ Файл не найден: {folder}/{name}"

@mcp.tool()
def list_records() -> str:
    """Вернуть список всех записей в базе."""
    records = []
    for folder in FOLDERS:
        folder_path = WIKI_ROOT / folder
        if folder_path.exists():
            for f in folder_path.glob("*"):
                if f.suffix in [".md", ".tex", ".sty", ".pdf"]:
                    records.append(f"{folder}/{f.stem}")
    return "\n".join(records) if records else "📂 База пуста."

@mcp.tool()
def get_wiki_info() -> str:
    """Получить информацию о структуре базы."""
    if not WIKI_ROOT.exists():
        return f"❌ Директория {WIKI_ROOT} не существует"
    info = [f"📍 Путь к базе: {WIKI_ROOT}"]
    total_files = 0
    for folder in ["concepts", "methods", "examples", "exercises", "sources", "article", "article-src"]:
        folder_path = WIKI_ROOT / folder
        if folder_path.exists():
            files = list(folder_path.glob("*.md"))
            count = len(files)
            total_files += count
            info.append(f"  📂 {folder}: {count} записей")
        else:
            info.append(f"  ⚠️ {folder}: папка не найдена")
    info.append(f"\n📊 Всего записей: {total_files}")
    return "\n".join(info)

@mcp.tool()
def batch_rename(dry_run: bool = True) -> str:
    """Массово переименовать файлы: _ → пробел, : → -.
    dry_run=True — только показать, dry_run=False — применить."""
    if not WIKI_ROOT.exists():
        return f"❌ Директория {WIKI_ROOT} не существует"
    results = []
    errors = []
    for folder in FOLDERS:
        folder_path = WIKI_ROOT / folder
        if not folder_path.exists():
            continue
        for f in folder_path.glob("*"):
            if f.suffix not in [".md", ".tex", ".sty"]:
                continue
            old_stem = f.stem
            new_stem = old_stem.replace("_", " ").replace(":", "-")
            if new_stem == old_stem:
                continue
            results.append(f"  {folder}/{old_stem} → {new_stem}")
            if not dry_run:
                try:
                    f.rename(f.parent / f"{new_stem}{f.suffix}")
                except Exception as e:
                    errors.append(f"❌ {old_stem}: {e}")
    if not results:
        return "✅ Нет файлов для переименования."
    mode = "🔍 ПРЕДПРОСМОТР:" if dry_run else "✅ ПРИМЕНЕНО:"
    report = [mode] + results
    if errors:
        report += ["⚠️ Ошибки:"] + errors
    report.append(f"\nВсего: {len(results)} файлов")
    return "\n".join(report)

@mcp.tool()
def fix_links(dry_run: bool = True) -> str:
    """Исправить ссылки внутри всех .md файлов.
    dry_run=True — только показать, dry_run=False — применить."""
    if not WIKI_ROOT.exists():
        return f"❌ Директория {WIKI_ROOT} не существует"

    def fix_wikilink(match):
        inner = match.group(1)
        if "/" in inner:
            inner = inner.split("/")[-1]
        inner = re.sub(r'^Запись[-:]\s*', '', inner)
        inner = inner.replace("_", " ").replace(":", "-")
        return f"[[{inner}]]"

    results = []
    errors = []
    for folder in FOLDERS:
        folder_path = WIKI_ROOT / folder
        if not folder_path.exists():
            continue
        for f in folder_path.glob("*.md"):
            try:
                original = f.read_text(encoding="utf-8")
                fixed = re.sub(r'\[\[([^\]]+)\]\]', fix_wikilink, original)
                if fixed != original:
                    results.append(f"  {folder}/{f.stem}")
                    if not dry_run:
                        f.write_text(fixed, encoding="utf-8")
            except Exception as e:
                errors.append(f"❌ {f.stem}: {e}")

    if not results:
        return "✅ Нет файлов для исправления."
    mode = "🔍 ПРЕДПРОСМОТР:" if dry_run else "✅ ПРИМЕНЕНО:"
    report = [mode] + results
    if errors:
        report += ["⚠️ Ошибки:"] + errors
    report.append(f"\nВсего файлов: {len(results)}")
    return "\n".join(report)

if __name__ == "__main__":
    mcp.run(transport="stdio")
