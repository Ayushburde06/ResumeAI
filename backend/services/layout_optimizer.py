"""
layout_optimizer.py — Post-render PDF inspection and spacing correction.

Uses PyMuPDF (fitz) to inspect rendered PDF bytes and detect:
  - overflow:             content bleeds past the bottom margin
  - sparse_bottom:        bottom 30%+ of a single page is empty white space
  - second_page_sparse:   a 2nd page exists but has < 15% content
  - crowded:              text blocks are packed too tightly (line height too small)

Then recommends spacing adjustments (font_size_delta, gap_deltas) to fix the issue.

This is the web-service equivalent of resume_builder/inspector/bedrock_inspector.py,
but uses PyMuPDF text-block analysis instead of vision models — no browser needed,
runs in ~50ms per page, suitable for real-time web requests.
"""
import logging
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# ── Thresholds (calibrated against A4 at 72dpi) ──────────────────────────────
# A4 = 595 x 842 points. With 0 margin @page and template padding (~40pt top/bottom),
# usable height is ~760pt. We measure fill as last_text_y / page_height.

SPARSE_BOTTOM_RATIO = 0.62   # single page, content fills < 62% → sparse_bottom
SECOND_PAGE_MIN_FILL = 0.15  # 2nd page fills < 15% → second_page_sparse
OVERFLOW_RATIO = 0.96        # content past 96% of page height → overflow
CROWDED_RATIO = 0.93         # content > 93% AND many text blocks → crowded


