#!/usr/bin/env python3
"""
Translate Femobiome II report from English to Turkish while preserving exact PDF layout.
Uses PyMuPDF (fitz) to manipulate PDF directly.
"""

import fitz  # PyMuPDF

# Translation dictionary based on the glossary and natural Turkish phrasing
TRANSLATIONS = {
    # Page title and headers
    "Female microbiota assessment": "Kadin mikrobiyota degerlendirmesi",

    # Patient info fields
    "Name:": "Ad Soyad:",
    "Age:": "Yas:",
    "Date of collection:": "Numune alim tarihi:",
    "Locus of biomaterial collection:": "Biyomateryal alim bolgesi:",
    "Container ID:": "Konteyner No:",
    "Doctor:": "Doktor:",

    # Conclusion section
    "Conclusion": "Sonuc",
    "Microbiota state – eubiosis": "Mikrobiyota durumu – obiyoz",
    "Microbiota state": "Mikrobiyota durumu",
    "eubiosis": "obiyoz",
    "predominance of normal microbiota": "normal mikrobiyota hakimiyeti",
    "predominance of normal": "normal mikrobiyota hakimiyeti",
    "microbiota,": "",
    "relative quantity of": "goreceli miktari",
    "Pathogens are not detected.": "Patojen saptanmadi.",
    "Pathogens are not detected": "Patojen saptanmadi",

    # Control parameters
    "Control biomaterial parameters": "Biyomateryal kontrol parametreleri",
    "Human genomic DNA": "Insan genomik DNA",
    "Total Bacterial Load": "Toplam bakteriyel yuk",
    "Reference": "Referans",

    # Legend - multiple variations to catch all occurrences
    "Normobiota": "Normobiyota",
    "Lower threshold of  normobiota 80%": "Normobiyota alt esigi %80",
    "Lower threshold of normobiota 80%": "Normobiyota alt esigi %80",
    "Lower threshold of normobiota": "Normobiyota alt esigi",
    "threshold of normobiota": "normobiyota esigi",
    "threshold of": "esigi",
    "Aerobes": "Aeroblar",
    "Anaerobes": "Anaeroblar",
    "Mycoplasmas": "Mikoplazmalar",

    # Microbiota state table
    "Microbiota state": "Mikrobiyota durumu",
    "NORMOBIOTA, total proportion": "NORMOBIYOTA, toplam oran",
    "AEROBES, total proportion": "AEROBLAR, toplam oran",
    "ANAEROBES, total proportion": "ANAEROBLAR, toplam oran",
    "MYCOPLASMAS, total proportion": "MIKOPLAZMALAR, toplam oran",

    # Footnotes
    "Proportion of species": "Tur orani",
    "in Lactobacillus spp., %": "Lactobacillus spp. icinde, %",
    "Proportion of species in Lactobacillus spp., %": "Lactobacillus spp. icindeki tur orani, %",
    "Yeast fungi": "Maya mantarlari",
    "Group B streptococcus": "Grup B streptokok",

    # Page 2 - Pathogens
    "PATHOGENS": "PATOJENLER",
    "SEXUALLY TRANSMITTED INFECTIONS (STI)": "CINSEL YOLLA BULASAN ENFEKSIYONLAR (CYBE)",
    "SEXUALLY TRANSMITTED INFECTIONS": "CINSEL YOLLA BULASAN ENFEKSIYONLAR",
    "STI": "CYBE",
    "HERPESVIRUSES": "HERPESVIRUSLER",
    "HUMAN PAPILLOMAVIRUSES (HPV)": "INSAN PAPILLOMAVIRUSLERI (HPV)",
    "HUMAN PAPILLOMAVIRUSES": "INSAN PAPILLOMAVIRUSLERI",
    "Result": "Sonuc",

    # Note section
    "NOTE:": "NOT:",
    "NOTE": "NOT",
    "Automated conclusion is only formed if the locus of biomaterial collection (V or C) is specified.":
        "Otomatik sonuc yalnizca biyomateryal alim bolgesi (V veya C) belirtildiginde olusturulur.",
    "Automated conclusion is only formed if the locus of biomaterial collection (V or C) is specified. Result interpretation":
        "Otomatik sonuc yalnizca biyomateryal alim bolgesi (V veya C) belirtildiginde olusturulur. Sonuc yorumu",
    "is carried out by the physician.": "hekim tarafindan yapilir.",
    "Result interpretation is carried out by the physician.": "Sonuc yorumu hekim tarafindan yapilir.",
    "Result interpretation": "Sonuc yorumu",

    # Signatures
    "Date of report": "Rapor tarihi",
    "Assay performed by": "Testi yapan",
    "Laboratory Manager": "Laboratuvar muduru",
    "Name": "Ad Soyad",
    "Signature": "Imza",

    # Reference note
    "Note": "Not",
    "Reference for Streptococcus agalactiae:": "Streptococcus agalactiae referansi:",
    "Reference for": "Referans:",
    "Gestational age over 37-38 weeks – negative result, all other cases":
        "Gebelik haftasi 37-38 uzerinde – negatif sonuc, diger tum durumlar",
    "Gestational age over 37-38 weeks": "Gebelik haftasi 37-38 uzerinde",
    "negative result": "negatif sonuc",
    "all other cases": "diger tum durumlar",

    # Infographics section
    "Types of Infographics in the test report": "Test raporundaki infografik turleri",
    "Types of Infographics": "Infografik turleri",
    "Color indicator – overall assessment of the microbiota state (eubiosis / moderate or severe dysbiosis);":
        "Renk gostergesi – mikrobiyota durumunun genel degerlendirmesi (obiyoz / orta veya siddetli disbiyoz);",
    "Color indicator": "Renk gostergesi",
    "overall assessment of the microbiota state": "mikrobiyota durumunun genel degerlendirmesi",
    "eubiosis / moderate or severe dysbiosis": "obiyoz / orta veya siddetli disbiyoz",
    "moderate or severe dysbiosis": "orta veya siddetli disbiyoz",
    "dysbiosis": "disbiyoz",

    "Linear histogram – display of the proportions of normobiota, aerobes, anaerobes, and mycoplasmas in the microbiota;":
        "Cizgisel histogram – mikrobiyotadaki normobiyota, aerob, anaerob ve mikoplazma oranlarinin gosterimi;",
    "Linear histogram": "Cizgisel histogram",
    "display of the proportions": "oranlarin gosterimi",

    "Column histogram – individual profile of microorganisms.":
        "Sutun histogram – mikroorganizmalarin bireysel profili.",
    "Column histogram": "Sutun histogram",
    "individual profile of microorganisms": "mikroorganizmalarin bireysel profili",

    # Terminology section
    "Terminology and Designations": "Terminoloji ve isaretlemeler",
    "Aerobes – facultative anaerobic opportunistic microorganisms.":
        "Aeroblar – fakultatif anaerobik firsatci mikroorganizmalar.",
    "facultative anaerobic opportunistic microorganisms": "fakultatif anaerobik firsatci mikroorganizmalar",
    "Anaerobes – obligate anaerobic opportunistic": "Anaeroblar – zorunlu anaerobik firsatci",
    "obligate anaerobic opportunistic microorganisms": "zorunlu anaerobik firsatci mikroorganizmalar",
    "microorganisms": "mikroorganizmalar",
    "Mycoplasmas – opportunistic genital mycoplasmas": "Mikoplazmalar – firsatci genital mikoplazmalar",
    "opportunistic genital mycoplasmas": "firsatci genital mikoplazmalar",

    "HPV 31-68 (11 types) – total detection of HPV 31/33/35/39/51/52/56/58/59/66/68 without differentiation.":
        "HPV 31-68 (11 tip) – HPV 31/33/35/39/51/52/56/58/59/66/68 toplam tespiti, ayrim yapilmadan.",
    "total detection": "toplam tespit",
    "without differentiation": "ayrim yapilmadan",

    "A dash (—) means a negative result; a listing separated by a \"/\" indicates pooled detection.":
        "Tire isareti (—) negatif sonucu belirtir; \"/\" ile ayrilan listeler toplu tespiti gosterir.",
    "A dash (—) means a negative result": "Tire isareti (—) negatif sonucu belirtir",
    "a listing separated by a \"/\" indicates pooled detection": "\"/\" ile ayrilan listeler toplu tespiti gosterir",
    "pooled detection": "toplu tespit",
}

