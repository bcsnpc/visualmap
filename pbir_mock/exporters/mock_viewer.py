from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image

from pbir_mock.models import Bookmark, Page
from pbir_mock.utils import ensure_dir


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PBIR Mock Viewer</title>
  <link rel="stylesheet" href="./styles.css" />
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <h1>PBIR Mock</h1>
      <input id="searchInput" type="search" placeholder="Search pages..." />
      <ul id="pageList"></ul>
    </aside>
    <main class="content">
      <div class="page-header">
        <h2 id="pageTitle"></h2>
        <p id="pageMeta"></p>
        <div class="view-controls">
          <label for="zoomSelect">Zoom</label>
          <select id="zoomSelect">
            <option value="fit" selected>Fit</option>
            <option value="0.5">50%</option>
            <option value="0.75">75%</option>
            <option value="1">100%</option>
          </select>
          <label class="debug-toggle"><input id="debugNavToggle" type="checkbox" /> Nav Debug</label>
        </div>
      </div>
      <div id="canvasScroll" class="canvas-scroll">
        <div id="pageCanvas" class="page-canvas"></div>
      </div>
    </main>
  </div>
  <script src="./app.js"></script>
</body>
</html>
"""


STYLES_CSS = """* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; font-family: "Segoe UI", Tahoma, sans-serif; color: #1f2937; }
body { background: linear-gradient(120deg, #f3f4f6, #e5e7eb); }
.app { display: grid; grid-template-columns: 300px 1fr; height: 100vh; }
.sidebar { padding: 16px; border-right: 1px solid #cbd5e1; background: #ffffffcc; overflow-y: auto; }
.sidebar h1 { margin: 0 0 12px 0; font-size: 20px; }
.sidebar input { width: 100%; padding: 10px; border: 1px solid #94a3b8; border-radius: 8px; margin-bottom: 12px; }
#pageList { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
#pageList button { width: 100%; text-align: left; border: 1px solid #cbd5e1; background: #fff; padding: 10px; border-radius: 8px; cursor: pointer; }
#pageList button.active { background: #dbeafe; border-color: #60a5fa; }
.content { display: grid; grid-template-rows: auto 1fr; min-width: 0; min-height: 0; }
.page-header { display: grid; grid-template-columns: 1fr auto; gap: 4px 16px; align-items: center; padding: 12px 16px; border-bottom: 1px solid #cbd5e1; background: #ffffffcc; }
.page-header h2 { margin: 0; font-size: 20px; }
.page-header p { margin: 0; font-size: 12px; color: #475569; grid-column: 1 / 2; }
.view-controls { display: flex; align-items: center; gap: 8px; }
.view-controls label { font-size: 12px; color: #475569; }
.view-controls select { padding: 6px 8px; border: 1px solid #94a3b8; border-radius: 6px; background: #fff; }
.debug-toggle { display: inline-flex; gap: 4px; align-items: center; user-select: none; }
.canvas-scroll { overflow: auto; padding: 10px; min-height: 0; }
.page-canvas {
  position: relative;
  background: #fff;
  border: 1px solid #94a3b8;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.1);
  background-size: 100% 100%;
  background-repeat: no-repeat;
}
.visual-box {
  position: absolute;
  border: 1px solid rgba(15, 23, 42, 0.2);
  background: rgba(14, 116, 144, 0.05);
  border-radius: 4px;
  pointer-events: none;
}
.visual-box.actionable {
  border: 1.5px solid rgba(22, 101, 52, 0.95);
  background: rgba(34, 197, 94, 0.12);
  pointer-events: auto;
  cursor: pointer;
}
.visual-badge {
  position: absolute;
  top: 3px;
  left: 3px;
  background: #ffea00;
  color: #000;
  border: 2px solid #000;
  border-radius: 999px;
  font-size: 15px;
  line-height: 1;
  font-weight: 800;
  letter-spacing: 0.4px;
  padding: 2px 8px;
  box-shadow: 0 0 0 2px #fff;
  z-index: 20;
  pointer-events: none;
}
.navigator-debug {
  position: absolute;
  border: 2px dashed rgba(220, 38, 38, 0.95);
  pointer-events: none;
  z-index: 30;
}
.navigator-grid-line {
  position: absolute;
  background: rgba(220, 38, 38, 0.7);
  pointer-events: none;
}
@media (max-width: 900px) {
  .app { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
  .sidebar { border-right: 0; border-bottom: 1px solid #cbd5e1; max-height: 35vh; }
}
"""


APP_JS_TEMPLATE = """const EMBEDDED_REPORT = __REPORT_JSON__;

const state = {
  report: EMBEDDED_REPORT,
  filteredPages: [],
  selectedPageId: null,
  history: [],
  activeBookmarkName: '',
  zoomMode: 'fit',
  debugNavigator: false
};

const IGNORED_TYPES = new Set(['textbox', 'basicshape', 'image']);

function norm(v) { return String(v || '').trim().toLowerCase(); }

function isNavigatorVisual(v) {
  return norm(v.type).includes('navigator');
}

function isActionable(v) {
  const t = norm(v.linkType);
  return t === 'pagenavigation' || t === 'bookmark' || t === 'weburl' || t === 'back' || isNavigatorVisual(v);
}

function getDrawableVisuals(page) {
  const ordered = page.visuals.slice().sort((a, b) => (a.z - b.z) || (a.y - b.y) || (a.x - b.x));
  let filtered = ordered.filter((v) => !v.isHidden && (!IGNORED_TYPES.has(norm(v.type)) || isActionable(v)));
  if (state.activeBookmarkName) {
    const bookmark = state.report.bookmarks[state.activeBookmarkName];
    const sectionIds = Array.isArray(bookmark?.sectionVisualIds) ? bookmark.sectionVisualIds : [];
    if (bookmark?.activeSection === page.pageId && sectionIds.length > 0) {
      const idSet = new Set(sectionIds);
      filtered = filtered.filter((v) => idSet.has(v.visualId) || isNavigatorVisual(v));
    }
  }
  return filtered.map((v, idx) => ({ ...v, drawSeq: idx + 1 }));
}

function navigateToPage(pageId) {
  if (!pageId) return;
  const exists = state.report.pages.some((p) => p.pageId === pageId);
  if (!exists || state.selectedPageId === pageId) return;
  state.history.push(state.selectedPageId);
  state.selectedPageId = pageId;
  renderPageList();
  renderSelectedPage();
}

function applyAction(visual) {
  const linkType = norm(visual.linkType);
  if (linkType === 'pagenavigation') {
    state.activeBookmarkName = '';
    navigateToPage(visual.navigationSection);
    return;
  }
  if (linkType === 'bookmark') {
    const bookmarkName = String(visual.bookmarkTarget || '');
    const bookmark = state.report.bookmarks[bookmarkName];
    if (bookmark?.activeSection) {
      state.activeBookmarkName = bookmarkName;
      navigateToPage(bookmark.activeSection);
    }
    return;
  }
  if (linkType === 'back') {
    state.activeBookmarkName = '';
    const prev = state.history.pop();
    if (prev) {
      state.selectedPageId = prev;
      renderPageList();
      renderSelectedPage();
    }
    return;
  }
  if (linkType === 'weburl') {
    state.activeBookmarkName = '';
    const url = String(visual.webUrl || '');
    if (url.startsWith('http://') || url.startsWith('https://')) window.open(url, '_blank', 'noopener');
  }
}

function safeBounds(page) {
  const iw = Math.max(1, Number(page.imageWidth || page.width || 1));
  const ih = Math.max(1, Number(page.imageHeight || page.height || 1));
  const b = page.contentBounds || {};
  const x = Math.max(0, Math.min(iw - 1, Number(b.x || 0)));
  const y = Math.max(0, Math.min(ih - 1, Number(b.y || 0)));
  const width = Math.max(1, Math.min(iw - x, Number(b.width || iw)));
  const height = Math.max(1, Math.min(ih - y, Number(b.height || ih)));
  return { x, y, width, height, iw, ih };
}

function currentScale(page) {
  if (state.zoomMode !== 'fit') return Number(state.zoomMode) || 1;
  const holder = document.getElementById('canvasScroll');
  const vw = Math.max(200, holder.clientWidth - 20);
  const vh = Math.max(160, holder.clientHeight - 20);
  const b = safeBounds(page);
  const sx = vw / Math.max(1, b.iw);
  const sy = vh / Math.max(1, b.ih);
  return Math.min(1, sx, sy);
}

function mapRectFromPbir(page, x, y, width, height, scale) {
  const pageW = Math.max(1, Number(page.width || 1));
  const pageH = Math.max(1, Number(page.height || 1));
  const b = safeBounds(page);
  const mx = b.x + (Math.max(0, Number(x || 0)) / pageW) * b.width;
  const my = b.y + (Math.max(0, Number(y || 0)) / pageH) * b.height;
  const mw = (Math.max(0, Number(width || 0)) / pageW) * b.width;
  const mh = (Math.max(0, Number(height || 0)) / pageH) * b.height;
  return { left: mx * scale, top: my * scale, width: mw * scale, height: mh * scale };
}

function clamp01(v) {
  if (Number.isNaN(v)) return 0;
  return Math.min(0.999999, Math.max(0, v));
}

function navigatorTargets(visual) {
  const explicit = Array.isArray(visual.navigatorTargetPageIds) ? visual.navigatorTargetPageIds : [];
  const byId = new Set(state.report.pages.map((p) => p.pageId));
  const clean = explicit.filter((id) => byId.has(id));
  if (clean.length > 0) return clean;
  return Array.isArray(state.report.pageOrderIds) ? state.report.pageOrderIds : state.report.pages.map((p) => p.pageId);
}

function drawNavigatorDebug(canvas, mapped, rows, cols) {
  if (!state.debugNavigator) return;
  const box = document.createElement('div');
  box.className = 'navigator-debug';
  box.style.left = `${mapped.left}px`;
  box.style.top = `${mapped.top}px`;
  box.style.width = `${Math.max(8, mapped.width)}px`;
  box.style.height = `${Math.max(8, mapped.height)}px`;
  canvas.appendChild(box);

  for (let c = 1; c < cols; c += 1) {
    const line = document.createElement('div');
    line.className = 'navigator-grid-line';
    line.style.left = `${mapped.left + (mapped.width * c / cols)}px`;
    line.style.top = `${mapped.top}px`;
    line.style.width = '1px';
    line.style.height = `${mapped.height}px`;
    canvas.appendChild(line);
  }
  for (let r = 1; r < rows; r += 1) {
    const line = document.createElement('div');
    line.className = 'navigator-grid-line';
    line.style.left = `${mapped.left}px`;
    line.style.top = `${mapped.top + (mapped.height * r / rows)}px`;
    line.style.width = `${mapped.width}px`;
    line.style.height = '1px';
    canvas.appendChild(line);
  }
}

function applyNavigatorClick(e, visual, mapped) {
  const rows = Math.max(1, Number(visual.navigatorRows || 1));
  const cols = Math.max(1, Number(visual.navigatorColumns || 1));
  const rx = clamp01((e.clientX - e.currentTarget.getBoundingClientRect().left) / Math.max(1, e.currentTarget.getBoundingClientRect().width));
  const ry = clamp01((e.clientY - e.currentTarget.getBoundingClientRect().top) / Math.max(1, e.currentTarget.getBoundingClientRect().height));
  const col = Math.floor(rx * cols);
  const row = Math.floor(ry * rows);
  const idx = (row * cols) + col;
  const targets = navigatorTargets(visual);
  if (state.debugNavigator) {
    console.log('navigator click', { pageId: visual.pageId, visualId: visual.visualId, rx, ry, row, col, idx, targetsCount: targets.length, mapped });
  }
  if (idx < 0 || idx >= targets.length) return;
  const targetPageId = targets[idx];
  state.activeBookmarkName = '';
  navigateToPage(targetPageId);
}

function renderPageList() {
  const pageList = document.getElementById('pageList');
  pageList.innerHTML = '';
  for (const page of state.filteredPages) {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.textContent = `${page.pageName} (${page.visuals.length})`;
    btn.className = page.pageId === state.selectedPageId ? 'active' : '';
    btn.onclick = () => {
      state.activeBookmarkName = '';
      state.selectedPageId = page.pageId;
      renderPageList();
      renderSelectedPage();
    };
    li.appendChild(btn);
    pageList.appendChild(li);
  }
}

function renderSelectedPage() {
  const page = state.report.pages.find((p) => p.pageId === state.selectedPageId);
  const pageTitle = document.getElementById('pageTitle');
  const pageMeta = document.getElementById('pageMeta');
  const canvas = document.getElementById('pageCanvas');
  if (!page) {
    pageTitle.textContent = 'No page selected';
    pageMeta.textContent = '';
    canvas.innerHTML = '';
    canvas.style.width = '0px';
    canvas.style.height = '0px';
    return;
  }
  const drawable = getDrawableVisuals(page);
  const scale = currentScale(page);
  const b = safeBounds(page);
  pageTitle.textContent = page.pageName;
  pageMeta.textContent = `${Math.round(page.width)}x${Math.round(page.height)} | scale ${Math.round(scale * 100)}% | overlays ${drawable.length}${state.activeBookmarkName ? ` | bookmark: ${state.activeBookmarkName}` : ''}`;
  canvas.style.width = `${b.iw * scale}px`;
  canvas.style.height = `${b.ih * scale}px`;
  canvas.style.backgroundImage = page.backgroundImage ? `url('${page.backgroundImage}')` : 'none';
  canvas.innerHTML = '';

  for (const v of drawable) {
    const mapped = mapRectFromPbir(page, v.x, v.y, Math.max(24, v.width), Math.max(20, v.height), scale);
    const box = document.createElement('div');
    box.className = 'visual-box';
    if (isActionable(v)) box.classList.add('actionable');
    box.style.left = `${mapped.left}px`;
    box.style.top = `${mapped.top}px`;
    box.style.width = `${Math.max(8, mapped.width)}px`;
    box.style.height = `${Math.max(8, mapped.height)}px`;
    box.style.zIndex = String(Math.round(v.z) + 2);

    if (isNavigatorVisual(v)) {
      box.addEventListener('click', (e) => applyNavigatorClick(e, { ...v, pageId: page.pageId }, mapped));
      drawNavigatorDebug(canvas, mapped, Math.max(1, Number(v.navigatorRows || 1)), Math.max(1, Number(v.navigatorColumns || 1)));
    } else if (norm(v.linkType)) {
      box.addEventListener('click', () => applyAction(v));
    }

    const badge = document.createElement('div');
    badge.className = 'visual-badge';
    badge.textContent = String(v.drawSeq).padStart(3, '0');
    box.appendChild(badge);
    canvas.appendChild(box);
  }
}

function wireSearch() {
  const input = document.getElementById('searchInput');
  input.addEventListener('input', (e) => {
    const term = String(e.target.value || '').toLowerCase().trim();
    state.filteredPages = state.report.pages.filter((p) => p.pageName.toLowerCase().includes(term));
    if (!state.filteredPages.some((p) => p.pageId === state.selectedPageId)) {
      state.selectedPageId = state.filteredPages[0]?.pageId || null;
    }
    renderPageList();
    renderSelectedPage();
  });
}

function wireZoom() {
  const select = document.getElementById('zoomSelect');
  select.value = state.zoomMode;
  select.addEventListener('change', (e) => {
    state.zoomMode = String(e.target.value || 'fit');
    renderSelectedPage();
  });
  window.addEventListener('resize', () => renderSelectedPage());
}

function wireDebugToggle() {
  const chk = document.getElementById('debugNavToggle');
  chk.checked = state.debugNavigator;
  chk.addEventListener('change', (e) => {
    state.debugNavigator = Boolean(e.target.checked);
    renderSelectedPage();
  });
}

async function init() {
  state.filteredPages = state.report.pages.slice();
  state.selectedPageId = state.filteredPages[0]?.pageId || null;
  wireSearch();
  wireZoom();
  wireDebugToggle();
  renderPageList();
  renderSelectedPage();
}

init().catch((err) => {
  console.error(err);
  const canvas = document.getElementById('pageCanvas');
  canvas.textContent = 'Failed to initialize viewer data';
});
"""


def _detect_content_bounds(image: Image.Image) -> dict[str, int]:
    rgb = image.convert("RGB")
    img_w, img_h = rgb.size
    pix = rgb.load()
    threshold = 245
    min_x = img_w
    min_y = img_h
    max_x = -1
    max_y = -1
    step = 2
    for y in range(0, img_h, step):
        for x in range(0, img_w, step):
            r, g, b = pix[x, y]
            if r < threshold or g < threshold or b < threshold:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y
    if max_x < min_x or max_y < min_y:
        return {"x": 0, "y": 0, "width": img_w, "height": img_h}
    pad = 3
    min_x = max(0, min_x - pad)
    min_y = max(0, min_y - pad)
    max_x = min(img_w - 1, max_x + pad)
    max_y = min(img_h - 1, max_y + pad)
    return {
        "x": min_x,
        "y": min_y,
        "width": max(1, max_x - min_x + 1),
        "height": max(1, max_y - min_y + 1),
    }


def _apply_global_median_bounds(pages_payload: list[dict[str, Any]]) -> None:
    margins: list[tuple[float, float, float, float]] = []
    for p in pages_payload:
        b = p.get("contentBounds", {})
        iw = float(p.get("imageWidth", 1))
        ih = float(p.get("imageHeight", 1))
        x = float(b.get("x", 0))
        y = float(b.get("y", 0))
        w = float(b.get("width", iw))
        h = float(b.get("height", ih))
        margins.append((x, y, max(0.0, iw - (x + w)), max(0.0, ih - (y + h))))
    if not margins:
        return

    left_m = median([m[0] for m in margins])
    top_m = median([m[1] for m in margins])
    right_m = median([m[2] for m in margins])
    bottom_m = median([m[3] for m in margins])
    tol = 15.0

    for p, m in zip(pages_payload, margins, strict=False):
        iw = int(p.get("imageWidth", 1))
        ih = int(p.get("imageHeight", 1))
        per_page = p.get("contentBounds", {"x": 0, "y": 0, "width": iw, "height": ih})
        is_outlier = any(abs(a - b) > tol for a, b in zip(m, (left_m, top_m, right_m, bottom_m), strict=False))
        if is_outlier:
            p["contentBounds"] = per_page
            p["contentBoundsMode"] = "per_page_outlier"
            continue

        gx = int(round(left_m))
        gy = int(round(top_m))
        gr = int(round(right_m))
        gb = int(round(bottom_m))
        gw = max(1, iw - gx - gr)
        gh = max(1, ih - gy - gb)
        p["contentBounds"] = {"x": gx, "y": gy, "width": gw, "height": gh}
        p["contentBoundsMode"] = "global_median"


def export_mock_viewer(pages: list[Page], out_root: Path, bookmarks: list[Bookmark] | None = None) -> None:
    mock_root = out_root / "mock"
    ensure_dir(mock_root)
    raw_pages_root = out_root / "annotated" / "pages_raw"

    bookmark_map = {
        b.bookmark_name: {
            "displayName": b.display_name,
            "activeSection": b.active_section,
            "sectionVisualIds": b.section_visual_ids,
        }
        for b in (bookmarks or [])
    }

    report_page_ids = [p.page_id for p in pages]
    page_name_by_id = {p.page_id: p.page_name for p in pages}

    payload_pages: list[dict[str, Any]] = []
    for idx, p in enumerate(pages, start=1):
        bg_rel = (
            f"../annotated/pages_raw/page_{idx:03d}.png"
            if (raw_pages_root / f"page_{idx:03d}.png").exists()
            else ""
        )
        image_width = int(round(p.width)) if p.width > 0 else 1
        image_height = int(round(p.height)) if p.height > 0 else 1
        content_bounds = {"x": 0, "y": 0, "width": image_width, "height": image_height}
        if bg_rel:
            image_path = (mock_root / bg_rel).resolve()
            if image_path.exists():
                try:
                    with Image.open(image_path) as image:
                        image_width, image_height = image.size
                        content_bounds = _detect_content_bounds(image)
                except Exception:
                    pass

        page_payload: dict[str, Any] = {
            "pageId": p.page_id,
            "pageName": p.page_name,
            "pageNameSafe": p.page_name_safe,
            "width": p.width,
            "height": p.height,
            "backgroundImage": bg_rel,
            "imageWidth": image_width,
            "imageHeight": image_height,
            "contentBounds": content_bounds,
            "contentBoundsMode": "per_page",
            "visuals": [],
        }

        for v in sorted(p.visuals, key=lambda it: it.seq):
            explicit_targets = [t for t in v.navigator_target_ids if t in page_name_by_id]
            if not explicit_targets and "navigator" in v.visual_type.lower():
                slots = max(1, (v.navigator_rows if v.navigator_rows > 0 else 1) * (v.navigator_columns if v.navigator_columns > 0 else len(report_page_ids)))
                explicit_targets = report_page_ids[: min(len(report_page_ids), slots)]

            page_payload["visuals"].append(
                {
                    "seq": v.seq,
                    "pageId": v.page_id,
                    "visualId": v.visual_id,
                    "type": v.visual_type,
                    "title": v.title,
                    "label": v.label,
                    "x": v.x,
                    "y": v.y,
                    "width": v.width,
                    "height": v.height,
                    "z": v.z,
                    "linkType": v.link_type,
                    "navigationSection": v.navigation_section,
                    "bookmarkTarget": v.bookmark_target,
                    "webUrl": v.web_url,
                    "isHidden": v.is_hidden,
                    "navigatorRows": v.navigator_rows,
                    "navigatorColumns": v.navigator_columns,
                    "navigatorOrientation": v.navigator_orientation,
                    "navigatorTargetPageIds": explicit_targets,
                }
            )

        payload_pages.append(page_payload)

    _apply_global_median_bounds(payload_pages)

    payload = {
        "bookmarks": bookmark_map,
        "pageOrderIds": report_page_ids,
        "pages": payload_pages,
    }
    report_json_text = json.dumps(payload, indent=2)
    app_js = APP_JS_TEMPLATE.replace("__REPORT_JSON__", report_json_text)

    (mock_root / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (mock_root / "styles.css").write_text(STYLES_CSS, encoding="utf-8")
    (mock_root / "app.js").write_text(app_js, encoding="utf-8")
    (mock_root / "report.json").write_text(report_json_text, encoding="utf-8")