def inspect_pdf(pdf_bytes: bytes) -> dict:
    """
    Inspect rendered PDF bytes and return a verdict dict.

    Returns:
        {
            "page_count": int,
            "issues": list[str],
            "fill_ratios": list[float],   # per-page fill ratio (0-1)
            "last_text_y_ratio": float,   # bottom-most text / page height (last page)
            "adjustments": dict,          # recommended spacing deltas
        }
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.warning(f"PyMuPDF inspection failed: {e}")
        return {"page_count": 1, "issues": [], "fill_ratios": [1.0],
                "last_text_y_ratio": 1.0, "adjustments": {}}

    page_count = doc.page_count
    fill_ratios = []
    block_counts = []

    for i in range(page_count):
        page = doc[i]
        page_height = page.rect.height

        # Get text blocks with bounding boxes
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get("blocks", [])

        max_y = 0.0
        text_block_count = 0

        for block in blocks:
            if block.get("type", 0) != 0:  # 0 = text block, 1 = image
                continue
            bbox = block.get("bbox", [0, 0, 0, 0])
            block_bottom = bbox[3]
            if block_bottom > max_y:
                max_y = block_bottom
            text_block_count += 1

        fill_ratio = max_y / page_height if page_height > 0 else 1.0
        fill_ratios.append(fill_ratio)
        block_counts.append(text_block_count)

    doc.close()

    last_fill = fill_ratios[-1] if fill_ratios else 1.0
    issues = []

    if page_count > 1:
        # Multi-page: the goal is one page. A sparse 2nd page means we can tighten.
        if last_fill < SECOND_PAGE_MIN_FILL:
            issues.append("second_page_sparse")
        elif last_fill > OVERFLOW_RATIO:
            issues.append("overflow")
    else:
        # Single page
        if last_fill < SPARSE_BOTTOM_RATIO:
            issues.append("sparse_bottom")
        elif last_fill > OVERFLOW_RATIO and block_counts[-1] > 25:
            issues.append("crowded")

    adjustments = _compute_adjustments(issues, fill_ratios, page_count)

    result = {
        "page_count": page_count,
        "issues": issues,
        "fill_ratios": [round(r, 3) for r in fill_ratios],
        "last_text_y_ratio": round(last_fill, 3),
        "adjustments": adjustments,
    }
    logger.info(f"PDF inspection: {result}")
    return result


def _compute_adjustments(issues: list[str], fill_ratios: list[float], page_count: int) -> dict:
    """
    Compute spacing deltas based on detected issues.

    Positive deltas = expand spacing (for sparse content → fills the page).
    Negative deltas = shrink spacing (for overflow → collapses to one page).
    """
    if not issues:
        return {}

    # ── Shrink: overflow or second_page_sparse ───────────────────────────────
    if "overflow" in issues or "second_page_sparse" in issues:
        # If 2nd page is very sparse, be aggressive (collapse to 1 page)
        if "second_page_sparse" in issues and page_count > 1:
            return {
                "font_size_delta": -0.35,
                "line_height_delta": -0.03,
                "section_gap_delta": -2.0,
                "entry_gap_delta": -1.5,
                "title_gap_delta": -1.0,
            }
        # Regular overflow
        return {
            "font_size_delta": -0.25,
            "line_height_delta": -0.02,
            "section_gap_delta": -1.5,
            "entry_gap_delta": -1.0,
            "title_gap_delta": -0.8,
        }

    # ── Expand: sparse_bottom ────────────────────────────────────────────────
    if "sparse_bottom" in issues:
        fill = fill_ratios[-1] if fill_ratios else 0.5
        # Very sparse (< 40% fill) → big expansion
        if fill < 0.40:
            return {
                "font_size_delta": 0.5,
                "line_height_delta": 0.04,
                "section_gap_delta": 3.0,
                "entry_gap_delta": 2.0,
                "title_gap_delta": 1.5,
            }
        # Moderately sparse → medium expansion
        return {
            "font_size_delta": 0.3,
            "line_height_delta": 0.02,
            "section_gap_delta": 2.0,
            "entry_gap_delta": 1.2,
            "title_gap_delta": 1.0,
        }

    # ── Crowded: increase line height only ───────────────────────────────────
    if "crowded" in issues:
        return {
            "font_size_delta": 0.0,
            "line_height_delta": 0.03,
            "section_gap_delta": 0.5,
            "entry_gap_delta": 0.0,
            "title_gap_delta": 0.0,
        }

    return {}


# ── Layout clamps (must match _adaptive_layout ranges + headroom) ────────────
_CLAMPS = {
    "font_size":   (7.5, 10.5),
    "line_height": (1.15, 1.55),
    "section_gap": (3.0, 14.0),
    "entry_gap":   (1.5, 9.0),
    "title_gap":   (2.0, 9.0),
}


def apply_adjustments(layout: dict, adjustments: dict) -> dict:
    """
    Apply recommended deltas to a layout dict, with hard clamping.

    Args:
        layout:      Current layout dict (font_size, line_height, section_gap, etc.)
        adjustments: Delta dict from inspect_pdf()

    Returns:
        New layout dict with adjusted + clamped values.
    """
    if not adjustments:
        return layout

    new = dict(layout)
    for key, (lo, hi) in _CLAMPS.items():
        delta = adjustments.get(f"{key}_delta", 0.0)
        new[key] = round(max(lo, min(hi, layout.get(key, lo) + delta)), 3)
    return new


def needs_trim(resume_data: dict) -> bool:
    """
    L1 pre-check: estimate if content is too dense to fit one page
    even at minimum spacing. If so, the caller should trim bullets/entries
    before rendering.
    """
    total_bullets = 0
    entry_count = 0
    for section in ("experience", "projects"):
        for entry in resume_data.get(section, []) or []:
            entry_count += 1
            bullets = entry.get("bullets", []) if isinstance(entry, dict) else []
            if isinstance(bullets, list):
                total_bullets += len([b for b in bullets if str(b).strip()])

    # Heuristic: > 28 bullets or > 8 entries → likely overflow at any spacing
    return total_bullets > 28 or entry_count > 8


def trim_content(resume_data: dict) -> dict:
    """
    L1 pre-render content trimming for dense resumes.

    Strategy:
    1. Cap bullets per entry (3 for experience, 2 for projects)
    2. If still too many entries, drop the lowest-relevance projects first
    """
    import copy
    data = copy.deepcopy(resume_data)

    # Cap bullets in experience to 3
    for entry in data.get("experience", []) or []:
        bullets = entry.get("bullets", [])
        if isinstance(bullets, list) and len(bullets) > 3:
            entry["bullets"] = bullets[:3]

    # Cap bullets in projects to 2
    for entry in data.get("projects", []) or []:
        bullets = entry.get("bullets", [])
        if isinstance(bullets, list) and len(bullets) > 2:
            entry["bullets"] = bullets[:2]

    # If too many entries, trim projects first (less critical than experience)
    exp = data.get("experience", []) or []
    proj = data.get("projects", []) or []
    if len(exp) + len(proj) > 7:
        # Keep max 4 experience, max 3 projects
        if len(exp) > 4:
            data["experience"] = exp[:4]
        if len(proj) > 3:
            data["projects"] = proj[:3]
        # If still > 7, drop projects further
        proj = data.get("projects", []) or []
        if len(data.get("experience", [])) + len(proj) > 7:
            data["projects"] = proj[: max(0, 7 - len(data.get("experience", [])))]

    return data
