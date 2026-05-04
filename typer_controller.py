import time
import threading
import sys
import pyperclip

# Conditional imports for cross-platform support
try:
    if sys.platform.startswith('linux'):
        import evdev
        from evdev import ecodes
    else:
        evdev = None
except ImportError:
    evdev = None

try:
    from pynput import keyboard
    from pynput.keyboard import Key, Controller
except ImportError:
    keyboard = None

class TyperController:
    def __init__(self, on_press_callback, on_release_callback, hotkey="KEY_RIGHTALT", mode="hold"):
        self.on_press_callback = on_press_callback
        self.on_release_callback = on_release_callback
        self.mode = mode
        self.is_active = False
        self.hotkey_str = hotkey
        
        # Keyboard controller for typing (pynput is good for this everywhere)
        self.controller = Controller() if keyboard else None
        
        # State for listener
        self.running = False
        self.threads = []
        
        # Map keys for different platforms
        self._setup_platform_mapping()

    def _setup_platform_mapping(self):
        if sys.platform.startswith('linux') and evdev:
            # Linux (evdev for reliable global hotkeys on Wayland/X11)
            self.trigger_code = getattr(ecodes, self.hotkey_str, ecodes.KEY_RIGHTALT)
            self.use_evdev = True
        else:
            # Windows/Mac (pynput)
            mapping = {
                "KEY_RIGHTALT": [Key.alt_gr, Key.alt_r],
                "KEY_LEFTCTRL": [Key.ctrl_l],
                "KEY_RIGHTCTRL": [Key.ctrl_r],
                "KEY_SPACE": [Key.space],
                "KEY_CAPSLOCK": [Key.caps_lock],
                "KEY_F10": [Key.f10]
            }
            self.target_keys = mapping.get(self.hotkey_str, [Key.alt_gr])
            self.use_evdev = False

    def update_settings(self, hotkey, mode):
        self.hotkey_str = hotkey
        self.mode = mode
        self.is_active = False
        self._setup_platform_mapping()
        
        if self.running:
            self.stop_listening()
            self.start_listening()

    def start_listening(self):
        self.running = True
        if self.use_evdev:
            self._start_evdev_listening()
        else:
            self._start_pynput_listening()

    def stop_listening(self):
        self.running = False
        if hasattr(self, 'pynput_listener') and self.pynput_listener:
            self.pynput_listener.stop()
            self.pynput_listener = None
        
        # Evdev threads will exit on self.running = False
        self.threads = []

    # --- Linux (evdev) Implementation ---
    def _start_evdev_listening(self):
        kbd_devices = []
        try:
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            for device in devices:
                if ecodes.EV_KEY in device.capabilities():
                    kbd_devices.append(device)
        except: pass
        
        if not kbd_devices:
            print("No keyboard devices found for evdev. Falling back to pynput.")
            self.use_evdev = False
            self._start_pynput_listening()
            return

        for device in kbd_devices:
            t = threading.Thread(target=self._evdev_loop, args=(device,), daemon=True)
            t.start()
            self.threads.append(t)

    def _evdev_loop(self, device):
        try:
            for event in device.read_loop():
                if not self.running: break
                if event.type == ecodes.EV_KEY and event.code == self.trigger_code:
                    if event.value == 1: # Press
                        if self.mode == "hold":
                            if not self.is_active:
                                self.is_active = True
                                self.on_press_callback()
                        else: # toggle
                            if not self.is_active:
                                self.is_active = True
                                self.on_press_callback()
                            else:
                                self.is_active = False
                                self.on_release_callback()
                    elif event.value == 0: # Release
                        if self.mode == "hold" and self.is_active:
                            self.is_active = False
                            self.on_release_callback()
        except: pass

    # --- Windows/Mac (pynput) Implementation ---
    def _start_pynput_listening(self):
        if not keyboard: return
        self.pynput_listener = keyboard.Listener(
            on_press=self._on_pynput_press, 
            on_release=self._on_pynput_release
        )
        self.pynput_listener.start()

    def _on_pynput_press(self, key):
        if key in self.target_keys:
            if self.mode == "hold":
                if not self.is_active:
                    self.is_active = True
                    self.on_press_callback()
            else: # toggle
                if not self.is_active:
                    self.is_active = True
                    self.on_press_callback()
                else:
                    self.is_active = False
                    self.on_release_callback()

    def _on_pynput_release(self, key):
        if key in self.target_keys:
            if self.mode == "hold" and self.is_active:
                self.is_active = False
                self.on_release_callback()

    # --- Typing Implementation (Cross-platform bridge) ---
    def type_text(self, text):
        if not text: return
        time.sleep(0.2)
        try:
            pyperclip.copy(text + " ")
            modifier = Key.cmd if sys.platform == 'darwin' else Key.ctrl
            with self.controller.pressed(modifier):
                self.controller.press('v')
                self.controller.release('v')
        except Exception as e:
            print(f"Typing error: {e}")
