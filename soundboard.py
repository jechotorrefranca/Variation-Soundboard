import os
import json
import shutil
import random
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

        pygame.mixer.quit()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        print("Pygame mixer initialized:", pygame.mixer.get_init())

        self.sounds = {}

        if not os.path.exists(SOUNDS_FOLDER):
            os.makedirs(SOUNDS_FOLDER)

        # UI
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
        tk.Button(btn_frame, text="Save Config", command=self.save_config, width=12).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(btn_frame, text="Load Config", command=self.load_config, width=12).grid(row=1, column=2, padx=5, pady=5)

        if os.path.exists(CONFIG_FILE):
            self.load_config()

    def edit_volume(self):
        """Open a dialog to adjust volume for selected sound"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a sound to edit volume.")
            return
        
        item = selected[0]
        values = self.tree.item(item, "values")
        key = values[1].lower()
        current_volume = int(self.sounds[key]["volume"] * 100)
        
        volume_window = tk.Toplevel(self.master)
        volume_window.title(f"Adjust Volume - {values[0]}")
        volume_window.geometry("350x150")
        volume_window.resizable(False, False)
        volume_window.transient(self.master)
        volume_window.grab_set()
        
        tk.Label(volume_window, text=f"Adjust volume for: {values[0]}", font=("Arial", 10, "bold")).pack(pady=10)
        
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
            self.sounds[key]["volume"] = new_volume / 100
            self.update_tree_item(item, key)
            messagebox.showinfo("Volume Updated", f"Volume set to {new_volume}%")
            volume_window.destroy()
        
        tk.Button(volume_window, text="Apply", command=apply_volume, width=15).pack(pady=10)

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

        key = key.lower()
        
        if key in self.sounds:
            messagebox.showerror("Duplicate Key", f"Hotkey '{key}' is already assigned!")
            return

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

        self.sounds[key] = {
            "name": name,
            "folder": sound_folder,
            "files": copied_files,
            "volume": 1.0
        }
        
        # Add to tree
        self.tree.insert("", "end", values=(name, key, 100, f"{len(copied_files)} variation(s)"))

        try:
            keyboard.add_hotkey(key, self.play_sound, args=(key,))
            messagebox.showinfo("Hotkey Assigned", 
                              f"{name} is now bound to [{key.upper()}]\n{len(copied_files)} variation(s) added")
        except Exception as e:
            messagebox.showerror("Hotkey Error", f"Could not bind hotkey: {e}")
            del self.sounds[key]
            shutil.rmtree(sound_folder)
            self.tree.delete(self.tree.get_children()[-1])

    def add_variations(self):
        """Add more audio file variations to an existing sound"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a sound to add variations to.")
            return
        
        item = selected[0]
        values = self.tree.item(item, "values")
        key = values[1].lower()
        
        filepaths = filedialog.askopenfilenames(title="Select Additional Sound File(s)", 
                                               filetypes=[("Audio Files", "*.wav *.mp3 *.ogg")])
        if not filepaths:
            return
        
        sound_data = self.sounds[key]
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
        
        self.update_tree_item(item, key)
        messagebox.showinfo("Variations Added", 
                          f"Added {len(filepaths)} variation(s)\nTotal: {len(sound_data['files'])}")

    def play_sound(self, key):
        """Play a random variation of the sound"""
        sound_data = self.sounds.get(key)
        if not sound_data or not sound_data["files"]:
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
            print(f"Error playing sound '{sound_data['name']}': {e}")
            messagebox.showerror("Playback Error", f"Could not play {sound_data['name']}: {e}")

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
            
        for item in selected:
            values = self.tree.item(item, "values")
            key = values[1].lower()
            if key in self.sounds:
                # Delete the entire sound folder
                try:
                    folder_path = self.sounds[key]["folder"]
                    if os.path.exists(folder_path):
                        shutil.rmtree(folder_path)
                        print(f"Deleted folder: {folder_path}")
                except Exception as e:
                    print(f"Could not delete folder: {e}")
                
                try:
                    keyboard.remove_hotkey(key)
                except:
                    pass
                
                del self.sounds[key]
            
            self.tree.delete(item)

    def save_config(self):
        """Save the soundboard configuration"""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.sounds, f, indent=4)
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
                self.sounds = json.load(f)
            
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            keyboard.unhook_all_hotkeys()
            
            for key, data in self.sounds.items():
                volume_percent = int(data.get("volume", 1.0) * 100)
                file_count = len(data.get("files", []))
                self.tree.insert("", "end", values=(data["name"], key, volume_percent, f"{file_count} variation(s)"))
                try:
                    keyboard.add_hotkey(key, self.play_sound, args=(key,))
                except Exception as e:
                    print(f"Could not bind hotkey {key}: {e}")
            
            messagebox.showinfo("Loaded", f"Loaded {len(self.sounds)} sound(s)!")
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load configuration: {e}")

    def update_tree_item(self, item, key):
        """Update a tree item with current sound data"""
        sound_data = self.sounds[key]
        volume_percent = int(sound_data["volume"] * 100)
        file_count = len(sound_data["files"])
        self.tree.set(item, "Name", sound_data["name"])
        self.tree.set(item, "Key", key)
        self.tree.set(item, "Volume", volume_percent)
        self.tree.set(item, "Files", f"{file_count} variation(s)")

    def _sanitize_folder_name(self, name):
        """Remove invalid characters from folder name"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()


if __name__ == "__main__":
    root = tk.Tk()
    app = SoundboardApp(root)
    root.mainloop()