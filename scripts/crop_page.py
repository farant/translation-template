"""CLI: crop a page PNG into quarters + halves for Claude-vision reading."""
import sys
from pathlib import Path
from PIL import Image
from scripts import imaging


def write_crops(src_png, out_dir):
    """Write the 8 crops of src_png into out_dir; return list of paths."""
    src_png = Path(src_png)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    image = Image.open(src_png)
    stem = src_png.stem
    written = []
    for name, crop in imaging.crops(image).items():
        dest = out_dir / f"{stem}_{name}.png"
        crop.save(dest)
        written.append(str(dest))
    return written


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python -m scripts.crop_page <page.png> <out-dir>")
        sys.exit(1)
    paths = write_crops(sys.argv[1], sys.argv[2])
    print(f"wrote {len(paths)} crops to {sys.argv[2]}")
