"""
Audio-reactive orb HUD — the JARVIS-style centerpiece.

Frameless, translucent, always-on-top. A glowing reactor orb that breathes when
idle, pulses with your voice, draws a real-time circular waveform during speech,
shifts colour by state, and shows a live caption (what you said / IU's reply).

Three satellite nodes sit at equal angles around the orb — Logs, Memory,
Settings — each opening its window. Drag the orb to move; double-click to hide.
"""

import math
from collections import deque

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QPushButton, QWidget

_STATE_RGB = {
    "listening":    (124, 108, 252),
    "transcribing": (251, 191, 36),
    "thinking":     (251, 191, 36),
    "speaking":     (74, 222, 128),
    "dictating":    (248, 113, 113),
    "paused":       (138, 143, 168),
}

_BARS = 72            # waveform spokes
_CX = 180.0           # orb centre x (window is 360 wide)
_CY = 175.0           # orb centre y
_SAT_RADIUS = 140     # distance of satellite buttons from centre
_SAT_SIZE = 8

# Tiny transparent dots — faint until hovered, so they don't fight the orb
_SAT_STYLE = """
QPushButton {
    background: transparent;
    border: 1px solid rgba(180,170,255,140);
    border-radius: 4px;
}
QPushButton:hover {
    background: rgba(124,108,252,90);
    border: 1px solid rgba(190,180,255,240);
}
QPushButton:pressed { background: rgba(91,79,214,170); }
"""

# Caption timing (frames @ ~30fps)
_HOLD_FRAMES = 150    # ~5s fully visible
_FADE_FRAMES = 45     # ~1.5s fade-out


