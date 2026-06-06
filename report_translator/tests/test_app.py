import os
import subprocess
import sys
import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
RT = os.path.normpath(os.path.join(HERE, ".."))


def test_cli_translates_to_file(femobiome_pdf, tmp_path):
    out = tmp_path / "cikti_TR.pdf"
    r = subprocess.run([sys.executable, "translate_report.py", femobiome_pdf,
                        "-o", str(out)], cwd=RT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert out.exists()
    assert "Maya mantarları" in fitz.open(str(out))[0].get_text()
