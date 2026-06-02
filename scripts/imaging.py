"""Pure PIL helpers for splitting book-spread scans and cropping pages.

These operate on PIL.Image objects so they are unit-testable without any
external binaries. CLI wrappers (extract_pages, crop_page) call into these.
"""


def split_spread(image):
    """Split a two-page book-spread image into (left_page, right_page)."""
    w, h = image.size
    mid = w // 2
    left = image.crop((0, 0, mid, h))
    right = image.crop((mid, 0, w, h))
    return left, right


def crops(image):
    """Return 8 named crops: 4 native-resolution quarters + 4 halves.

    Quarters are best for dense body text/footnotes; halves give context
    that crosses quarter boundaries. Mirrors the baronius crop_page technique.
    """
    w, h = image.size
    mx, my = w // 2, h // 2
    return {
        "q1_top_left": image.crop((0, 0, mx, my)),
        "q2_top_right": image.crop((mx, 0, w, my)),
        "q3_bottom_left": image.crop((0, my, mx, h)),
        "q4_bottom_right": image.crop((mx, my, w, h)),
        "top": image.crop((0, 0, w, my)),
        "bottom": image.crop((0, my, w, h)),
        "left": image.crop((0, 0, mx, h)),
        "right": image.crop((mx, 0, w, h)),
    }