class OrbWidget(QWidget):
    open_logs = pyqtSignal()
    open_memory = pyqtSignal()
    open_settings = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint   # no macOS rounded-rect shadow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.resize(360, 460)

        self._state = "listening"
        self._level = 0.0
        self._target_level = 0.0
        self._phase = 0.0
        self._history = deque([0.0] * _BARS, maxlen=_BARS)
        self._caption_heard = ""
        self._caption_reply = ""
        self._caption_age = 9999      # frames since caption last changed
        self._reveal = 0              # chars of reply revealed (typewriter)
        self._drag_pos = None

        self._make_satellites()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    # ── Satellite nodes ──────────────────────────────────────────────────────
    def _make_satellites(self):
        # 3 identical empty transparent circles — Settings top, Logs + Memory bottom.
        # No glyphs; hover tooltip + fixed position identify each.
        defs = [
            ("Settings", self.open_settings, -90),
            ("Logs", self.open_logs, 150),
            ("Memory", self.open_memory, 30),
        ]
        self._sat_buttons = []
        for tip, sig, ang in defs:
            btn = QPushButton("", self)
            btn.setToolTip(tip)
            btn.setFixedSize(_SAT_SIZE, _SAT_SIZE)
            btn.setStyleSheet(_SAT_STYLE)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(sig)
            rad = math.radians(ang)
            cx = _CX + _SAT_RADIUS * math.cos(rad) - _SAT_SIZE / 2
            cy = _CY + _SAT_RADIUS * math.sin(rad) - _SAT_SIZE / 2
            btn.move(int(cx), int(cy))
            self._sat_buttons.append(btn)
        self._restyle_satellites()

    def _restyle_satellites(self):
        """Tint the dots to the current state colour so the whole HUD shifts together."""
        r, g, b = _STATE_RGB.get(self._state, _STATE_RGB["listening"])
        lr, lg, lb = min(r + 60, 255), min(g + 60, 255), min(b + 60, 255)
        style = f"""
        QPushButton {{
            background: transparent;
            border: 1px solid rgba({lr},{lg},{lb},150);
            border-radius: {_SAT_SIZE // 2}px;
        }}
        QPushButton:hover {{
            background: rgba({r},{g},{b},110);
            border: 1px solid rgba({lr},{lg},{lb},245);
        }}
        QPushButton:pressed {{ background: rgba({r},{g},{b},180); }}
        """
        for btn in self._sat_buttons:
            btn.setStyleSheet(style)

    # ── Slots ─────────────────────────────────────────────────────────────────
    def set_level(self, level: float):
        self._target_level = max(0.0, min(1.0, level))
        self._history.append(self._target_level)

    def set_state(self, state: str):
        if state in _STATE_RGB and state != self._state:
            self._state = state
            self._restyle_satellites()

    def set_partial(self, text: str):
        # Live interim text while you're still speaking (dim, no fade)
        self._caption_heard = text
        self._caption_reply = ""
        self._caption_age = 0

    def set_heard(self, text: str):
        self._caption_heard = text
        self._caption_reply = ""
        self._caption_age = 0
        self._reveal = 0

    def set_reply(self, text: str):
        self._caption_reply = text
        self._caption_age = 0
        self._reveal = 0

    # ── Animation ────────────────────────────────────────────────────────────
    def _tick(self):
        self._level += (self._target_level - self._level) * 0.25
        self._target_level *= 0.9
        self._phase += 0.16 if self._state in ("transcribing", "thinking") else 0.05
        self._caption_age += 1
        self._reveal += 3          # typewriter: ~90 chars/sec
        self.update()

    def _caption_alpha(self) -> float:
        """1.0 while held, then linear fade to 0; stays 0 afterwards."""
        if self._caption_age <= _HOLD_FRAMES:
            return 1.0
        gone = self._caption_age - _HOLD_FRAMES
        return max(0.0, 1.0 - gone / _FADE_FRAMES)

    # ── Painting ─────────────────────────────────────────────────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QPointF(_CX, _CY)
        r, g, b = _STATE_RGB.get(self._state, _STATE_RGB["listening"])

        breath = 0.5 + 0.5 * math.sin(self._phase)
        base = 54
        core_r = base * (1.0 + 0.10 * breath + 0.45 * self._level)

        for i in range(6, 0, -1):
            frac = i / 6
            glow_r = core_r * (1.0 + frac * 1.6)
            alpha = int(28 * (1 - frac) * (0.6 + 0.4 * self._level + 0.2 * breath))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(r, g, b, max(0, alpha)))
            p.drawEllipse(center, glow_r, glow_r)

        # Circular waveform
        ring_r = core_r * 1.55
        p.setPen(QPen(QColor(r, g, b, 170), 1.6))
        for i, lvl in enumerate(self._history):
            ang = (i / _BARS) * 2 * math.pi - self._phase
            inner = ring_r
            outer = ring_r + 4 + lvl * 40
            ca, sa = math.cos(ang), math.sin(ang)
            p.drawLine(
                QPointF(_CX + inner * ca, _CY + inner * sa),
                QPointF(_CX + outer * ca, _CY + outer * sa),
            )

        # Rotating reactor arcs (HUD energy rings) — counter-rotating, accent-lit
        lr, lg, lb = min(r + 70, 255), min(g + 70, 255), min(b + 70, 255)
        arcs = [
            (ring_r * 1.34, self._phase * 1.4, 70, 3.0, 200),
            (ring_r * 1.50, -self._phase * 1.0, 110, 2.0, 130),
            (ring_r * 1.50, -self._phase * 1.0 + math.pi, 60, 2.0, 130),
        ]
        for rad, rot, span_deg, wpx, alpha in arcs:
            rect = QRectF(_CX - rad, _CY - rad, rad * 2, rad * 2)
            p.setPen(QPen(QColor(lr, lg, lb, alpha), wpx, cap=Qt.PenCapStyle.RoundCap))
            start16 = int(-math.degrees(rot) * 16)
            p.drawArc(rect, start16, span_deg * 16)

        # Bright energy core — hot cyan-white centre fading into the accent
        grad = QRadialGradient(center, core_r)
        grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        grad.setColorAt(0.22, QColor(225, 240, 255, 245))
        grad.setColorAt(0.55, QColor(lr, lg, lb, 230))
        grad.setColorAt(1.0, QColor(r, g, b, 90))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawEllipse(center, core_r, core_r)

        # Crisp rim highlight
        p.setPen(QPen(QColor(lr, lg, lb, 180), 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(center, core_r, core_r)

        self._paint_caption(p, r, g, b)
        p.end()

    def _paint_caption(self, p: QPainter, r: int, g: int, b: int):
        a = self._caption_alpha()
        if a <= 0:
            return
        if self._caption_heard:
            p.setFont(QFont("Menlo", 11))
            p.setPen(QColor(180, 184, 200, int(220 * a)))
            p.drawText(QPointF(20, 400), self._elide(self._caption_heard, "“", "”", 40))
        if self._caption_reply:
            # Typewriter reveal — text appears as if IU is speaking it
            shown = self._caption_reply[: max(0, self._reveal)]
            f = QFont("Menlo", 12)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor(min(r + 40, 255), min(g + 40, 255), min(b + 40, 255), int(255 * a)))
            p.drawText(QPointF(20, 428), self._elide(shown, "", "", 40))

    def _elide(self, text: str, lq: str, rq: str, limit: int) -> str:
        text = text.strip().replace("\n", " ")
        if len(text) > limit:
            text = text[: limit - 1] + "…"
        return f"{lq}{text}{rq}"

    # ── Drag / hide (ignore clicks on the satellite buttons) ──────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseDoubleClickEvent(self, _e):
        self.hide()
