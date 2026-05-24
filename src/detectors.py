from src.config import A4, BIN, DETECT, INTRINSICS, MEASURE, SCENE
from src.utils import clamp, rect_corners_from_xywh


def _clip_rect(x, y, w, h, img_w, img_h):
    if x < 0:
        w += x
        x = 0
    if y < 0:
        h += y
        y = 0
    if (x + w) > img_w:
        w = img_w - x
    if (y + h) > img_h:
        h = img_h - y
    if w < 2 or h < 2:
        return None
    return (x, y, w, h)


def binary_auto(gray_img, stats_roi=None):
    if stats_roi is None:
        st = gray_img.get_statistics()
    else:
        st = gray_img.get_statistics(roi=stats_roi)

    mean_v = int(st.mean())
    if BIN["adaptive"]:
        thr = int(clamp(mean_v + BIN["mean_offset"], BIN["min_thr"], BIN["max_thr"]))
    else:
        thr = BIN["fixed_thr"]

    gray_img.binary([(thr, 255)])

    if BIN["open_n"] > 0:
        gray_img.open(BIN["open_n"])
    if BIN["close_n"] > 0:
        gray_img.close(BIN["close_n"])

    return gray_img, {"thr": thr, "mean": mean_v}


def paper_width_px_from_rect(a4_rect):
    if a4_rect is None:
        return 0.0
    _, _, w, h = a4_rect
    # The current A4 detector returns an axis-aligned box.
    # For a portrait A4 target, the short side is our best width proxy.
    return float(min(w, h))


def estimate_distance_mm_from_a4_rect(a4_rect):
    paper_width_px = paper_width_px_from_rect(a4_rect)
    if paper_width_px <= 1.0:
        return 0.0

    d_cam_mm = (MEASURE["focal_px"] * A4["width_mm"]) / paper_width_px
    return d_cam_mm * MEASURE["distance_gain"] + MEASURE["distance_offset_mm"]


def estimate_size_mm_from_shape_rect(shape_rect, a4_rect, shape_type):
    if shape_rect is None or a4_rect is None:
        return 0.0

    paper_width_px = paper_width_px_from_rect(a4_rect)
    if paper_width_px <= 1.0:
        return 0.0

    _, _, sw, sh = shape_rect
    if shape_type == "CIRCLE":
        shape_px = 0.5 * (sw + sh)
    else:
        shape_px = float(max(sw, sh))

    size_mm = (shape_px / paper_width_px) * A4["width_mm"]
    return size_mm * MEASURE["size_gain"] + MEASURE["size_offset_mm"]


def detect_anchor_blob(gray_img, roi, thr):
    if roi is None:
        return None, []

    dark_hi = int(clamp(thr - DETECT["anchor_dark_offset"], 20, 160))
    blobs = gray_img.find_blobs(
        [(0, dark_hi)],
        roi=roi,
        pixels_threshold=DETECT["anchor_pixels_threshold"],
        area_threshold=DETECT["anchor_area_threshold"],
        merge=True,
    )
    if not blobs:
        return None, []

    roi_area = roi[2] * roi[3]
    roi_cx = roi[0] + roi[2] // 2
    roi_cy = roi[1] + roi[3] // 2
    candidates = []
    best = None
    best_score = -1000000

    for b in blobs:
        x, y, w, h = b.rect()
        if w < DETECT["anchor_min_side_px"] or h < DETECT["anchor_min_side_px"]:
            continue

        area = b.pixels()
        area_ratio = float(area) / float(roi_area)
        if area_ratio < DETECT["anchor_min_area_ratio"] or area_ratio > DETECT["anchor_max_area_ratio"]:
            continue

        dx = abs(b.cx() - roi_cx)
        dy = abs(b.cy() - roi_cy)
        score = area - (dx + dy) * DETECT["anchor_center_score_weight"]
        cand = {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "cx": b.cx(),
            "cy": b.cy(),
            "score": score,
        }
        candidates.append(cand)
        if score > best_score:
            best_score = score
            best = cand

    candidates.sort(key=lambda z: z["score"], reverse=True)
    return best, candidates


