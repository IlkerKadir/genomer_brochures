"""paths.py — paketlenmiş (PyInstaller) ve geliştirme ortamında dosya yollarını çözer.

İki tür yol:
- bundle_path: SALT-OKUNUR varlıklar (fonts, web, taban dictionary.json/glossary.tsv/postedit.tsv).
  Paketliyse PyInstaller'ın açtığı geçici dizinde (sys._MEIPASS), değilse kaynak dizinde.
- data_path: YAZILABİLİR kullanıcı verisi (config.json, ai_cache.json, glossary_state.json ve
  düzenlenebilir sözlük/glossary/postedit). Paketliyse %APPDATA%\\Genomer (Win) /
  ~/Library/Application Support/Genomer (mac) / ~/.config/Genomer (Linux); değilse kaynak dizin
  (geliştirme + testler kaynak dosyaları doğrudan kullanır, davranış değişmez).

Paketli modda yazılabilir dosyalar bundle'dan İLK AÇILIŞTA kopyalanabilir (seed=True): böylece
taban içerik gelir, kullanıcı düzenlemeleri %APPDATA%'da kalıcı olur (geçici _MEIPASS silinse de).
"""
import os
import sys
import shutil

_FROZEN = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
_SRC = os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = sys._MEIPASS if _FROZEN else _SRC


def _resolve_data_dir():
    if not _FROZEN:
        return _SRC                            # geliştirme: kaynak dizini (testler/düzenleme)
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    d = os.path.join(base, "Genomer")
    os.makedirs(d, exist_ok=True)
    return d


DATA_DIR = _resolve_data_dir()


def bundle_path(name):
    """Salt-okunur paket varlığının yolu."""
    return os.path.join(BUNDLE_DIR, name)


def data_path(name, seed=False):
    """Yazılabilir kullanıcı verisi yolu. seed=True ise (yalnız paketli modda) dosya yoksa
    bundle'daki taban kopyadan oluşturulur."""
    p = os.path.join(DATA_DIR, name)
    if seed and _FROZEN and not os.path.exists(p):
        src = os.path.join(BUNDLE_DIR, name)
        if os.path.exists(src):
            try:
                shutil.copy2(src, p)
            except OSError:
                pass
    return p
