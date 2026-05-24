from src.config import DEBUG_VIEW, SCENE


def clip_roi(x, y, w, h, img_w, img_h):
    if x < 0:
        x = 0
    if y < 0:
        y = 0
    if x + w > img_w:
        w = img_w - x
    if y + h > img_h:
        h = img_h - y
    if w < 2 or h < 2:
        return None
    return (x, y, w, h)


def center_roi(img_w, img_h):
    rw = int(img_w * SCENE["search_roi_w_ratio"])
    rh = int(img_h * SCENE["search_roi_h_ratio"])
    x = (img_w - rw) // 2
    y = (img_h - rh) // 2
    return (x, y, rw, rh)


def stats_roi(center_search_roi):
    if SCENE["stats_from_center_roi_only"]:
        return center_search_roi
    return None


def inner_roi(a4_rect, img_w, img_h):
    if a4_rect is None:
        return None
    x, y, w, h = a4_rect
    m = SCENE["inner_margin_px"]
    return clip_roi(x + m, y + m, w - 2 * m, h - 2 * m, img_w, img_h)


def draw_roi(img, roi, color, thickness=1):
    if roi is None:
        return
    img.draw_rectangle(roi[0], roi[1], roi[2], roi[3], color=color, thickness=thickness)


def draw_cross(img, x, y, color, size=4):
    img.draw_line(x - size, y, x + size, y, color=color, thickness=1)
    img.draw_line(x, y - size, x, y + size, color=color, thickness=1)


def draw_shape_candidates(img, candidates, color):
    if not candidates:
        return
    for idx, cand in enumerate(candidates):
        thickness = 2 if idx == 0 else 1
        img.draw_rectangle(cand["x"], cand["y"], cand["w"], cand["h"], color=color, thickness=thickness)


def draw_a4_candidates(img, candidates, color):
    if not candidates:
        return
    for cand in candidates:
        img.draw_rectangle(cand["x"], cand["y"], cand["w"], cand["h"], color=color, thickness=1)


def mask_outside_roi_white(img, roi):
    if roi is None:
        return
    rx, ry, rw, rh = roi
    w = img.width()
    h = img.height()
    if ry > 0:
        img.draw_rectangle(0, 0, w, ry, color=255, fill=True)
    if (ry + rh) < h:
        img.draw_rectangle(0, ry + rh, w, h - (ry + rh), color=255, fill=True)
    if rx > 0:
        img.draw_rectangle(0, ry, rx, rh, color=255, fill=True)
    if (rx + rw) < w:
        img.draw_rectangle(rx + rw, ry, w - (rx + rw), rh, color=255, fill=True)


def apply_debug_view(
    img,
    bw,
    center_search_roi,
    threshold_stats_roi,
    a4_rect,
    a4_candidates,
    anchor=None,
    inner_search_roi=None,
    shape_rect=None,
    shape_candidates=None,
):
    display_mode = DEBUG_VIEW["display_mode"]

    if display_mode == "binary":
        if DEBUG_VIEW["mask_outside_center_roi_in_binary"]:
            mask_outside_roi_white(bw, center_search_roi)
        img.replace(bw)

    base_color = 180 if display_mode == "binary" else 255
    if DEBUG_VIEW["draw_center_roi"]:
        draw_roi(img, center_search_roi, base_color)
    if DEBUG_VIEW["draw_stats_roi"] and threshold_stats_roi is not None:
        draw_roi(img, threshold_stats_roi, 220 if display_mode == "binary" else 255)
    if DEBUG_VIEW.get("draw_a4_candidates", True):
        draw_a4_candidates(img, a4_candidates, 140 if display_mode == "binary" else 255)
    if DEBUG_VIEW["draw_a4_rect"] and a4_rect is not None:
        draw_roi(img, a4_rect, 96 if display_mode == "binary" else 255, thickness=2)
    if DEBUG_VIEW.get("draw_inner_roi", True) and inner_search_roi is not None:
        draw_roi(img, inner_search_roi, 150 if display_mode == "binary" else 255)
    if DEBUG_VIEW.get("draw_shape_candidates", True) and shape_candidates:
        draw_shape_candidates(img, shape_candidates, 110 if display_mode == "binary" else 255)
    if DEBUG_VIEW.get("draw_shape_rect", True) and shape_rect is not None:
        draw_roi(img, shape_rect, 40 if display_mode == "binary" else 255, thickness=2)
    if DEBUG_VIEW.get("draw_anchor", True) and anchor is not None:
        draw_cross(img, anchor[0], anchor[1], 64 if display_mode == "binary" else 255)