def translate_text(text):
    """Translate text using the dictionary, trying longest matches first."""
    if not text or not text.strip():
        return text

    result = text
    # Sort by length (longest first) to match longer phrases before shorter ones
    sorted_translations = sorted(TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True)

    for eng, tur in sorted_translations:
        if eng in result:
            result = result.replace(eng, tur)

    return result

def translate_pdf(input_path, output_path):
    """
    Translate PDF by replacing text while preserving layout.
    """
    # Open the PDF
    doc = fitz.open(input_path)

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Get all text blocks with their positions
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        # Create a list of redaction areas and replacement texts
        edits = []

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    original_text = span["text"]
                    translated_text = translate_text(original_text)

                    if translated_text != original_text:
                        # Get the bounding box
                        bbox = fitz.Rect(span["bbox"])
                        font_size = span["size"]
                        font_name = span["font"]
                        color = span["color"]

                        edits.append({
                            "bbox": bbox,
                            "original": original_text,
                            "translated": translated_text,
                            "font_size": font_size,
                            "font_name": font_name,
                            "color": color,
                            "origin": span["origin"]
                        })

        # Apply edits: first add redaction annotations, then apply them
        for edit in edits:
            # Add redaction annotation (white rectangle to cover original text)
            page.add_redact_annot(edit["bbox"], fill=(1, 1, 1))

        # Apply all redactions
        page.apply_redactions()

        # Now insert translated text
        for edit in edits:
            # Convert color from integer to RGB tuple
            color_int = edit["color"]
            r = ((color_int >> 16) & 255) / 255.0
            g = ((color_int >> 8) & 255) / 255.0
            b = (color_int & 255) / 255.0

            # Insert text at the original position
            try:
                # Try to use a similar font
                fontname = "helv"  # Default to Helvetica
                if "bold" in edit["font_name"].lower():
                    fontname = "hebo"  # Helvetica Bold

                page.insert_text(
                    edit["origin"],
                    edit["translated"],
                    fontsize=edit["font_size"],
                    fontname=fontname,
                    color=(r, g, b)
                )
            except Exception as e:
                print(f"Warning: Could not insert text '{edit['translated']}': {e}")

    # Save the translated PDF
    doc.save(output_path)
    doc.close()
    print(f"Translated PDF saved to: {output_path}")

if __name__ == "__main__":
    input_pdf = "/Users/ilkerkadirozturk/Documents/genomer_brochures/reportsamples/Femobiome_II report_eubiosis_eng.pdf"
    output_pdf = "/Users/ilkerkadirozturk/Documents/genomer_brochures/reportsamples/Femobiome_II_report_eubiosis_TR.pdf"

    translate_pdf(input_pdf, output_pdf)
