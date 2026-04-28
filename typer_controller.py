import evdev
from evdev import ecodes, UInput
import threading
import time

class TyperController:
    def __init__(self, on_press_callback, on_release_callback, hotkey="KEY_LEFTCTRL", mode="hold"):
        self.on_press_callback = on_press_callback
        self.on_release_callback = on_release_callback
        self.threads = []
        self.running = False
        self.trigger_code = getattr(ecodes, hotkey, ecodes.KEY_LEFTCTRL)
        self.mode = mode
        self.is_active = False
        
        capabilities = {ecodes.EV_KEY: ecodes.keys.keys()}
        try:
            self.ui = UInput(capabilities, name="VoiceTyper-Virtual-Keyboard")
            time.sleep(1.0)
        except:
            self.ui = None

    def update_settings(self, hotkey, mode):
        self.trigger_code = getattr(ecodes, hotkey, ecodes.KEY_LEFTCTRL)
        self.mode = mode
        self.is_active = False

    def find_keyboard_devices(self):
        kbd_devices = []
        try:
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            for device in devices:
                capabilities = device.capabilities()
                if ecodes.EV_KEY in capabilities: kbd_devices.append(device)
        except: pass
        return kbd_devices

    def start_listening(self):
        devices = self.find_keyboard_devices()
        if not devices: return
        self.running = True
        for device in devices:
            t = threading.Thread(target=self._listen_loop, args=(device,), daemon=True)
            t.start()
            self.threads.append(t)

    def _listen_loop(self, device):
        try:
            for event in device.read_loop():
                if not self.running: break
                if event.type == ecodes.EV_KEY:
                    if event.code == self.trigger_code:
                        if self.mode == "hold":
                            if event.value == 1: self.on_press_callback()
                            elif event.value == 0: self.on_release_callback()
                        else:
                            if event.value == 1:
                                if not self.is_active:
                                    self.is_active = True
                                    self.on_press_callback()
                                else:
                                    self.is_active = False
                                    self.on_release_callback()
        except: pass

    def type_text(self, text):
        if not text or not self.ui: return
        
        # Focus settle
        time.sleep(0.1)
        
        key_map = {
            ' ': ecodes.KEY_SPACE, '.': ecodes.KEY_DOT, ',': ecodes.KEY_COMMA,
            '!': (ecodes.KEY_1, True), '?': (ecodes.KEY_SLASH, True),
            ':': (ecodes.KEY_SEMICOLON, True), ';': ecodes.KEY_SEMICOLON,
            '"': (ecodes.KEY_APOSTROPHE, True), "'": ecodes.KEY_APOSTROPHE,
            '-': ecodes.KEY_MINUS, '_': (ecodes.KEY_MINUS, True),
            '\n': ecodes.KEY_ENTER, '\t': ecodes.KEY_TAB
        }

        for char in text + " ":
            try:
                is_shift = char.isupper()
                code = None
                if char in key_map:
                    val = key_map[char]
                    if isinstance(val, tuple): code, is_shift = val
                    else: code = val
                else:
                    key_name = 'KEY_' + char.upper()
                    code = getattr(ecodes, key_name, None)
                
                if code:
                    if is_shift: self.ui.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 1)
                    self.ui.write(ecodes.EV_KEY, code, 1)
                    self.ui.write(ecodes.EV_KEY, code, 0)
                    if is_shift: self.ui.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 0)
                    self.ui.syn()
                
                # Tiny sleep for stability
                time.sleep(0.005)
            except: pass
