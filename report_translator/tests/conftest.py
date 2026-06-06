import os
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.normpath(os.path.join(HERE, "..", "..", "reportsamples", "en"))


@pytest.fixture
def femobiome_pdf():
    p = os.path.join(SAMPLES, "Femobiome_II report_eubiosis_eng.pdf")
    assert os.path.exists(p), f"örnek bulunamadı: {p}"
    return p


@pytest.fixture
def androbiome_pdf():
    p = os.path.join(SAMPLES, "Androbiome.pdf")
    assert os.path.exists(p), f"örnek bulunamadı: {p}"
    return p


@pytest.fixture
def enterobiome_pdf():
    p = os.path.join(SAMPLES, "Enterobiome Kids.pdf")
    assert os.path.exists(p), f"örnek bulunamadı: {p}"
    return p
