def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def rect_corners_from_xywh(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def format_uart_v2(mode, valid, confidence, distance_mm, size_mm):
    v = 1 if valid else 0
    conf = int(clamp(confidence, 0.0, 1.0) * 100)
    return "MODE=%s,VALID=%d,CONF=%d,D=%.1f,X=%.1f" % (
        mode,
        v,
        conf,
        distance_mm,
        size_mm,
    )


class EMAFilter:
    def __init__(self, alpha):
        self.alpha = alpha
        self.value = None

    def update(self, x):
        if self.value is None:
            self.value = x
        else:
            self.value = self.alpha * x + (1.0 - self.alpha) * self.value
        return self.value
