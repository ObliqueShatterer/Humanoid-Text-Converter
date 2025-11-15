try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets
import sys, os, time, math, random, subprocess

# ----------------------------- Worker for background tasks -----------------------------
class WorkerSignals(QtCore.QObject):
    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal()
    message = QtCore.pyqtSignal(str)

class FakeLongTask(QtCore.QRunnable):
    def __init__(self, duration=5, message_prefix="Working"):
        super().__init__()
        self.duration = duration
        self.signals = WorkerSignals()
        self.message_prefix = message_prefix

    def run(self):
        steps = max(10, int(self.duration * 5))
        for i in range(steps + 1):
            pct = int(i * 100 / steps)
            self.signals.progress.emit(pct)
            if i % (max(1, steps // 5)) == 0:
                self.signals.message.emit(f"{self.message_prefix}... {pct}%")
            time.sleep(self.duration / steps)
        self.signals.message.emit(f"{self.message_prefix} complete.")
        self.signals.finished.emit()


# ----------------------------- Space Background -----------------------------
class SpaceBackground(QtWidgets.QWidget):
    def __init__(self, star_count=145, parent=None):
        super().__init__(parent)
        self.star_count = star_count
        self.stars = []
        for _ in range(star_count):
            x = random.randint(0, 1920)
            y = random.randint(0, 1080)
            base_brightness = random.randint(180, 255)
            phase = random.random() * math.pi * 2
            self.stars.append([x, y, base_brightness, phase])
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(100)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor(0, 0, 0))
        grad = QtGui.QLinearGradient(self.width() * 0.5, 0, self.width(), self.height())
        grad.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QtGui.QColor(100, 0, 160, 40))
        p.fillRect(self.rect(), grad)
        for x, y, base_brightness, phase in self.stars:
            brightness = base_brightness + 50 * math.sin(time.time() * 0.8 + phase)
            brightness = max(100, min(255, int(brightness)))
            p.setPen(QtGui.QColor(brightness, brightness, brightness))
            p.drawPoint(x % self.width(), y % self.height())


