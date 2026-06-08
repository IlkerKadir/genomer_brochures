#!/usr/bin/env python3
"""translate_report.py — qPCR rapor PDF'lerini EN->TR çeviren CLI (engine üstüne ince katman)."""
import os
import argparse
import fitz
import engine
import dictionary


def translate_pdf(in_path, out_path, kit=None):
    kits, common, passthrough, raw = dictionary.load()
    doc = fitz.open(in_path)
    kit = kit or dictionary.detect_kit(doc)
    table = kits[kit]
    templates = dictionary.compile_templates(raw, kit)
    segs = engine.extract_segments(doc)
    ann = engine.translate_segments(segs, table, passthrough, overrides={}, templates=templates)
    engine.render(doc, ann)
    doc.save(out_path, garbage=4, deflate=True)
    doc.close()

    review = sorted({a.en for a in ann if a.needs_review})
    with open(os.path.splitext(out_path)[0] + "_review.txt", "w", encoding="utf-8") as f:
        f.write("# Sözlüğe eklenecek / gözden geçirilecek birimler\n")
        f.write("# kit: %s | kaynak: %s\n\n" % (kit, os.path.basename(in_path)))
        for line in review:
            f.write(line + "\n")
    translated = sum(1 for a in ann if a.source in ("dict-exact", "dict-partial", "override"))
    print("✓ %-50s [%s] %d çevrildi, %d gözden geçir"
          % (os.path.basename(out_path), kit, translated, len(review)))


def main():
    ap = argparse.ArgumentParser(description="EN->TR qPCR rapor PDF çevirici")
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    ap.add_argument("--kit", choices=["femobiome_ii", "androbiome", "enterobiome_kids"])
    args = ap.parse_args()
    if os.path.isdir(args.input):
        for f in sorted(os.listdir(args.input)):
            if f.lower().endswith(".pdf"):
                p = os.path.join(args.input, f)
                translate_pdf(p, os.path.splitext(p)[0] + "_TR.pdf", args.kit)
    else:
        out = args.output or (os.path.splitext(args.input)[0] + "_TR.pdf")
        translate_pdf(args.input, out, args.kit)


if __name__ == "__main__":
    main()
