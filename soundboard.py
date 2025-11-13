import os
import json
import shutil
import random
import uuid
import pygame
import keyboard
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter.ttk import Treeview

CONFIG_FILE = "soundboard_config.json"
SOUNDS_FOLDER = "sounds"


class SoundboardApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Python Soundboard 🎵 (Random Variations)")
        self.master.geometry("800x500")
        self.master.resizable(False, False)

        try:
            pygame.mixer.quit()
        except Exception:
            pass
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        print("Pygame mixer initialized:", pygame.mixer.get_init())

        self.sounds = {}

        self.hotkey_handles = {}

        if not os.path.exists(SOUNDS_FOLDER):
            os.makedirs(SOUNDS_FOLDER)

        self.tree = Treeview(master, columns=("Name", "Key", "Volume", "Files"), show="headings", height=15)
        self.tree.heading("Name", text="Name")
        self.tree.heading("Key", text="Hotkey")
        self.tree.heading("Volume", text="Volume %")
        self.tree.heading("Files", text="Variation Count")

        self.tree.column("Name", width=150)
        self.tree.column("Key", width=100)
        self.tree.column("Volume", width=80)
        self.tree.column("Files", width=450)

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(master)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Add Sound", command=self.add_sound, width=12).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Add Variations", command=self.add_variations, width=12).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Remove Selected", command=self.remove_sound, width=12).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Edit Volume", command=self.edit_volume, width=12).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="Edit Keybind", command=self.edit_keybind, width=12).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(btn_frame, text="Save Config", command=self.save_config, width=12).grid(row=2, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="Load Config", command=self.load_config, width=12).grid(row=2, column=1, padx=5, pady=5)

        if os.path.exists(CONFIG_FILE):
            self.load_config()

    def _sanitize_folder_name(self, name):
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()

    def _generate_sound_id(self, base_name):
        return f"{self._sanitize_folder_name(base_name)}_{uuid.uuid4().hex[:8]}"

    def _safe_remove_hotkey_by_key(self, key):
        """Remove hotkey using the stored handler if possible."""
        if not key:
            return
        handle = self.hotkey_handles.pop(key, None)
        try:
            if handle is not None:
                keyboard.remove_hotkey(handle)
            else:
                keyboard.remove_hotkey(key)
        except Exception:
            pass

    def add_sound(self):
        """Add a new sound with one or more audio file variations"""
        filepaths = filedialog.askopenfilenames(title="Select Sound File(s) (variations)",
                                                filetypes=[("Audio Files", "*.wav *.mp3 *.ogg")])
        if not filepaths:
            return

        name = simpledialog.askstring("Sound Name", "Enter a name for this sound:")
        if not name:
            messagebox.showwarning("Invalid Name", "Sound name cannot be empty.")
            return

        key = simpledialog.askstring("Hotkey", "Enter a hotkey (example: F1, a, ctrl+shift+1):")
        if not key:
            messagebox.showwarning("Invalid Key", "Hotkey cannot be empty.")
            return

        key = key.lower().strip()

        folder_name = self._sanitize_folder_name(name)
        sound_folder = os.path.join(SOUNDS_FOLDER, folder_name)
        counter = 1
        original_folder = sound_folder
        while os.path.exists(sound_folder):
            sound_folder = f"{original_folder}_{counter}"
            counter += 1
        os.makedirs(sound_folder)

        copied_files = []
        for filepath in filepaths:
            filename = os.path.basename(filepath)
            dest_path = os.path.join(sound_folder, filename)

            counter = 1
            while os.path.exists(dest_path):
                name_part, ext = os.path.splitext(filename)
                dest_path = os.path.join(sound_folder, f"{name_part}_{counter}{ext}")
                counter += 1

            shutil.copy2(filepath, dest_path)
            copied_files.append(dest_path)

        sound_id = self._generate_sound_id(name)
        sound_entry = {
            "name": name,
            "folder": sound_folder,
            "files": copied_files,
            "volume": 1.0,
            "key": "(unbound)"
        }

        bound = False
        try:
            if key in self.hotkey_handles:
                messagebox.showwarning("Key in Use", f"Hotkey '{key}' is already assigned. This sound will be unbound.")
            else:
                handle = keyboard.add_hotkey(key, self.play_sound, args=(sound_id,))
                self.hotkey_handles[key] = handle
                sound_entry["key"] = key
                bound = True
        except Exception as e:
            print(f"Could not bind hotkey '{key}': {e}")
            messagebox.showwarning("Hotkey Error", f"Could not bind hotkey '{key}'. Sound was added but unbound.")

        self.sounds[sound_id] = sound_entry
        display_key = sound_entry["key"]
        self.tree.insert("", "end", iid=sound_id,
                         values=(name, display_key, int(sound_entry["volume"] * 100), f"{len(copied_files)} variation(s)"))

        if bound:
            messagebox.showinfo("Hotkey Assigned",
                                f"{name} is now bound to [{display_key.upper()}]\n{len(copied_files)} variation(s) added")
        else:
            messagebox.showinfo("Sound Added", f"{name} added without a keybind.\nYou can edit the keybind later.")

    def add_variations(self):
        """Add more audio file variations to an existing sound"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a sound to add variations to.")
            return

        item = selected[0]
        if item not in self.sounds:
            messagebox.showerror("Error", "Selected item not found in internal data.")
            return

        filepaths = filedialog.askopenfilenames(title="Select Additional Sound File(s)",
                                                filetypes=[("Audio Files", "*.wav *.mp3 *.ogg")])
        if not filepaths:
            return

        sound_data = self.sounds[item]
        sound_folder = sound_data["folder"]

        for filepath in filepaths:
            filename = os.path.basename(filepath)
            dest_path = os.path.join(sound_folder, filename)

            counter = 1
            while os.path.exists(dest_path):
                name_part, ext = os.path.splitext(filename)
                dest_path = os.path.join(sound_folder, f"{name_part}_{counter}{ext}")
                counter += 1

            shutil.copy2(filepath, dest_path)
            sound_data["files"].append(dest_path)

        self.update_tree_item(item)
        messagebox.showinfo("Variations Added",
                            f"Added {len(filepaths)} variation(s)\nTotal: {len(sound_data['files'])}")

    def play_sound(self, sound_id):
        """Play a random variation of the sound. This can be called from a keyboard callback thread."""
        sound_data = self.sounds.get(sound_id)
        if not sound_data or not sound_data.get("files"):
            return

        sound_file = random.choice(sound_data["files"])

        try:
            if not os.path.exists(sound_file):
                print(f"Error: Sound file not found: {sound_file}")
                return

            file_ext = os.path.splitext(sound_file)[1].lower()
            if file_ext == '.mp3':
                pygame.mixer.music.load(sound_file)
                pygame.mixer.music.set_volume(sound_data["volume"])
                pygame.mixer.music.play()
            else:
                sound = pygame.mixer.Sound(sound_file)
                sound.set_volume(sound_data["volume"])
                sound.play()

            filename = os.path.basename(sound_file)
            print(f"▶ Playing: {sound_data['name']} ({filename}) at volume {int(sound_data['volume']*100)}%")
        except Exception as e:
            print(f"Error playing sound '{sound_data.get('name', sound_id)}': {e}")

            def _show_err():
                messagebox.showerror("Playback Error", f"Could not play {sound_data.get('name', sound_id)}: {e}")
            try:
                self.master.after(0, _show_err)
            except Exception:
                pass

    def remove_sound(self):
        """Remove selected sound(s) and delete their folders"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a sound to remove.")
            return

        confirm = messagebox.askyesno("Confirm Removal",
                                     "Remove selected sound(s)? This will delete the entire folder and all variations.")
        if not confirm:
            return

        for item in list(selected):
            if item not in self.sounds:
                try:
                    self.tree.delete(item)
                except Exception:
                    pass
                continue

            sound_entry = self.sounds[item]
            key = sound_entry.get("key")
            try:
                folder_path = sound_entry.get("folder")
                if folder_path and os.path.exists(folder_path):
                    shutil.rmtree(folder_path)
                    print(f"Deleted folder: {folder_path}")
            except Exception as e:
                print(f"Could not delete folder: {e}")

            try:
                if key and key != "(unbound)":
                    self._safe_remove_hotkey_by_key(key)
            except Exception:
                pass

            try:
                del self.sounds[item]
            except Exception:
                pass
            try:
                self.tree.delete(item)
            except Exception:
                pass

    def save_config(self):
        """Save the soundboard configuration"""
        try:
            to_save = []
            for sid, data in self.sounds.items():
                to_save.append({
                    "name": data.get("name"),
                    "folder": data.get("folder"),
                    "files": data.get("files"),
                    "volume": data.get("volume"),
                    "key": data.get("key") if data.get("key") != "(unbound)" else None
                })
            with open(CONFIG_FILE, "w") as f:
                json.dump(to_save, f, indent=4)
            messagebox.showinfo("Saved", "Soundboard configuration saved!")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save configuration: {e}")

    def load_config(self):
        """Load the soundboard configuration"""
        if not os.path.exists(CONFIG_FILE):
            messagebox.showwarning("No Config", "No saved soundboard configuration found.")
            return

        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not read config file: {e}")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        for k in list(self.hotkey_handles.keys()):
            try:
                self._safe_remove_hotkey_by_key(k)
            except Exception:
                pass
        self.hotkey_handles.clear()
        self.sounds.clear()

        failed_keys = []

        for entry in loaded:
            name = entry.get("name", "Unnamed")
            folder = entry.get("folder")
            files = entry.get("files", []) or []
            volume = float(entry.get("volume", 1.0))
            key = entry.get("key")
            if key:
                key = key.lower().strip()

            sound_id = self._generate_sound_id(name)
            sound_entry = {
                "name": name,
                "folder": folder,
                "files": files,
                "volume": volume,
                "key": "(unbound)"
            }

            if key:
                try:
                    handle = keyboard.add_hotkey(key, self.play_sound, args=(sound_id,))
                    self.hotkey_handles[key] = handle
                    sound_entry["key"] = key
                except Exception as e:
                    print(f"Could not bind hotkey '{key}' for '{name}': {e}")
                    failed_keys.append(f"{name} ({key})")
                    sound_entry["key"] = "(unbound)"

            self.sounds[sound_id] = sound_entry
            display_key = sound_entry["key"]
            self.tree.insert("", "end", iid=sound_id,
                             values=(name, display_key, int(volume * 100), f"{len(files)} variation(s)"))

        success_msg = f"Loaded {len(self.sounds)} sound(s)!"
        if failed_keys:
            success_msg += f"\n\nFailed to load {len(failed_keys)} keybind(s):\n" + "\n".join(failed_keys)
            success_msg += "\n\nThese sounds were loaded but unbound. Please check the keybinds."

        messagebox.showinfo("Loaded", success_msg)

    def update_tree_item(self, sound_id):
        """Update a tree item with current sound data"""
        if sound_id not in self.sounds:
            return
        sound_data = self.sounds[sound_id]
        volume_percent = int(sound_data["volume"] * 100)
        file_count = len(sound_data["files"])
        try:
            self.tree.set(sound_id, "Name", sound_data["name"])
            self.tree.set(sound_id, "Key", sound_data["key"])
            self.tree.set(sound_id, "Volume", volume_percent)
            self.tree.set(sound_id, "Files", f"{file_count} variation(s)")
        except Exception:
            try:
                self.tree.insert("", "end", iid=sound_id,
                                 values=(sound_data["name"], sound_data["key"], volume_percent, f"{file_count} variation(s)"))
            except Exception:
                pass

    def edit_volume(self):
        """Open a dialog to adjust volume for selected sound"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a sound to edit volume.")
            return

        item = selected[0]
        if item not in self.sounds:
            messagebox.showerror("Error", "Selected item not found.")
            return

        sound_data = self.sounds[item]
        current_volume = int(sound_data["volume"] * 100)

        volume_window = tk.Toplevel(self.master)
        volume_window.title(f"Adjust Volume - {sound_data['name']}")
        volume_window.geometry("350x150")
        volume_window.resizable(False, False)
        volume_window.transient(self.master)
        volume_window.grab_set()

        tk.Label(volume_window, text=f"Adjust volume for: {sound_data['name']}", font=("Arial", 10, "bold")).pack(pady=10)

        volume_var = tk.IntVar(value=current_volume)
        volume_label = tk.Label(volume_window, text=f"Volume: {current_volume}%", font=("Arial", 10))
        volume_label.pack(pady=5)

        def update_label(val):
            volume_label.config(text=f"Volume: {val}%")

        volume_slider = tk.Scale(volume_window, from_=0, to=100, orient="horizontal",
                                variable=volume_var, command=update_label, length=250)
        volume_slider.pack(pady=5)

        def apply_volume():
            new_volume = volume_var.get()
            sound_data["volume"] = new_volume / 100
            self.update_tree_item(item)
            messagebox.showinfo("Volume Updated", f"Volume set to {new_volume}%")
            volume_window.destroy()

        tk.Button(volume_window, text="Apply", command=apply_volume, width=15).pack(pady=10)

    def edit_keybind(self):
        """Edit the hotkey for selected sound"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a sound to edit keybind.")
            return

        item = selected[0]
        if item not in self.sounds:
            messagebox.showerror("Error", "Selected item not found.")
            return

        sound_entry = self.sounds[item]
        old_key = sound_entry.get("key")
        if old_key == "(unbound)":
            old_key_display = "(unbound)"
            old_key = None
        else:
            old_key_display = old_key

        sound_name = sound_entry.get("name")

        new_key = simpledialog.askstring("Edit Keybind",
                                         f"Enter new hotkey for '{sound_name}':\n(Current: {old_key_display})",
                                         initialvalue=old_key_display if old_key_display != "(unbound)" else "")
        if new_key is None:
            return
        new_key = new_key.lower().strip()
        if new_key == "":
            if old_key:
                self._safe_remove_hotkey_by_key(old_key)
            sound_entry["key"] = "(unbound)"
            self.update_tree_item(item)
            messagebox.showinfo("Key Unbound", f"'{sound_name}' is now unbound.")
            return

        if new_key == old_key:
            return

        conflicting_id = None
        for sid, d in self.sounds.items():
            if sid != item and d.get("key") and d.get("key") == new_key:
                conflicting_id = sid
                break

        if conflicting_id is not None:
            conflicting_name = self.sounds[conflicting_id]["name"]
            confirm = messagebox.askyesno("Keybind Conflict",
                                          f"'{new_key}' is already assigned to '{conflicting_name}'.\n\n"
                                          f"Remove it from '{conflicting_name}' and assign to '{sound_name}'?")
            if not confirm:
                return

            try:
                self._safe_remove_hotkey_by_key(new_key)
            except Exception:
                pass

            self.sounds[conflicting_id]["key"] = "(unbound)"
            self.update_tree_item(conflicting_id)
            messagebox.showinfo("Keybind Removed",
                                f"Removed keybind from '{conflicting_name}'")

        if old_key:
            try:
                self._safe_remove_hotkey_by_key(old_key)
            except Exception:
                pass

        try:
            handle = keyboard.add_hotkey(new_key, self.play_sound, args=(item,))
            self.hotkey_handles[new_key] = handle
            sound_entry["key"] = new_key
            self.update_tree_item(item)
            messagebox.showinfo("Keybind Updated",
                                f"'{sound_name}' is now bound to [{new_key.upper()}]")
        except Exception as e:
            sound_entry["key"] = "(unbound)"
            self.update_tree_item(item)
            messagebox.showerror("Hotkey Error", f"Could not bind hotkey '{new_key}': {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SoundboardApp(root)
    root.mainloop()
