from __future__ import annotations

import json
from pathlib import Path

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
      </div>
      <div class="canvas-scroll">
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
.sidebar { padding: 16px; border-right: 1px solid #cbd5e1; background: #ffffffcc; backdrop-filter: blur(6px); overflow-y: auto; }
.sidebar h1 { margin: 0 0 12px 0; font-size: 20px; }
.sidebar input { width: 100%; padding: 10px; border: 1px solid #94a3b8; border-radius: 8px; margin-bottom: 12px; }
#pageList { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
#pageList button { width: 100%; text-align: left; border: 1px solid #cbd5e1; background: #fff; padding: 10px; border-radius: 8px; cursor: pointer; }
#pageList button.active { background: #dbeafe; border-color: #60a5fa; }
.content { display: grid; grid-template-rows: auto 1fr; min-width: 0; }
.page-header { padding: 14px 18px; border-bottom: 1px solid #cbd5e1; background: #ffffffcc; backdrop-filter: blur(6px); }
.page-header h2 { margin: 0 0 4px 0; font-size: 20px; }
.page-header p { margin: 0; font-size: 13px; color: #475569; }
.canvas-scroll { overflow: auto; padding: 16px; }
.page-canvas {
  position: relative;
  background: #fff;
  border: 1px solid #cbd5e1;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.1);
  background-size: 100% 100%;
  background-repeat: no-repeat;
}
.visual-box {
  position: absolute;
  border: 2px solid rgba(8, 47, 73, 0.85);
  background: rgba(255, 255, 0, 0.18);
  border-radius: 4px;
  cursor: default;
}
.visual-badge {
  position: absolute;
  top: 4px;
  left: 4px;
  background: #ffef00;
  color: #000;
  border: 2px solid #000;
  padding: 2px 7px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 0.3px;
  box-shadow: 0 0 0 2px #fff;
}
.visual-box.actionable {
  border-color: rgba(22, 101, 52, 0.95);
  background: rgba(34, 197, 94, 0.16);
  cursor: pointer;
}
.visual-box.actionable .visual-badge {
  background: #22c55e;
  color: #052e16;
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
  activeBookmarkName: ''
};

const IGNORED_TYPES = new Set(['textbox', 'basicshape', 'image']);

async function init() {
  state.filteredPages = state.report.pages.slice();
  state.selectedPageId = state.filteredPages[0]?.pageId || null;
  wireSearch();
  renderPageList();
  renderSelectedPage();
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

function renderPageList() {
  const pageList = document.getElementById('pageList');
  pageList.innerHTML = '';
  for (const page of state.filteredPages) {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.textContent = `${page.pageName} (${page.visuals.length})`;
    btn.className = page.pageId === state.selectedPageId ? 'active' : '';
    btn.onclick = () => {
      state.selectedPageId = page.pageId;
      renderPageList();
      renderSelectedPage();
    };
    li.appendChild(btn);
    pageList.appendChild(li);
  }
}

function isActionable(v) {
  const t = String(v.linkType || '').toLowerCase();
  return t === 'pagenavigation' || t === 'bookmark' || t === 'weburl' || t === 'back';
}

function getDrawableVisuals(page) {
  const ordered = page.visuals.slice().sort((a, b) => (a.z - b.z) || (a.y - b.y) || (a.x - b.x));
  let filtered = ordered.filter(
    (v) => !v.isHidden && !IGNORED_TYPES.has(String(v.type || '').toLowerCase())
  );
  if (state.activeBookmarkName) {
    const bookmark = state.report.bookmarks[state.activeBookmarkName];
    const sectionIds = Array.isArray(bookmark?.sectionVisualIds) ? bookmark.sectionVisualIds : [];
    if (bookmark?.activeSection === page.pageId && sectionIds.length > 0) {
      const idSet = new Set(sectionIds);
      filtered = filtered.filter((v) => idSet.has(v.visualId));
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
  const linkType = String(visual.linkType || '').toLowerCase();
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
    if (url.startsWith('http://') || url.startsWith('https://')) {
      window.open(url, '_blank', 'noopener');
    }
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

  pageTitle.textContent = page.pageName;
  const drawable = getDrawableVisuals(page);
  const bookmarkText = state.activeBookmarkName ? ` | bookmark: ${state.activeBookmarkName}` : '';
  pageMeta.textContent = `${page.width} x ${page.height} | labels: ${drawable.length} (filtered)${bookmarkText}`;
  canvas.style.width = `${page.width}px`;
  canvas.style.height = `${page.height}px`;
  canvas.style.backgroundImage = page.backgroundImage ? `url('${page.backgroundImage}')` : 'none';
  canvas.innerHTML = '';

  for (const v of drawable) {
    const box = document.createElement('div');
    box.className = 'visual-box';
    if (isActionable(v)) {
      box.classList.add('actionable');
      box.addEventListener('click', () => applyAction(v));
    }
    box.style.left = `${Math.max(0, v.x)}px`;
    box.style.top = `${Math.max(0, v.y)}px`;
    box.style.width = `${Math.max(24, v.width)}px`;
    box.style.height = `${Math.max(20, v.height)}px`;
    box.style.zIndex = String(Math.round(v.z) + 1);
    box.title = `V${String(v.drawSeq).padStart(3, '0')} | ${v.type} | ${v.linkType || 'NoAction'}`;

    const badge = document.createElement('div');
    badge.className = 'visual-badge';
    badge.textContent = String(v.drawSeq).padStart(3, '0');

    box.appendChild(badge);
    canvas.appendChild(box);
  }
}

init().catch((err) => {
  console.error(err);
  const canvas = document.getElementById('pageCanvas');
  canvas.textContent = 'Failed to initialize viewer data';
});
"""


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

    payload = {
        "bookmarks": bookmark_map,
        "pages": [
            {
                "pageId": p.page_id,
                "pageName": p.page_name,
                "pageNameSafe": p.page_name_safe,
                "width": p.width,
                "height": p.height,
                "backgroundImage": (
                    f"../annotated/pages_raw/page_{idx:03d}.png"
                    if (raw_pages_root / f"page_{idx:03d}.png").exists()
                    else ""
                ),
                "visuals": [
                    {
                        "seq": v.seq,
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
                    }
                    for v in sorted(p.visuals, key=lambda it: it.seq)
                ],
            }
            for idx, p in enumerate(pages, start=1)
        ]
    }

    report_json_text = json.dumps(payload, indent=2)
    app_js = APP_JS_TEMPLATE.replace("__REPORT_JSON__", report_json_text)

    (mock_root / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (mock_root / "styles.css").write_text(STYLES_CSS, encoding="utf-8")
    (mock_root / "app.js").write_text(app_js, encoding="utf-8")
    (mock_root / "report.json").write_text(report_json_text, encoding="utf-8")