# ----------------------------- Glow Button -----------------------------
class GlowButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(70)
        self.setMinimumWidth(300)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setOffset(0, 0)
        self.shadow.setBlurRadius(0)
        self.shadow.setColor(QtGui.QColor(30, 150, 255, 160))
        self.setGraphicsEffect(self.shadow)

        self._scale = 1.0
        self.anim_group = QtCore.QParallelAnimationGroup(self)
        self.blur_anim = QtCore.QPropertyAnimation(self.shadow, b"blurRadius")
        self.scale_anim = QtCore.QPropertyAnimation(self, b"_scale_prop")

        for anim in (self.blur_anim, self.scale_anim):
            anim.setDuration(220)
            anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.anim_group.addAnimation(self.blur_anim)
        self.anim_group.addAnimation(self.scale_anim)

        self.setStyleSheet(self.base_stylesheet())

    def get_scale(self):
        return self._scale

    def set_scale(self, v):
        self._scale = v
        self.setStyleSheet(self.base_stylesheet(scale=v))

    _scale_prop = QtCore.pyqtProperty(float, fget=get_scale, fset=set_scale)

    def enterEvent(self, e):
        self.blur_anim.setStartValue(self.shadow.blurRadius())
        self.blur_anim.setEndValue(36)
        self.scale_anim.setStartValue(self._scale)
        self.scale_anim.setEndValue(1.03)
        self.anim_group.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.blur_anim.setStartValue(self.shadow.blurRadius())
        self.blur_anim.setEndValue(0)
        self.scale_anim.setStartValue(self._scale)
        self.scale_anim.setEndValue(1.0)
        self.anim_group.start()
        super().leaveEvent(e)

    def base_stylesheet(self, scale=1.0):
        base1 = "rgba(10, 40, 90, 220)"
        base2 = "rgba(25, 90, 160, 240)"
        hover1 = "rgba(20, 70, 140, 240)"
        hover2 = "rgba(70, 150, 255, 255)"
        border_normal = "rgba(30,150,255,0.35)"
        border_hover = "rgba(80,200,255,0.70)"
        text_color = "rgb(235,245,255)"

        return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {base1},
                stop:1 {base2});
            border: 2px solid {border_normal};
            border-radius: 18px;
            padding: 10px 18px;
            color: {text_color};
            font-size: 24px;
            font-weight: 600;
            letter-spacing: 0.6px;
            text-align: center;
            transform: scale({scale});
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {hover1},
                stop:1 {hover2});
            border: 2px solid {border_hover};
        }}
        QPushButton:pressed {{
            transform: scale({max(0.98, scale - 0.02)});
        }}
        """


# ----------------------------- AURA Core -----------------------------
class AuraCore(QtWidgets.QLabel):
    DEFAULT_COLOR = QtGui.QColor(100, 220, 255)
    
    def __init__(self, x=None, y=None):
        super().__init__()
        self.orb_size = 320
        self.setFixedSize(520, 520)  # Increased to prevent clipping during expansion
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, False)

        # Store custom position if provided
        self.custom_x = x
        self.custom_y = y

        self._color = self.DEFAULT_COLOR
        self._target_color = self.DEFAULT_COLOR
        self._opacity = 180
        self._scale = 1.0
        self._pulse_scale = 1.0  # Additional scale for pulse reactions
        self.phase = 0.0
        self.speed = 0.04
        self.flow_angle = 0
        self.tilt_angle = -45

        # Color transition animation
        self.color_transition_progress = 1.0
        self.color_start = self._color
        self.color_end = self._color

        self.anim_timer = QtCore.QTimer(self)
        self.anim_timer.timeout.connect(self.animate)
        self.anim_timer.start(30)

        # Active pulse animations tracking
        self.active_animations = []
    
    def set_position(self, x, y):
        """Set absolute position of the orb"""
        self.custom_x = x
        self.custom_y = y
        if self.parent():
            self.move(x, y)

    def animate(self):
        # Orb pulse breathing
        self.phase += self.speed
        self._scale = 1.0 + 0.12 * math.sin(self.phase)
        self._opacity = 130 + 110 * (1 + math.sin(self.phase)) / 2

        # Animate ring color flow gradient
        self.flow_angle = (self.flow_angle + 1.2) % 360

        # Smooth color transition
        if self.color_transition_progress < 1.0:
            self.color_transition_progress = min(1.0, self.color_transition_progress + 0.05)
            t = self.color_transition_progress
            self._color = QtGui.QColor(
                int(self.color_start.red() + (self.color_end.red() - self.color_start.red()) * t),
                int(self.color_start.green() + (self.color_end.green() - self.color_start.green()) * t),
                int(self.color_start.blue() + (self.color_end.blue() - self.color_start.blue()) * t)
            )

        self.update()

    def get_pulse_scale(self):
        return self._pulse_scale

    def set_pulse_scale(self, value):
        self._pulse_scale = value
        self.update()

    pulse_scale = QtCore.pyqtProperty(float, fget=get_pulse_scale, fset=set_pulse_scale)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtCore.Qt.transparent)

        cx = self.width() / 2
        cy = self.height() / 2

        # Combine breathing scale with pulse scale
        combined_scale = self._scale * self._pulse_scale

        # ORB
        orb_size = self.orb_size
        r = orb_size / 2
        ox = cx - r
        oy = cy - r

        p.save()
        p.translate(cx, cy)
        p.scale(combined_scale, combined_scale)
        p.translate(-cx, -cy)

        brightness_factor = 1.0 + ((combined_scale - 1.0) * 2.5)
        brightness_factor = min(1.8, max(0.6, brightness_factor))

        glow_color = QtGui.QColor(
            min(int(self._color.red() * brightness_factor), 255),
            min(int(self._color.green() * brightness_factor), 255),
            min(int(self._color.blue() * brightness_factor), 255)
        )

        grad = QtGui.QRadialGradient(QtCore.QPointF(cx, cy), r)
        c = QtGui.QColor(glow_color)
        c.setAlpha(int(self._opacity))
        grad.setColorAt(0.0, c)
        grad.setColorAt(0.5, QtGui.QColor(c.red(), c.green(), c.blue(), 180))
        grad.setColorAt(0.8, QtGui.QColor(c.red(), c.green(), c.blue(), 80))
        grad.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))

        p.setBrush(grad)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(QtCore.QRectF(ox, oy, orb_size, orb_size))
        p.restore()

        # ANIMATED FLOWING SATURN RING
        ring_w = orb_size * 1.55
        ring_h = orb_size * 0.45

        flow_grad = QtGui.QConicalGradient(cx, cy, self.flow_angle)
        flow_grad.setColorAt(0.00, QtGui.QColor(255, 255, 255, 110))
        flow_grad.setColorAt(0.25, QtGui.QColor(220, 220, 220, 60))
        flow_grad.setColorAt(0.50, QtGui.QColor(255, 255, 255, 180))
        flow_grad.setColorAt(0.75, QtGui.QColor(200, 200, 200, 55))
        flow_grad.setColorAt(1.00, QtGui.QColor(255, 255, 255, 110))

        ellipse_rect = QtCore.QRectF(cx - ring_w / 2, cy - ring_h / 2, ring_w, ring_h)
        outer_path = QtGui.QPainterPath()
        outer_path.addEllipse(ellipse_rect)
        inner_path = QtGui.QPainterPath()
        inner_path.addEllipse(ellipse_rect.adjusted(6, 6, -6, -6))
        ring_path = outer_path.subtracted(inner_path)

        p.save()
        p.translate(cx, cy)
        p.scale(combined_scale, combined_scale)  # Apply same scale to ring
        p.rotate(self.tilt_angle)
        p.translate(-cx, -cy)
        p.setBrush(flow_grad)
        p.setPen(QtCore.Qt.NoPen)
        p.drawPath(ring_path)
        p.restore()

    def pulse_react(self, color: QtGui.QColor):
        """Pulse animation with color change - uses scale instead of geometry"""
        self.color_start = self._color
        self.color_end = color
        self.color_transition_progress = 0.0

        # Use orb_size scaling instead of widget geometry
        anim = QtCore.QPropertyAnimation(self, b"pulse_scale")
        anim.setDuration(600)
        anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim.setStartValue(1.0)
        anim.setEndValue(1.15)
        anim.finished.connect(self.reset_pulse)
        anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
        self.active_animations.append(anim)

    def reset_pulse(self):
        """Reset pulse animation"""
        anim = QtCore.QPropertyAnimation(self, b"pulse_scale")
        anim.setDuration(800)
        anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        anim.setStartValue(self.get_pulse_scale())
        anim.setEndValue(1.0)
        anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
        self.active_animations.append(anim)

    def reset_color(self, delay_ms=2000):
        """Smoothly return to default color after delay"""
        QtCore.QTimer.singleShot(delay_ms, self._start_color_reset)

    def _start_color_reset(self):
        """Internal method to start color reset animation"""
        self.color_start = self._color
        self.color_end = self.DEFAULT_COLOR
        self.color_transition_progress = 0.0


# ----------------------------- Main Window -----------------------------
class AuraMain(QtWidgets.QMainWindow):
    # ====== ORB POSITION CONFIGURATION ======
    # Set these values to customize orb position
    # None = use layout positioning, or set specific x, y coordinates
    ORB_X = 150      # X position (left edge), or None for layout control
    ORB_Y = 200      # Y position (top edge), or None for layout control
    
    # Layout-based positioning (used when ORB_X/ORB_Y are None)
    ORB_USE_LAYOUT = False  # True = use layout, False = absolute positioning
    ORB_LAYOUT_ALIGNMENT = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AURA — Interface")
        self.resize(1024, 600)

        self.background = SpaceBackground()
        self.setCentralWidget(self.background)

        self.overlay = QtWidgets.QWidget(self.background)
        self.overlay.setGeometry(self.background.rect())
        self.overlay.raise_()

        layout = QtWidgets.QVBoxLayout(self.overlay)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        header = self.header_widget()
        layout.addWidget(header, alignment=QtCore.Qt.AlignHCenter)

        content = self.center_controls()
        layout.addWidget(content, alignment=QtCore.Qt.AlignHCenter)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 600;
            color: rgba(150,200,255,0.8);
            letter-spacing: 2px;
            text-shadow: 0 0 25px rgba(100,160,255,0.6);
        """)
        layout.addWidget(self.status_label, alignment=QtCore.Qt.AlignHCenter)

        self.background.installEventFilter(self)
        self.threadpool = QtCore.QThreadPool()
        
        # Track active processes
        self.active_processes = []
        
        self.showMaximized()

    def eventFilter(self, s, e):
        if e.type() == QtCore.QEvent.Resize:
            self.overlay.setGeometry(self.background.rect())
        return super().eventFilter(s, e)

    def header_widget(self):
        w = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(w)

        try:
            from PyQt5.QtGui import QFontDatabase, QFont
            font_path = os.path.join(os.path.dirname(__file__), "Centauri", "Centauri.ttf")
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
                else:
                    font_family = "Segoe UI"
            else:
                font_family = "Segoe UI"
        except:
            font_family = "Segoe UI"

        title = QtWidgets.QLabel("AURA")
        title.setFont(QFont(font_family, 110, QFont.Bold))
        title.setStyleSheet("""
            color: #1C6EDC;
            letter-spacing: 10px;
            text-shadow:
                0 0 18px rgba(140, 200, 255, 0.8),
                0 0 42px rgba(100, 170, 255, 0.65),
                0 0 85px rgba(120, 190, 255, 0.50),
                0 0 160px rgba(170, 220, 255, 0.35),
                0 0 240px rgba(200, 240, 255, 0.25);
        """)
        title.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        h.addWidget(title)
        h.addStretch()
        return w

    def center_controls(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setSpacing(100)
        layout.setContentsMargins(220, 40, 60, 40)

        # Create orb with optional custom position
        self.aura_core = AuraCore(x=self.ORB_X, y=self.ORB_Y)
        
        # Choose positioning method
        if self.ORB_X is not None and self.ORB_Y is not None and not self.ORB_USE_LAYOUT:
            # Absolute positioning - set parent but don't add to layout
            self.aura_core.setParent(self.overlay)
            self.aura_core.move(self.ORB_X, self.ORB_Y)
            self.aura_core.raise_()  # Bring to front
        else:
            # Layout-based positioning
            layout.addWidget(self.aura_core, alignment=self.ORB_LAYOUT_ALIGNMENT)

        btn_col = QtWidgets.QVBoxLayout()
        btn_col.setSpacing(25)
        btn_col.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.btn_start = GlowButton("Identify Me")
        self.btn_train = GlowButton("Register Face")
        self.btn_manage = GlowButton("View Users")
        self.btn_listen = GlowButton("Chat")
        self.btn_exit = GlowButton("Exit")

        for b in [self.btn_start, self.btn_train, self.btn_manage, self.btn_listen]:
            btn_col.addWidget(b)

        self.btn_start.clicked.connect(self.start_recognition)
        self.btn_train.clicked.connect(self.train_data)
        self.btn_manage.clicked.connect(self.manage_dataset)
        self.btn_listen.clicked.connect(self.run_queries)
        self.btn_exit.clicked.connect(self.exit_app)

        # Only add orb to layout if using layout positioning
        if self.ORB_USE_LAYOUT and (self.ORB_X is None or self.ORB_Y is None):
            layout.addWidget(self.aura_core, alignment=self.ORB_LAYOUT_ALIGNMENT)
        
        layout.addSpacing(300)
        layout.addLayout(btn_col, stretch=0)

        # Exit button styling and positioning
        self.btn_exit.setFixedSize(120, 45)
        self.exit_button_default_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(100,0,60,220), stop:1 rgba(200,0,100,255));
                border: 2px solid rgba(255,120,120,0.6);
                border-radius: 14px;
                color: rgb(255,230,230);
                font-size: 22px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(150,0,80,240), stop:1 rgba(255,80,80,255));
            }
        """
        self.btn_exit.setStyleSheet(self.exit_button_default_style)

        exit_container = QtWidgets.QWidget(self.overlay)
        exit_layout = QtWidgets.QHBoxLayout(exit_container)
        exit_layout.setContentsMargins(0, 0, 40, 40)
        exit_layout.addStretch()
        exit_layout.addWidget(self.btn_exit, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        exit_container.setLayout(exit_layout)
        exit_container.setGeometry(0, 0, self.overlay.width(), self.overlay.height())
        exit_container.raise_()

        def overlay_resize(event):
            exit_container.setGeometry(0, 0, self.overlay.width(), self.overlay.height())

        self.overlay.resizeEvent = overlay_resize

        return container

    def start_recognition(self):
        script_path = os.path.join(os.path.dirname(__file__), "recognise.py")
        if not os.path.exists(script_path):
            self.show_error("Error", "recognise.py not found in the app folder.")
            return
        try:
            self.aura_core.pulse_react(QtGui.QColor(38, 103, 255))
            self.status_label.setText("Recognizing...")

            process = subprocess.Popen([sys.executable, script_path])
            self.active_processes.append(process)

            QtCore.QTimer.singleShot(3000, self.clear_status_and_reset_color)

        except Exception as e:
            self.show_error("Error", f"Failed to run recognise.py:\n{e}")

    def train_data(self):
        script_path = os.path.join(os.path.dirname(__file__), "train.py")
        if not os.path.exists(script_path):
            self.show_error("Error", "train.py not found in the app folder.")
            return

        person_name, ok = QtWidgets.QInputDialog.getText(
            self, "Enter Name", "Enter the person's name for training:"
        )
        if ok and person_name.strip():
            try:
                name = person_name.strip()
                self.aura_core.pulse_react(QtGui.QColor(255, 220, 60))
                self.status_label.setText(f"Registering {name}...")

                self.training_process = QtCore.QProcess(self)
                self.training_process.finished.connect(lambda: self.training_done(name))
                self.training_process.start(sys.executable, [script_path, name])

            except Exception as e:
                self.show_error("Error", f"Failed to run train.py:\n{e}")

    def training_done(self, name):
        self.aura_core.pulse_react(QtGui.QColor(80, 255, 120))
        self.status_label.setText(f"{name} registration complete!")
        QtCore.QTimer.singleShot(3000, self.clear_status_and_reset_color)

    def run_queries(self):
        script_path = os.path.join(os.path.dirname(__file__), "queries_api.py")
        if not os.path.exists(script_path):
            self.show_error("Error", f"queries_api.py not found at:\n{script_path}")
            return

        try:
            self.aura_core.pulse_react(QtGui.QColor(0, 255, 255))
            self.status_label.setText("Listening...")

            process = subprocess.Popen([sys.executable, script_path])
            self.active_processes.append(process)

            QtCore.QTimer.singleShot(3000, self.clear_status_and_reset_color)

        except Exception as e:
            self.show_error("Error", f"Failed to run queries_api.py:\n{e}")

    def manage_dataset(self):
        self.status_label.setText("Opening dataset folder...")
        self.aura_core.pulse_react(QtGui.QColor(180, 100, 255))

        data_path = os.path.join(os.path.dirname(__file__), "data")
        if not os.path.exists(data_path):
            os.makedirs(data_path, exist_ok=True)

        try:
            if sys.platform.startswith("win"):
                os.startfile(data_path)
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", data_path])
            else:
                subprocess.Popen(["xdg-open", data_path])
        except Exception as e:
            self.show_error("Error", f"Failed to open folder:\n{e}")

        QtCore.QTimer.singleShot(1500, self.clear_status_and_reset_color)

    def exit_app(self):
        self.status_label.setText("Exiting...")
        self.aura_core.pulse_react(QtGui.QColor(255, 70, 70))
        
        reply = QtWidgets.QMessageBox.question(
            self, "Exit", "Exit AURA Interface?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.cleanup_and_exit()
        else:
            # Restore exit button to default pink color
            self.btn_exit.setStyleSheet(self.exit_button_default_style)
            self.clear_status_and_reset_color()

    def cleanup_and_exit(self):
        """Clean up resources before exiting"""
        for process in self.active_processes:
            try:
                if process.poll() is None:
                    process.terminate()
            except:
                pass
        QtWidgets.QApplication.quit()

    def clear_status_and_reset_color(self):
        """Clear status label and reset orb to default color"""
        self.status_label.clear()
        self.aura_core.reset_color(delay_ms=500)

    def show_error(self, title, message):
        """Show error dialog with proper formatting"""
        QtWidgets.QMessageBox.warning(self, title, message)
        self.aura_core.reset_color(delay_ms=100)

    def closeEvent(self, event):
        """Handle window close event"""
        self.cleanup_and_exit()
        event.accept()


# ----------------------------- Entrypoint -----------------------------
def main():
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    w = AuraMain()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()