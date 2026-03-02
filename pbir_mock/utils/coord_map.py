from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PixelRect:
    x: int
    y: int
    width: int
    height: int


def pbir_to_pixel_rect(
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    page_width: float,
    page_height: float,
    image_width: int,
    image_height: int,
) -> PixelRect:
    safe_page_width = page_width if page_width > 0 else 1.0
    safe_page_height = page_height if page_height > 0 else 1.0

    px_x = int(round((x / safe_page_width) * image_width))
    px_y = int(round((y / safe_page_height) * image_height))
    px_w = int(round((width / safe_page_width) * image_width))
    px_h = int(round((height / safe_page_height) * image_height))

    px_w = max(1, px_w)
    px_h = max(1, px_h)
    px_x = max(0, min(px_x, image_width - 1))
    px_y = max(0, min(px_y, image_height - 1))

    if px_x + px_w > image_width:
        px_w = max(1, image_width - px_x)
    if px_y + px_h > image_height:
        px_h = max(1, image_height - px_y)

    return PixelRect(x=px_x, y=px_y, width=px_w, height=px_h)

