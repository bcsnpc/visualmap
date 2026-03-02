from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

from pbir_mock.models import Page, Visual
from pbir_mock.utils import ensure_dir
from pbir_mock.utils.coord_map import PixelRect, pbir_to_pixel_rect


PALETTE = [
    (255, 235, 59),
    (0, 230, 118),
    (41, 182, 246),
    (255, 112, 67),
    (236, 64, 122),
    (255, 193, 7),
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_name in ("arialbd.ttf", "arial.ttf", "segoeuib.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _color_for_visual(*, bg_mode: str, page: Page, visual: Visual) -> tuple[int, int, int]:
    if bg_mode == "by_pageid":
        key = page.page_id
    elif bg_mode == "by_name":
        key = visual.visual_type
    else:
        key = f"{page.page_id}:{visual.seq}"
    digest = hashlib.md5(key.encode("utf-8")).digest()
    return PALETTE[digest[0] % len(PALETTE)]


def _label_anchor(rect: PixelRect, label_position: str, text_w: int, text_h: int) -> tuple[int, int]:
    if label_position == "top-right":
        x = rect.x + rect.width - text_w - 6
        y = rect.y + 6
    elif label_position == "center":
        x = rect.x + (rect.width - text_w) // 2
        y = rect.y + (rect.height - text_h) // 2
    else:
        x = rect.x + 6
        y = rect.y + 6
    return x, y


def _draw_pill(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill_rgb: tuple[int, int, int],
    text_rgb: tuple[int, int, int] = (0, 0, 0),
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pad_x = 10
    pad_y = 5
    left = x
    top = y
    right = x + text_w + pad_x * 2
    bottom = y + text_h + pad_y * 2

    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=8,
        fill=(*fill_rgb, 245),
        outline=(0, 0, 0, 255),
        width=3,
    )
    draw.text(
        (left + pad_x, top + pad_y),
        text,
        fill=(*text_rgb, 255),
        font=font,
        stroke_width=2,
        stroke_fill=(255, 255, 255, 255),
    )


def _draw_page_marker(
    draw: ImageDraw.ImageDraw,
    image_w: int,
    *,
    page: Page,
    page_index_1: int,
    pageid_position: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    text = f"P{page_index_1:03d} | {page.page_id} | {page.page_name}"
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pad = 8
    top = 10
    left = 10 if pageid_position == "top-left" else max(10, image_w - text_w - pad * 2 - 10)

    draw.rounded_rectangle(
        [left, top, left + text_w + pad * 2, top + text_h + pad * 2],
        radius=10,
        fill=(255, 64, 129, 235),
        outline=(0, 0, 0, 255),
        width=3,
    )
    draw.text((left + pad, top + pad), text, fill=(255, 255, 255, 255), font=font, stroke_width=1, stroke_fill=(0, 0, 0, 255))


def _render_pdf_pages(pdf_path: Path, dpi: int) -> list[Image.Image]:
    doc = fitz.open(pdf_path)
    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    images: list[Image.Image] = []
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        mode = "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images


def _write_page_map(out_csv: Path, pdf_page_count: int, pages: list[Page]) -> None:
    ensure_dir(out_csv.parent)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["pdf_page_index", "pageId", "pageName"])
        writer.writeheader()
        for i in range(max(pdf_page_count, len(pages))):
            page = pages[i] if i < len(pages) else None
            writer.writerow(
                {
                    "pdf_page_index": i + 1,
                    "pageId": page.page_id if page else "",
                    "pageName": page.page_name if page else "",
                }
            )


def annotate_pdf(
    *,
    pages: list[Page],
    pdf_path: Path,
    out_root: Path,
    dpi: int,
    bg_mode: str,
    draw_box: bool,
    label_position: str,
    pageid_position: str,
) -> dict[str, int]:
    annotated_root = out_root / "annotated"
    raw_root = annotated_root / "pages_raw"
    marked_root = annotated_root / "pages_annotated"
    ensure_dir(raw_root)
    ensure_dir(marked_root)

    rendered_pages = _render_pdf_pages(pdf_path, dpi)
    _write_page_map(annotated_root / "pdf_page_map.csv", len(rendered_pages), pages)

    warnings: list[str] = []
    if len(rendered_pages) != len(pages):
        warnings.append(
            f"PDF pages ({len(rendered_pages)}) do not match PBIR pages ({len(pages)}). "
            f"Annotated only min={min(len(rendered_pages), len(pages))} page pairs."
        )

    pageid_font = _load_font(28)
    num_font = _load_font(26)
    annotated_images: list[Image.Image] = []
    annotated_count = 0

    for idx, raw_img in enumerate(rendered_pages, start=1):
        raw_path = raw_root / f"page_{idx:03d}.png"
        raw_img.save(raw_path)

        page = pages[idx - 1] if idx - 1 < len(pages) else None
        if page is None:
            continue

        img = raw_img.convert("RGBA")
        draw = ImageDraw.Draw(img, "RGBA")
        _draw_page_marker(draw, img.width, page=page, page_index_1=idx, pageid_position=pageid_position, font=pageid_font)

        for visual in sorted(page.visuals, key=lambda v: v.seq):
            rect = pbir_to_pixel_rect(
                x=visual.x,
                y=visual.y,
                width=visual.width,
                height=visual.height,
                page_width=page.width,
                page_height=page.height,
                image_width=img.width,
                image_height=img.height,
            )
            fill_rgb = _color_for_visual(bg_mode=bg_mode, page=page, visual=visual)
            if draw_box:
                draw.rectangle(
                    [rect.x, rect.y, rect.x + rect.width, rect.y + rect.height],
                    outline=(0, 0, 0, 255),
                    width=4,
                    fill=(*fill_rgb, 40),
                )
                draw.rectangle(
                    [rect.x + 2, rect.y + 2, rect.x + rect.width - 2, rect.y + rect.height - 2],
                    outline=(*fill_rgb, 255),
                    width=2,
                )

            label_text = f"{visual.seq:03d}"
            bbox = draw.textbbox((0, 0), label_text, font=num_font, stroke_width=2)
            text_w = (bbox[2] - bbox[0]) + 20
            text_h = (bbox[3] - bbox[1]) + 12
            label_x, label_y = _label_anchor(rect, label_position, text_w, text_h)
            label_x = max(0, min(label_x, img.width - text_w - 2))
            label_y = max(0, min(label_y, img.height - text_h - 2))
            _draw_pill(draw, x=label_x, y=label_y, text=label_text, font=num_font, fill_rgb=fill_rgb)

            annotated_count += 1

        marked_path = marked_root / f"page_{idx:03d}.png"
        rgb = img.convert("RGB")
        rgb.save(marked_path)
        annotated_images.append(rgb)

    if annotated_images:
        first, rest = annotated_images[0], annotated_images[1:]
        first.save(annotated_root / "report_annotated.pdf", save_all=True, append_images=rest, resolution=dpi)
    else:
        warnings.append("No annotated pages were produced.")

    if warnings:
        (annotated_root / "warnings.txt").write_text("\n".join(warnings) + "\n", encoding="utf-8")

    return {
        "pdf_pages": len(rendered_pages),
        "pbir_pages": len(pages),
        "annotated_pages": min(len(rendered_pages), len(pages)),
        "annotated_visuals": annotated_count,
    }

