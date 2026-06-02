from scripts import imaging


def test_split_spread_returns_left_then_right(sample_image):
    left, right = imaging.split_spread(sample_image)
    assert left.size == (600, 900)
    assert right.size == (600, 900)
    # Left half has the black pattern; right half is pure white.
    assert left.getpixel((0, 0)) == (0, 0, 0)
    assert right.getpixel((0, 0)) == (255, 255, 255)


def test_crops_produces_eight_named_regions(sample_image):
    crops = imaging.crops(sample_image)
    assert set(crops.keys()) == {
        "q1_top_left", "q2_top_right", "q3_bottom_left", "q4_bottom_right",
        "top", "bottom", "left", "right",
    }
    # Quarters are native-resolution exact halves of each dimension.
    assert crops["q1_top_left"].size == (600, 450)
    # Halves cover a full dimension.
    assert crops["left"].size[1] == 900


from pathlib import Path
from scripts import crop_page
from PIL import Image


def test_write_crops_creates_eight_files(tmp_path, sample_image):
    src = tmp_path / "page-001.png"
    sample_image.save(src)
    out = tmp_path / "crops"
    written = crop_page.write_crops(src, out)
    assert len(written) == 8
    for p in written:
        assert Path(p).exists()
    assert (out / "page-001_q1_top_left.png").exists()
