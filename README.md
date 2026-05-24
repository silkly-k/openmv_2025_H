# OpenMV C Topic Starter Template

This project is a centered-scene OpenMV starter for the 2025 NUEDC C-topic
(monocular vision measurement).

Reference:
[NUEDC C topic page](https://res.nuedc-training.com.cn/topic/2025/topic_122.html)

## Files

- `boot.py`: startup banner, then OpenMV runs `main.py`
- `main.py`: main loop and IDE-facing debug overlay
- `src/config.py`: camera, scene, binary, debug, and detection configuration
- `src/pipeline.py`: main processing pipeline
- `src/detectors.py`: binary, A4, and shape detection
- `src/roi.py`: centered ROI helpers and debug drawing
- `src/utils.py`: helper math, filters, and UART formatting
- `docs/NEXT_STEPS.md`: exact implementation checklist

## Quick run

1. Open `main.py` in OpenMV IDE.
2. Copy all `.py` files to OpenMV storage.
3. Run and verify FPS/status text on frame.
4. Power cycle and verify auto-start.
