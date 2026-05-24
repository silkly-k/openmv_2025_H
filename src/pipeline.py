from src.detectors import (
    binary_auto,
    detect_a4_blob,
    detect_anchor_blob,
    detect_shape_blobs,
    estimate_distance_mm_from_a4_rect,
    estimate_size_mm_from_shape_rect,
)
from src.roi import apply_debug_view, center_roi, inner_roi, stats_roi
from src.utils import format_uart_v2


def process_frame(img):
    bw = img.copy()
    if bw.format() != 1:
        bw = bw.to_grayscale()

    center_search_roi = center_roi(bw.width(), bw.height())
    threshold_stats_roi = stats_roi(center_search_roi)
    bw, bin_dbg = binary_auto(bw, stats_roi=threshold_stats_roi)
    thr = bin_dbg["thr"]
    mean_v = bin_dbg["mean"]

    anchor, anchor_candidates = detect_anchor_blob(bw, center_search_roi, thr)
    anchor_point = None
    if anchor is not None:
        anchor_point = (anchor["cx"], anchor["cy"])

    a4, a4_candidates = detect_a4_blob(bw, search_roi=center_search_roi, anchor=anchor)
    if a4 is None:
        apply_debug_view(
            img,
            bw,
            center_search_roi,
            threshold_stats_roi,
            None,
            a4_candidates,
            anchor=anchor_point,
        )
        return {
            "status": "NO_A4 T=%d M=%d" % (thr, mean_v),
            "d_mm": 0.0,
            "x_mm": 0.0,
        }

    a4_rect = a4["rect"]
    distance_mm = estimate_distance_mm_from_a4_rect(a4_rect)
    shape_roi = inner_roi(a4_rect, bw.width(), bw.height())
    shape_blob, shape_candidates = detect_shape_blobs(bw, shape_roi, thr)
    shape_rect = None
    best_shape_type = "ANY"
    if shape_blob is not None:
        shape_rect = (shape_blob["x"], shape_blob["y"], shape_blob["w"], shape_blob["h"])
        best_shape_type = shape_blob["shape_type"]
    shape_count = len(shape_candidates) if shape_candidates else 0
    tri_count = 0
    rect_count = 0
    circle_count = 0
    if shape_candidates:
        for cand in shape_candidates:
            if cand["shape_type"] == "TRI":
                tri_count += 1
            elif cand["shape_type"] == "RECT":
                rect_count += 1
            elif cand["shape_type"] == "CIRCLE":
                circle_count += 1

    apply_debug_view(
        img,
        bw,
        center_search_roi,
        threshold_stats_roi,
        a4_rect,
        a4_candidates,
        anchor=anchor_point,
        inner_search_roi=shape_roi,
        shape_rect=shape_rect,
        shape_candidates=shape_candidates,
    )

    if shape_count <= 0:
        status = "A4 D=%.0f T=%d" % (distance_mm, thr)
        return {
            "status": "A4 D=%.0f T=%d" % (distance_mm, thr),
            "d_mm": distance_mm,
            "x_mm": 0.0,
        }
    else:
        mode = "SHAPE"
        if rect_count >= tri_count and rect_count >= circle_count and rect_count > 0:
            mode = "RECT"
        elif tri_count >= rect_count and tri_count >= circle_count and tri_count > 0:
            mode = "TRI"
        elif circle_count > 0:
            mode = "CIRCLE"
        size_mm = estimate_size_mm_from_shape_rect(shape_rect, a4_rect, best_shape_type)
        status = "%s D=%.0f X=%.0f" % (mode, distance_mm, size_mm)
        return {
            "status": "%s D=%.0f X=%.0f" % (mode, distance_mm, size_mm),
            "d_mm": distance_mm,
            "x_mm": size_mm,
        }
    return {"status": status, "uart_line": uart_line}
