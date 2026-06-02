"""CLI: PDF -> pages/page-NNN.png at 300dpi.

For normal single-page PDFs, each rendered page is kept as-is.
For book-spread scans (--spread), each rendered page is split left/right.
pdftoppm (poppler) is required at runtime; the split step is pure PIL.
"""
import subprocess
import sys
from pathlib import Path
from PIL import Image
from scripts import imaging


def render_pdf(pdf_path, raw_dir, dpi=300):
    """Render every PDF page to raw_dir/page-N.png via pdftoppm."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-png", str(pdf_path), str(raw_dir / "page")],
        check=True)
    return sorted(raw_dir.glob("page-*.png"))


def _renumber(out_dir, index, image):
    dest = out_dir / f"page-{index:03d}.png"
    image.save(dest)
    return str(dest)


def split_rendered(raw_dir, out_dir):
    """Split each rendered spread in raw_dir into two pages in out_dir."""
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written, index = [], 1
    for src in sorted(raw_dir.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[1])):
        left, right = imaging.split_spread(Image.open(src))
        written.append(_renumber(out_dir, index, left)); index += 1
        written.append(_renumber(out_dir, index, right)); index += 1
    return written


def copy_rendered(raw_dir, out_dir):
    """Renumber rendered single pages into out_dir as page-NNN.png."""
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for index, src in enumerate(
            sorted(raw_dir.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[1])), start=1):
        written.append(_renumber(out_dir, index, Image.open(src)))
    return written


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--spread"]
    spread = "--spread" in sys.argv
    if len(args) != 2:
        print("usage: python -m scripts.extract_pages [--spread] <file.pdf> <work-dir>")
        sys.exit(1)
    pdf, work = args
    raw = Path(work) / "_raw"
    pages = Path(work) / "pages"
    render_pdf(pdf, raw)
    written = split_rendered(raw, pages) if spread else copy_rendered(raw, pages)
    print(f"wrote {len(written)} pages to {pages}")
