import json
from pathlib import Path
import pytest
from PIL import Image


@pytest.fixture
def sample_image():
    # 1200x900 white image with a black left half, so split halves differ.
    img = Image.new("RGB", (1200, 900), "white")
    for x in range(600):
        for y in range(0, 900, 10):
            img.putpixel((x, y), (0, 0, 0))
    return img


@pytest.fixture
def sample_section():
    return [
        {"page": "001", "region": "q1_top_left", "type": "heading",
         "source": "CAPUT PRIMUM", "english": "Chapter One", "notes": []},
        {"page": "001", "region": "q3_bottom_left", "type": "body",
         "source": "In principio creavit Deus.", "english": "In the beginning God created.", "notes": []},
        {"page": "002", "type": "scripture",
         "source": "Fiat lux.", "english": "Let there be light.", "notes": []},
    ]


@pytest.fixture
def work_dir(tmp_path, sample_section):
    work = tmp_path / "work" / "sample-work"
    (work / "translation").mkdir(parents=True)
    (work / "translation" / "section-01.json").write_text(
        json.dumps(sample_section), encoding="utf-8")
    return work
