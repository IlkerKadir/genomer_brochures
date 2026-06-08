import os
import sys
import fitz
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import engine


def _solid_pm(w, h, color):
    """w x h düz renkli RGB pixmap. color = (r,g,b) 0-255 int."""
    pm = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w, h), False)
    pm.set_rect(pm.irect, color)
    return pm


def test_sample_bg_white():
    pm = _solid_pm(100, 50, (255, 255, 255))
    bg = engine._sample_bg(pm, fitz.Rect(20, 20, 60, 30), 1.0)
    assert bg is not None
    assert all(abs(c - 1.0) < 0.02 for c in bg)


def test_sample_bg_gray():
    pm = _solid_pm(100, 50, (240, 240, 240))
    bg = engine._sample_bg(pm, fitz.Rect(20, 20, 60, 30), 1.0)
    assert bg is not None
    assert all(abs(c - 240 / 255) < 0.02 for c in bg)


def test_sample_bg_multicolor_returns_none():
    # sol yarı beyaz, sağ yarı mavi; rect tam sınırda -> marj çok-renkli
    pm = _solid_pm(100, 50, (255, 255, 255))
    pm.set_rect(fitz.IRect(50, 0, 100, 50), (0, 0, 255))
    bg = engine._sample_bg(pm, fitz.Rect(40, 20, 60, 30), 1.0)
    assert bg is None


def test_sample_bg_edge_does_not_crash():
    # rect sayfa kenarında: sol/üst marj sınır dışı -> kalan noktalardan örnekle, çökme
    pm = _solid_pm(100, 50, (255, 255, 255))
    bg = engine._sample_bg(pm, fitz.Rect(0, 0, 30, 20), 1.0)
    assert bg is None or all(abs(c - 1.0) < 0.02 for c in bg)
