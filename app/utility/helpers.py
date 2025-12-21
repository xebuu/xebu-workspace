# loading_screen.py
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel

class SpinnerWidget(QWidget):
    def __init__(self, size=72, stroke=6, color="#2D68C4", speed=8, parent=None):
        super().__init__(parent)
        self._size, self._s, self._color, self._angle = size, stroke, QColor(color), 0
        self._timer = QTimer(self, interval=16, timeout=self._tick); self._timer.start()
        self.setFixedSize(size, size); self._speed = speed

    def _tick(self): self._angle = (self._angle + self._speed) % 360; self.update()
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(self._color, self._s); p.setPen(pen)
        r = self.rect().adjusted(self._s, self._s, -self._s, -self._s)
        p.translate(self.rect().center()); p.rotate(self._angle); p.translate(-self.rect().center())
        p.drawArc(r, 0 * 16, 240 * 16)

class LoadingScreen(QWidget):
    def __init__(self, text="Cargando…", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool); self.setAttribute(Qt.WA_TranslucentBackground)
        card = QWidget(self); card.setObjectName("card")
        lay = QVBoxLayout(card); lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(10)
        lay.addWidget(SpinnerWidget(), 0, Qt.AlignCenter)
        lbl = QLabel(text); lbl.setAlignment(Qt.AlignCenter); lay.addWidget(lbl)
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.addWidget(card, 0, Qt.AlignCenter)
        self.setStyleSheet("""
            QWidget#card { background:#1f2022; border:1px solid #2e3b3f; border-radius:14px; }
            QLabel { color:#eaeaea; font-weight:700; }
        """); self.resize(300, 200)
    def showEvent(self, e):
        g = QApplication.primaryScreen().availableGeometry()
        self.move(g.center().x()-self.width()//2, g.center().y()-self.height()//2)
        super().showEvent(e)

def show_loading_then(app: QApplication, build_main, duration_ms=2000, text="Preparando…"):
    """Muestra loader y luego crea/enseña la ventana principal construida por build_main()."""
    loader = LoadingScreen(text); loader.show()
    def open_main():
        main = build_main(); main.show(); loader.close()
    QTimer.singleShot(duration_ms, open_main)
