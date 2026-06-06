import json
import shutil
import dictionary


def test_load_returns_kits_and_passthrough():
    kits, common, passthrough, raw = dictionary.load()
    assert "femobiome_ii" in kits and "androbiome" in kits
    assert kits["femobiome_ii"]["Yeast fungi"] == "Maya mantarları"
    assert passthrough  # derlenmiş regex listesi
    assert hasattr(passthrough[0], "fullmatch")


def test_detect_kit(femobiome_pdf, androbiome_pdf):
    import fitz
    assert dictionary.detect_kit(fitz.open(femobiome_pdf)) == "femobiome_ii"
    assert dictionary.detect_kit(fitz.open(androbiome_pdf)) == "androbiome"


def test_add_entry_short_label_and_backup(tmp_path):
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)
    res = dictionary.add_entry("femobiome_ii", "Brand New Label", "Yepyeni Etiket",
                               path=str(work))
    assert res["ok"] and not res.get("conflict")
    data = json.load(open(work, encoding="utf-8"))
    assert data["femobiome_ii"]["Brand New Label"] == "Yepyeni Etiket"
    assert (tmp_path / "dictionary.json.bak").exists()  # yedek alındı


def test_add_entry_long_goes_to_paragraphs(tmp_path):
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)
    long_en = "This is a long sentence with clearly more than six words total here."
    dictionary.add_entry("femobiome_ii", long_en, "Bu uzun bir cümledir.", path=str(work))
    data = json.load(open(work, encoding="utf-8"))
    assert long_en in data["femobiome_ii"]["_paragraphs"]


def test_add_entry_conflict_detected(tmp_path):
    src = dictionary.DICT_PATH
    work = tmp_path / "dictionary.json"
    shutil.copy(src, work)
    res = dictionary.add_entry("femobiome_ii", "Yeast fungi", "Farklı Çeviri",
                               path=str(work), overwrite=False)
    assert res["conflict"] and res["existing"] == "Maya mantarları"
    # overwrite=True ile üzerine yazılır
    res2 = dictionary.add_entry("femobiome_ii", "Yeast fungi", "Farklı Çeviri",
                                path=str(work), overwrite=True)
    assert res2["ok"]
    data = json.load(open(work, encoding="utf-8"))
    assert data["femobiome_ii"]["Yeast fungi"] == "Farklı Çeviri"
