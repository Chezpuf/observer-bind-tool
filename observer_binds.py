import tkinter as tk
from tkinter import messagebox
import re
import os
import time
import threading
import asyncio
import telnetlib3

# --- V V V ---  USER CONFIGURATION - EDIT THIS SECTION --- V V V ---

TELNET_HOST = "127.0.0.1"
TELNET_PORT = 2121
CS2_CFG_PATH = "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/cfg"
OUTPUT_FILENAME = "binds.cfg"

# --- ^ ^ ^ ---  END OF USER CONFIGURATION --- ^ ^ ^ ---

async def fetch_players_async():
    """Connects to CS2 using telnetlib3, runs 'voice_show_mute', and parses the output."""
    players = []
    output = ""
    try:
        reader, writer = await telnetlib3.open_connection(
            TELNET_HOST, TELNET_PORT, shell=None
        )

        writer.write("voice_show_mute\n")

        # Loop to read all incoming data until the server stops sending for a moment
        while True:
            try:
                chunk = await asyncio.wait_for(reader.read(4096), timeout=0.2)
                if not chunk:
                    break
                output += chunk
            except asyncio.TimeoutError:
                break # This is the normal way to exit the loop
        
        # For debugging: prints the full server output to the console
        print("--- RAW TELNET OUTPUT ---\n" + output + "\n-------------------------")

        writer.close()
        await writer.wait_closed()
        
        player_lines = re.findall(r"^\s*(\d+)\s+(.+)$", output, re.MULTILINE)

        for match in player_lines:
            player_num_str, player_name = match
            player_num = int(player_num_str)
            slot = player_num + 1
            players.append({"name": player_name.strip(), "slot": slot})
            
        return players

    except ConnectionRefusedError:
        messagebox.showerror("Connection Error", f"Connection refused on port {TELNET_PORT}.\n\nIs CS2 running with '-netconport {TELNET_PORT}'?")
        return []
    except Exception as e:
        messagebox.showerror("Telnet Error", f"An unexpected error occurred: {e}")
        return []

class ObserverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 Observer Bind Tool (Telnetlib3)")
        self.root.geometry("450x450")
        
        self.players = []
        self.entry_widgets = []

        if not os.path.isdir(CS2_CFG_PATH):
             messagebox.showerror("Configuration Error", f"The CS2 CFG path is invalid!\n\nPlease edit the script and fix CS2_CFG_PATH.")
             self.root.destroy()
             return
        self.setup_ui()

    def setup_ui(self):
        controls_frame = tk.Frame(self.root, padx=10, pady=10)
        controls_frame.pack(fill=tk.X)
        
        self.refresh_button = tk.Button(controls_frame, text="Refresh Player List", command=self.threaded_refresh_players)
        self.refresh_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.generate_button = tk.Button(controls_frame, text="Generate Binds File", command=self.generate_config, font=("Segoe UI", 8, "bold"))
        self.generate_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.player_frame = tk.Frame(self.root, padx=10)
        self.player_frame.pack(fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(self.root, text="Click 'Refresh' to get player list from CS2.", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def threaded_refresh_players(self):
        self.status_label.config(text="Connecting to CS2...")
        self.refresh_button.config(state=tk.DISABLED)
        threading.Thread(target=self._run_async_fetch, daemon=True).start()

    def _run_async_fetch(self):
        fetched_players = asyncio.run(fetch_players_async())
        self.root.after(0, self.populate_player_list, fetched_players)

    def populate_player_list(self, fetched_players):
        for widget in self.player_frame.winfo_children():
            widget.destroy()
        self.entry_widgets.clear()
        
        self.players = fetched_players
        
        tk.Label(self.player_frame, text="Bind Key", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5, pady=2)
        tk.Label(self.player_frame, text="Player Name (Server Slot)", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=5, sticky="w")
        
        for i, player in enumerate(self.players):
            entry = tk.Entry(self.player_frame, width=5, justify='center')
            entry.grid(row=i + 1, column=0, padx=5, pady=2)
            self.entry_widgets.append(entry)
            
            label_text = f"{player['name']} (Slot: {player['slot']})"
            label = tk.Label(self.player_frame, text=label_text)
            label.grid(row=i + 1, column=1, padx=5, sticky="w")
            
        self.refresh_button.config(state=tk.NORMAL)
        if self.players:
            self.status_label.config(text=f"Successfully fetched {len(self.players)} players.")
        else:
            self.status_label.config(text="No players found. Make sure you are in a server.")

    def generate_config(self):
        if not self.players:
            messagebox.showwarning("Warning", "Player list is empty. Refresh first.")
            return

        config_lines = [
            f"// --- Manually Generated Observer Binds ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---",
            "spec_usenumberkeys_nobinds false",
            "echo \">>> Custom Telnet observer binds loaded.\""
        ]

        for i, player in enumerate(self.players):
            key = self.entry_widgets[i].get().strip()
            if key:
                line = f'bind "{key}" "spec_player {player["slot"]}" // {player["name"]}'
                config_lines.append(line)
        
        output_path = os.path.join(CS2_CFG_PATH, OUTPUT_FILENAME)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(config_lines))
            self.status_label.config(text="SUCCESS: Binds file generated!")
            messagebox.showinfo("Success", f"Config file '{OUTPUT_FILENAME}' was generated successfully.")
        except Exception as e:
            messagebox.showerror("File Error", f"Could not write to the config file.\nError: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ObserverApp(root)

    root.mainloop()