def detect_shape_blobs(gray_img, roi, thr):
    if roi is None:
        return None, []

    dark_hi = int(clamp(thr - DETECT["shape_dark_offset"], 20, 180))
    blobs = gray_img.find_blobs(
        [(0, dark_hi)],
        roi=roi,
        pixels_threshold=DETECT["shape_pixels_threshold"],
        area_threshold=DETECT["shape_area_threshold"],
        merge=False,
    )
    if not blobs:
        return None, []

    roi_area = roi[2] * roi[3]
    roi_cx = roi[0] + roi[2] // 2
    roi_cy = roi[1] + roi[3] // 2
    candidates = []
    best = None
    best_score = -1000000

    for b in blobs:
        x, y, w, h = b.rect()
        if w < DETECT["shape_min_side_px"] or h < DETECT["shape_min_side_px"]:
            continue

        area = b.pixels()
        area_ratio = float(area) / float(roi_area)
        if area_ratio < DETECT["shape_min_area_ratio"] or area_ratio > DETECT["shape_max_area_ratio"]:
            continue

        aspect = float(w) / float(h)
        if abs(aspect - 1.0) > DETECT["shape_aspect_tol"]:
            continue

        box_area = w * h
        if box_area <= 0:
            continue

        fill_ratio = float(area) / float(box_area)
        shape_type = "ANY"
        if DETECT["tri_fill_min"] <= fill_ratio <= DETECT["tri_fill_max"]:
            shape_type = "TRI"
        elif DETECT["circle_fill_min"] <= fill_ratio <= DETECT["circle_fill_max"]:
            shape_type = "CIRCLE"
        elif DETECT["rect_fill_min"] <= fill_ratio <= DETECT["rect_fill_max"]:
            shape_type = "RECT"
        else:
            continue

        dx = abs(b.cx() - roi_cx)
        dy = abs(b.cy() - roi_cy)
        aspect_penalty = abs(aspect - 1.0) * 120
        score = area - (dx + dy) * DETECT["shape_center_score_weight"] - aspect_penalty
        if shape_type == "TRI":
            score += 20
        cand = {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "cx": b.cx(),
            "cy": b.cy(),
            "aspect": aspect,
            "fill_ratio": fill_ratio,
            "shape_type": shape_type,
            "score": score,
        }
        candidates.append(cand)
        if score > best_score:
            best_score = score
            best = cand

    candidates.sort(key=lambda z: z["score"], reverse=True)
    return best, candidates


def detect_a4_blob(bw_img, search_roi=None, anchor=None):
    blobs = bw_img.find_blobs(
        [(250, 255)],
        roi=search_roi,
        pixels_threshold=DETECT["paper_pixels_threshold"],
        area_threshold=DETECT["paper_area_threshold"],
        merge=False,
    )
    if not blobs:
        return None, []

    img_w = bw_img.width()
    img_h = bw_img.height()
    search_area = img_w * img_h
    if search_roi is not None:
        search_area = search_roi[2] * search_roi[3]
    if search_roi is None:
        cx0 = img_w // 2
        cy0 = img_h // 2
        rw = img_w
        rh = img_h
    else:
        cx0 = search_roi[0] + search_roi[2] // 2
        cy0 = search_roi[1] + search_roi[3] // 2
        _, _, rw, rh = search_roi
    best = None
    best_score = -1000000
    candidates = []
    anchor_candidates = []

    for b in blobs:
        x, y, w, h = b.rect()
        area = b.area()
        pixels = b.pixels()
        if area < search_area * DETECT["a4_min_area_ratio"] or h <= 0:
            continue
        if w > int(rw * DETECT["a4_max_w_ratio_in_search"]):
            continue
        if h > int(rh * DETECT["a4_max_h_ratio_in_search"]):
            continue

        aspect = float(w) / float(h)
        if aspect < DETECT["a4_aspect_min"] or aspect > DETECT["a4_aspect_max"]:
            continue

        box_area = w * h
        if box_area <= 0:
            continue

        fill_ratio = float(pixels) / float(box_area)
        if fill_ratio < DETECT["a4_fill_min"] or fill_ratio > DETECT["a4_fill_max"]:
            continue

        anchor_hit = False
        anchor_penalty = 0
        if anchor is not None:
            ax = anchor["cx"]
            ay = anchor["cy"]
            anchor_hit = not (ax < x or ax > (x + w) or ay < y or ay > (y + h))
            if anchor_hit:
                anchor_penalty = abs(ax - (x + w // 2)) + abs(ay - (y + h // 2))

        cxb = x + w // 2
        cyb = y + h // 2
        dx = abs(cxb - cx0)
        dy = abs(cyb - cy0)
        if SCENE["paper_is_centered"]:
            if dx > int(rw * SCENE["a4_center_tol_ratio"]):
                continue
            if dy > int(rh * SCENE["a4_center_tol_ratio"]):
                continue

        area_ratio = float(pixels) / float(search_area)
        aspect_err = abs(aspect - DETECT["a4_aspect_target"])

        score = (
            pixels
            + area_ratio * 500
            - (dx + dy) * DETECT["a4_center_score_weight"]
            - aspect_err * DETECT["a4_aspect_score_weight"]
            - anchor_penalty * 4
        )
        if anchor_hit:
            score += 500

        cand = {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "score": score,
            "anchor_hit": anchor_hit,
        }
        candidates.append(cand)
        if anchor_hit:
            anchor_candidates.append(cand)
        if score > best_score:
            best_score = score
            best = (x, y, w, h)

    if anchor_candidates:
        anchor_candidates.sort(key=lambda z: z["score"], reverse=True)
        best = (
            anchor_candidates[0]["x"],
            anchor_candidates[0]["y"],
            anchor_candidates[0]["w"],
            anchor_candidates[0]["h"],
        )
    elif best is None:
        return None, candidates

    x, y, w, h = best
    expand_px = DETECT["a4_expand_px"]
    expanded = _clip_rect(
        x - expand_px,
        y - expand_px,
        w + 2 * expand_px,
        h + 2 * expand_px,
        bw_img.width(),
        bw_img.height(),
    )
    if expanded is not None:
        x, y, w, h = expanded

    return {"rect": (x, y, w, h), "corners": rect_corners_from_xywh(x, y, w, h)}, candidates
