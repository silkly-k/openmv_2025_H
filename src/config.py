import sensor


CAM_CFG = {
    "pixformat": sensor.GRAYSCALE,
    "framesize": sensor.VGA,
    "warmup_ms": 1200,
    "auto_gain": False,
    "auto_whitebal": False,
}


SCENE = {
    "paper_is_centered": True,
    "search_roi_w_ratio": 0.45,
    "search_roi_h_ratio": 0.65,
    "stats_from_center_roi_only": True,
    "a4_center_tol_ratio": 0.40,
    "inner_margin_px": 16,
}


DEBUG_VIEW = {
    "display_mode": "binary",  # binary / source / overlay
    "mask_outside_center_roi_in_binary": True,
    "draw_center_roi": True,
    "draw_stats_roi": True,
    "draw_a4_rect": True,
    "draw_a4_candidates": True,
    "draw_anchor": True,
    "draw_inner_roi": True,
    "draw_shape_candidates": True,
    "draw_shape_rect": True,
}


A4 = {"width_mm": 210.0, "height_mm": 297.0}

INTRINSICS = {"fx": 560.0, "fy": 560.0, "cx": 320.0, "cy": 240.0}


MEASURE = {
    # Engineering-version measurement parameters.
    # Replace these with real calibration results after distance sampling.
    "focal_px": 560.0,
    "distance_gain": 0.884,
    "distance_offset_mm": 38.0,
    "size_gain": 1.043,
    "size_offset_mm": 0.0,
}


BIN = {
    "adaptive": True,
    "mean_offset": 8,
    "min_thr": 60,
    "max_thr": 210,
    "fixed_thr": 90,
    "open_n": 0,
    "close_n": 1,
}



DETECT = {
    "paper_pixels_threshold": 80,
    "paper_area_threshold": 80,
    "a4_min_area_ratio": 0.02,
    "a4_aspect_min": 0.55,
    "a4_aspect_max": 0.90,
    "a4_fill_min": 0.45,
    "a4_fill_max": 0.98,
    "a4_expand_px": 4,
    "a4_aspect_target": 0.707,
    "a4_center_score_weight": 8,
    "a4_aspect_score_weight": 260,
    "a4_max_w_ratio_in_search": 0.92,
    "a4_max_h_ratio_in_search": 0.92,
    "anchor_dark_offset": 25,
    "anchor_pixels_threshold": 50,
    "anchor_area_threshold": 50,
    "anchor_min_side_px": 10,
    "anchor_min_area_ratio": 0.0004,
    "anchor_max_area_ratio": 0.12,
    "anchor_center_score_weight": 3,
    "shape_dark_offset": 25,
    "shape_pixels_threshold": 50,
    "shape_area_threshold": 50,
    "shape_min_side_px": 10,
    "shape_min_area_ratio": 0.0005,
    "shape_max_area_ratio": 0.25,
    "shape_center_score_weight": 2,
    "shape_aspect_tol": 0.40,
    "rect_fill_min": 0.84,
    "rect_fill_max": 1.00,
    "circle_fill_min": 0.58,
    "circle_fill_max": 0.84,
    "tri_fill_min": 0.32,
    "tri_fill_max": 0.62,
}


STABILITY = {}


PERF = {}
