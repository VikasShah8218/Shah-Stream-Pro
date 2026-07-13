"""Crisp monochrome transport icons drawn with QPainter (no emoji, no asset files).

Each factory returns a :class:`QIcon` rendered at 2x for high-DPI sharpness in a
single, theme-controllable colour. Requires a running QGuiApplication (QPixmap).
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

# Icons are designed in a 40x40 space (art roughly inside x/y 12..28) and shown
# downscaled, which keeps edges crisp on both standard and high-DPI displays.
_RENDER = 40
_STROKE = 2.6


def _icon(draw, color: str) -> QIcon:
    pixmap = QPixmap(_RENDER, _RENDER)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    draw(painter, QColor(color))
    painter.end()
    return QIcon(pixmap)


def _stroke_pen(color: QColor) -> QPen:
    pen = QPen(color, _STROKE)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _fill(painter: QPainter, color: QColor) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)


def _draw_play(p: QPainter, c: QColor) -> None:
    _fill(p, c)
    p.drawPolygon(QPolygonF([QPointF(15, 12), QPointF(15, 28), QPointF(30, 20)]))


def _draw_pause(p: QPainter, c: QColor) -> None:
    _fill(p, c)
    p.drawRoundedRect(QRectF(14, 12, 4.6, 16), 1.8, 1.8)
    p.drawRoundedRect(QRectF(21.4, 12, 4.6, 16), 1.8, 1.8)


def _draw_stop(p: QPainter, c: QColor) -> None:
    _fill(p, c)
    p.drawRoundedRect(QRectF(13, 13, 14, 14), 2.6, 2.6)


def _draw_open(p: QPainter, c: QColor) -> None:
    _fill(p, c)
    p.drawRoundedRect(QRectF(11, 13.5, 9, 4.5), 1.6, 1.6)  # tab
    p.drawRoundedRect(QRectF(10.5, 16.5, 19, 12.5), 2.4, 2.4)  # body


def _speaker(p: QPainter, c: QColor) -> None:
    _fill(p, c)
    p.drawRect(QRectF(10.5, 16.5, 4, 7))  # driver
    p.drawPolygon(
        QPolygonF(
            [QPointF(14.5, 16.5), QPointF(20, 12), QPointF(20, 28), QPointF(14.5, 23.5)]
        )
    )


def _draw_volume(p: QPainter, c: QColor) -> None:
    _speaker(p, c)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_stroke_pen(c))
    p.drawArc(QRectF(16, 15, 10, 10), int(-58 * 16), int(116 * 16))
    p.drawArc(QRectF(13, 11, 17, 18), int(-52 * 16), int(104 * 16))


def _draw_mute(p: QPainter, c: QColor) -> None:
    _speaker(p, c)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_stroke_pen(c))
    p.drawLine(QPointF(24, 16), QPointF(30, 24))
    p.drawLine(QPointF(30, 16), QPointF(24, 24))


def _draw_fullscreen(p: QPainter, c: QColor) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_stroke_pen(c))
    # Four corner brackets.
    p.drawPolyline(QPolygonF([QPointF(13, 17), QPointF(13, 13), QPointF(17, 13)]))
    p.drawPolyline(QPolygonF([QPointF(23, 13), QPointF(27, 13), QPointF(27, 17)]))
    p.drawPolyline(QPolygonF([QPointF(13, 23), QPointF(13, 27), QPointF(17, 27)]))
    p.drawPolyline(QPolygonF([QPointF(27, 23), QPointF(27, 27), QPointF(23, 27)]))


def play_icon(color: str) -> QIcon:
    return _icon(_draw_play, color)


def pause_icon(color: str) -> QIcon:
    return _icon(_draw_pause, color)


def stop_icon(color: str) -> QIcon:
    return _icon(_draw_stop, color)


def open_icon(color: str) -> QIcon:
    return _icon(_draw_open, color)


def volume_icon(color: str) -> QIcon:
    return _icon(_draw_volume, color)


def mute_icon(color: str) -> QIcon:
    return _icon(_draw_mute, color)


def fullscreen_icon(color: str) -> QIcon:
    return _icon(_draw_fullscreen, color)
