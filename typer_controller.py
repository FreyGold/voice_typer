import evdev
from evdev import ecodes, UInput
import threading
import time
import subprocess

class TyperController:
    def __init__(self, on_press_callback, on_release_callback, hotkey="KEY_RIGHTALT", mode="hold"):
        self.on_press_callback = on_press_callback
        self.on_release_callback = on_release_callback
        self.threads = []
        self.running = False
        self.trigger_code = getattr(ecodes, hotkey, ecodes.KEY_RIGHTALT)
        self.mode = mode
        self.is_active = False
        
        capabilities = {ecodes.EV_KEY: ecodes.keys.keys()}
        try:
            self.ui = UInput(capabilities, name="VoiceTyper-Virtual-Keyboard")
            time.sleep(1.0)
        except:
            self.ui = None

    def update_settings(self, hotkey, mode):
        self.trigger_code = getattr(ecodes, hotkey, ecodes.KEY_RIGHTALT)
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
        if not text: return
        
        # Settle focus
        time.sleep(0.2)

        # ARABIC & RELIABILITY FIX:
        # Instead of simulating key-by-key, we use the CLIPBOARD method.
        # This works perfectly with Arabic, emojis, and all languages on Wayland.
        
        try:
            # 1. Copy text to clipboard using wl-copy (Wayland) or xclip (X11)
            # We'll try wl-copy first as you are on Pop!_OS Wayland
            copy_proc = subprocess.Popen(['wl-copy'], stdin=subprocess.PIPE)
            copy_proc.communicate(input=(text + " ").encode('utf-8'))
            
            # 2. Trigger Ctrl+V using our virtual keyboard
            if self.ui:
                # Press Ctrl
                self.ui.write(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 1)
                # Press V
                self.ui.write(ecodes.EV_KEY, ecodes.KEY_V, 1)
                self.ui.write(ecodes.EV_KEY, ecodes.KEY_V, 0)
                # Release Ctrl
                self.ui.write(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 0)
                self.ui.syn()
                
        except Exception as e:
            print(f"Typing error: {e}")
            # Fallback for X11 if wl-copy fails
            try:
                copy_proc = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
                copy_proc.communicate(input=(text + " ").encode('utf-8'))
                if self.ui:
                    self.ui.write(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 1)
                    self.ui.write(ecodes.EV_KEY, ecodes.KEY_V, 1)
                    self.ui.write(ecodes.EV_KEY, ecodes.KEY_V, 0)
                    self.ui.write(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 0)
                    self.ui.syn()
            except:
                pass
