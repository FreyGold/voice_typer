import sys
import os
import threading
import time
import json
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLabel, QProgressBar, QTextEdit, QPushButton, QLineEdit, QStackedWidget, QComboBox, QSystemTrayIcon, QMenu, QCheckBox, QGraphicsOpacityEffect, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QPauseAnimation
from PyQt6.QtGui import QIcon, QAction, QColor
from recorder import Recorder
from transcriber import Transcriber
from typer_controller import TyperController

CONFIG_FILE = "config.json"

class WorkerSignals(QObject):
    status = pyqtSignal(str)
    preview = pyqtSignal(str)
    progress = pyqtSignal(int)
    model_loaded = pyqtSignal()
    trigger_press = pyqtSignal()
    trigger_release = pyqtSignal()

class VoiceTyperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Typer")
        self.setFixedSize(300, 320)
        
        # Tool window behavior + Stays on top
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Try to load custom icon
        self.icon_path = os.path.expanduser("~/.local/share/icons/voice-typer.svg")
        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))
        
        self.signals = WorkerSignals()
        self.signals.status.connect(self.update_status)
        self.signals.preview.connect(self.update_preview)
        self.signals.progress.connect(self.update_progress)
        self.signals.model_loaded.connect(self.on_model_ready)
        self.signals.trigger_press.connect(self.start_recording_ui)
        self.signals.trigger_release.connect(self.stop_recording_ui)
        
        self.recorder = Recorder()
        self.transcriber = None
        self.config = self.load_config()
        
        self.typer = TyperController(
            on_press_callback=lambda: self.signals.trigger_press.emit(), 
            on_release_callback=lambda: self.signals.trigger_release.emit(),
            hotkey=self.config.get("hotkey", "KEY_RIGHTALT"),
            mode=self.config.get("trigger_mode", "hold")
        )
        
        self.is_recording = False
        self.is_loading_model = False
        self.setup_ui()
        self.setup_tray()
        self.typer.start_listening()

    def load_config(self):
        defaults = {"mode": None, "api_key": "", "hotkey": "KEY_RIGHTALT", "trigger_mode": "hold", "language": "auto", "refine": True}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                try: 
                    d = json.load(f)
                    defaults.update(d)
                except: pass
        return defaults

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def setup_ui(self):
        self.main_container = QWidget()
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1b26; border-radius: 12px; }
            QWidget#main_container { background-color: #1a1b26; }
            QLabel { color: #a9b1d6; font-family: 'Inter', 'Segoe UI', sans-serif; font-size: 11px; }
            QPushButton { background-color: #24283b; color: #c0caf5; border: 1px solid #414868; border-radius: 6px; padding: 6px 12px; font-weight: 500; }
            QPushButton:hover { background-color: #3d59a1; border-color: #7aa2f7; }
            QLineEdit, QComboBox, QTextEdit { background-color: #16161e; color: #c0caf5; border: 1px solid #414868; border-radius: 6px; padding: 6px; }
            QProgressBar { border: none; background-color: #24283b; border-radius: 3px; }
            QProgressBar::chunk { background-color: #7aa2f7; border-radius: 3px; }
            QCheckBox { color: #a9b1d6; font-size: 10px; spacing: 8px; }
        """)
        self.main_container.setObjectName("main_container")
        self.setCentralWidget(self.main_container)
        layout = QVBoxLayout(self.main_container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        self.init_selection_screen()
        self.init_main_screen()
        
        if self.config["mode"]: 
            self.start_app_with_mode(self.config["mode"], self.config["api_key"])
        else: 
            self.stack.setCurrentIndex(0)

    def init_selection_screen(self):
        page = QWidget(); layout = QVBoxLayout(page)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(12)
        
        title = QLabel("CONFIGURATION"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight:bold; color:#7aa2f7; font-size:13px; letter-spacing: 1px; margin-bottom: 5px;")
        layout.addWidget(title)
        
        row1 = QHBoxLayout(); row1.setSpacing(10)
        self.combo_key = QComboBox()
        self.combo_key.addItems(["KEY_RIGHTALT", "KEY_LEFTCTRL", "KEY_RIGHTCTRL", "KEY_SPACE", "KEY_CAPSLOCK", "KEY_F10"])
        self.combo_key.setCurrentText(self.config["hotkey"])
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["hold", "toggle"])
        self.combo_mode.setCurrentText(self.config["trigger_mode"])
        row1.addWidget(self.combo_key, 2); row1.addWidget(self.combo_mode, 1); layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        self.combo_lang = QComboBox(); self.combo_lang.addItems(["auto", "en", "ar", "fr", "es"]); self.combo_lang.setCurrentText(self.config["language"])
        row2.addWidget(QLabel("Language:"), 1); row2.addWidget(self.combo_lang, 2); layout.addLayout(row2)
        
        self.check_refine = QCheckBox("Smart Punctuation (Cloud only)"); self.check_refine.setChecked(self.config["refine"]); layout.addWidget(self.check_refine)
        
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setFrameShadow(QFrame.Shadow.Plain); line.setStyleSheet("color: #24283b;"); layout.addWidget(line)
        
        self.api_input = QLineEdit(); self.api_input.setPlaceholderText("Groq API Key..."); self.api_input.setEchoMode(QLineEdit.EchoMode.Password); self.api_input.setText(self.config["api_key"]); layout.addWidget(self.api_input)

        btn_apply = QPushButton("SAVE SETTINGS"); btn_apply.setStyleSheet("background-color: #3d59a1; color: white; font-weight: bold; padding: 8px;"); btn_apply.clicked.connect(self.apply_changes); layout.addWidget(btn_apply)

        mode_layout = QHBoxLayout(); mode_layout.setSpacing(10)
        btn_local = QPushButton("USE LOCAL"); btn_local.clicked.connect(lambda: self.start_app_with_mode("local"))
        btn_cloud = QPushButton("USE CLOUD"); btn_cloud.clicked.connect(lambda: self.start_app_with_mode("cloud", self.api_input.text()))
        mode_layout.addWidget(btn_local); mode_layout.addWidget(btn_cloud); layout.addLayout(mode_layout)
        
        self.stack.addWidget(page)

    def init_main_screen(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(15)
        self.label_status = QLabel("READY"); self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter); self.label_status.setStyleSheet("font-size: 22px; font-weight: 900; color: #9ece6a; margin-top: 10px"); layout.addWidget(self.label_status)
        self.progressbar = QProgressBar(); self.progressbar.setFixedHeight(6); self.progressbar.setTextVisible(False); layout.addWidget(self.progressbar)
        self.text_preview = QTextEdit(); self.text_preview.setReadOnly(True); self.text_preview.setPlaceholderText("Transcription will appear here..."); self.text_preview.setStyleSheet("background-color: #16161e; color: #c0caf5; border: 1px solid #24283b; border-radius: 8px; font-size: 11px; padding: 10px;"); layout.addWidget(self.text_preview)
        footer = QHBoxLayout(); self.label_hint = QLabel(""); self.label_hint.setStyleSheet("font-size: 9px; color: #565f89; font-weight: 500;"); footer.addWidget(self.label_hint, 1)
        btn_play = QPushButton("▶"); btn_play.setFixedSize(30, 24); btn_play.clicked.connect(self.recorder.play_last); footer.addWidget(btn_play)
        btn_set = QPushButton("⚙"); btn_set.setFixedSize(30, 24); btn_set.clicked.connect(self.reset_mode); footer.addWidget(btn_set)
        layout.addLayout(footer); self.stack.addWidget(page)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        if os.path.exists(self.icon_path): self.tray.setIcon(QIcon(self.icon_path))
        else: from PyQt6.QtWidgets import QStyle; self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DriveHDIcon))
        menu = QMenu(); show_act = QAction("Show", self); show_act.triggered.connect(self.show); quit_act = QAction("Quit", self); quit_act.triggered.connect(QApplication.instance().quit); menu.addActions([show_act, quit_act]); self.tray.setContextMenu(menu); self.tray.show()

    def apply_changes(self):
        self.config.update({"api_key": self.api_input.text(), "hotkey": self.combo_key.currentText(), "trigger_mode": self.combo_mode.currentText(), "language": self.combo_lang.currentText(), "refine": self.check_refine.isChecked()})
        self.save_config(); self.typer.update_settings(self.config["hotkey"], self.config["trigger_mode"])
        if self.transcriber: self.on_model_ready(); self.fade_to_page(1)
        else: self.start_app_with_mode(self.config.get("mode", "local"), self.config["api_key"])

    def fade_to_page(self, index):
        if self.stack.currentIndex() == index: return
        
        # Adjust focus flags before transition
        if index == 0: # Settings
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowDoesNotAcceptFocus)
        else: # Main
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.show()
        
        current_page = self.stack.currentWidget(); next_page = self.stack.widget(index)
        if hasattr(self, "fade_anim"): self.fade_anim.stop()
        if hasattr(self, "fade_anim2"): self.fade_anim2.stop()
        eff = QGraphicsOpacityEffect(current_page); current_page.setGraphicsEffect(eff); self.fade_anim = QPropertyAnimation(eff, b"opacity"); self.fade_anim.setDuration(150); self.fade_anim.setStartValue(1.0); self.fade_anim.setEndValue(0.0)
        def on_fade_out():
            current_page.setGraphicsEffect(None); self.stack.setCurrentIndex(index)
            eff2 = QGraphicsOpacityEffect(next_page); next_page.setGraphicsEffect(eff2); self.fade_anim2 = QPropertyAnimation(eff2, b"opacity"); self.fade_anim2.setDuration(150); self.fade_anim2.setStartValue(0.0); self.fade_anim2.setEndValue(1.0); self.fade_anim2.finished.connect(lambda: next_page.setGraphicsEffect(None)); self.fade_anim2.start()
        self.fade_anim.finished.connect(on_fade_out); self.fade_anim.start()

    def start_app_with_mode(self, mode, api_key=""):
        self.config.update({"mode": mode, "api_key": api_key, "hotkey": self.combo_key.currentText(), "trigger_mode": self.combo_mode.currentText(), "language": self.combo_lang.currentText(), "refine": self.check_refine.isChecked()})
        self.save_config(); self.typer.update_settings(self.config["hotkey"], self.config["trigger_mode"]); self.fade_to_page(1); self.update_status("LOADING"); self.update_progress(-1)
        threading.Thread(target=self.load_transcriber, args=(mode, api_key), daemon=True).start()

    def reset_mode(self): self.fade_to_page(0)
    def load_transcriber(self, mode, api_key):
        try: self.transcriber = Transcriber(mode=mode, api_key=api_key); self.signals.model_loaded.emit()
        except: self.signals.status.emit("ERROR")
    def on_model_ready(self):
        self.is_loading_model = False; self.update_status("READY")
        self.label_hint.setText(f"{self.config['trigger_mode'].upper()} {self.config['hotkey'].replace('KEY_', '')} ({self.config['language'].upper()})")
        self.update_progress(0)
    
    def update_status(self, text): 
        if self.label_status.text() == text and text != "RECORDING": return
        self.label_status.setText(text)
        if text == "RECORDING": self.label_status.setStyleSheet("font-size: 22px; font-weight: 900; color: #f7768e; margin-top: 10px"); self.progressbar.setStyleSheet("QProgressBar::chunk { background-color: #f7768e; }"); self.start_pulse()
        elif text == "WORKING": self.label_status.setStyleSheet("font-size: 22px; font-weight: 900; color: #e0af68; margin-top: 10px"); self.progressbar.setStyleSheet("QProgressBar::chunk { background-color: #e0af68; }"); self.stop_pulse()
        elif text == "READY": self.label_status.setStyleSheet("font-size: 22px; font-weight: 900; color: #9ece6a; margin-top: 10px"); self.progressbar.setStyleSheet("QProgressBar::chunk { background-color: #7aa2f7; }"); self.stop_pulse()
        elif text == "ERROR": self.label_status.setStyleSheet("font-size: 22px; font-weight: 900; color: #db4b4b; margin-top: 10px"); self.stop_pulse()
        elif text == "LOADING": self.label_status.setStyleSheet("font-size: 22px; font-weight: 900; color: #7aa2f7; margin-top: 10px"); self.stop_pulse()

    def update_preview(self, text): self.text_preview.setText(text)
    def update_progress(self, v):
        if v == -1: self.progressbar.setRange(0, 0)
        else: self.progressbar.setRange(0, 100); self.progressbar.setValue(v)
    def start_pulse(self):
        if hasattr(self, "pulse_anim"): self.pulse_anim.stop()
        eff = QGraphicsOpacityEffect(self.label_status); self.label_status.setGraphicsEffect(eff); self.pulse_anim = QSequentialAnimationGroup()
        a1 = QPropertyAnimation(eff, b"opacity"); a1.setDuration(800); a1.setStartValue(1.0); a1.setEndValue(0.3); a1.setEasingCurve(QEasingCurve.Type.InOutQuad)
        a2 = QPropertyAnimation(eff, b"opacity"); a2.setDuration(800); a2.setStartValue(0.3); a2.setEndValue(1.0); a2.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.pulse_anim.addAnimation(a1); self.pulse_anim.addAnimation(a2); self.pulse_anim.setLoopCount(-1); self.pulse_anim.start()
    def stop_pulse(self):
        if hasattr(self, "pulse_anim"): self.pulse_anim.stop()
        self.label_status.setGraphicsEffect(None)

    def start_recording_ui(self):
        if self.is_loading_model or not self.transcriber: return
        if not self.is_recording: self.is_recording = True; self.recording_start_time = time.time(); self.update_status("RECORDING"); self.recorder.start(); self.update_progress(-1)
    def stop_recording_ui(self):
        if self.is_recording:
            self.is_recording = False
            duration = time.time() - self.recording_start_time
            if duration < 0.6: self.recorder.stop(); self.update_status("READY"); self.update_progress(0); return
            self.update_status("WORKING"); self.update_progress(100); threading.Thread(target=self.process_audio, daemon=True).start()
    def process_audio(self):
        try:
            audio_file = self.recorder.stop()
            if audio_file and os.path.exists(audio_file):
                text = self.transcriber.transcribe(audio_file, language=self.config["language"], refine=self.config["refine"])
                if text.strip(): self.signals.preview.emit(text); self.typer.type_text(text)
        except Exception as e: print(f"Process Audio Error: {e}"); self.signals.status.emit("ERROR")
        self.signals.status.emit("READY"); self.signals.progress.emit(0)

if __name__ == "__main__":
    import socket
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.bind(("127.0.0.1", 47474))
    except socket.error:
        print("Another instance of Voice Typer is already running. Please close it from the system tray first.")
        sys.exit(0)

    app = QApplication(sys.argv); app.setApplicationName("Voice Typer"); app.setDesktopFileName("voice-typer")
    icon_path = os.path.expanduser("~/.local/share/icons/voice-typer.svg")
    if os.path.exists(icon_path): app.setWindowIcon(QIcon(icon_path))
    window = VoiceTyperApp(); window.show(); sys.exit(app.exec())
