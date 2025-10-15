import tkinter as tk
from tkinter import messagebox
import re
import os
import time
import threading
import asyncio
import telnetlib3
import json

# --- V V V ---  USER CONFIGURATION - EDIT THIS SECTION --- V V V ---

# 1. Telnet connection details (should match your CS2 launch options)
TELNET_HOST = "127.0.0.1"
TELNET_PORT = 2020

# 2. Full path to your CS2 'cfg' directory. (Optional for this version, but good to keep)
CS2_CFG_PATH = "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/cfg"

# File for saving and loading key assignments (Key -> Player Name)
BINDINGS_FILE = "observer_tool_bindings.json"

# --- ^ ^ ^ ---  END OF USER CONFIGURATION --- ^ ^ ^ ---

async def fetch_players_async():
    """Connects to CS2, runs 'voice_show_mute', and parses the output."""
    players = []
    output = ""
    try:
        reader, writer = await telnetlib3.open_connection(
            TELNET_HOST, TELNET_PORT, shell=None
        )

        writer.write("voice_show_mute\n")

        # Loop to read all incoming data until the server stops sending
        while True:
            try:
                # Use a short timeout to reliably read all data packets
                chunk = await asyncio.wait_for(reader.read(4096), timeout=0.2)
                if not chunk:
                    break
                output += chunk
            except asyncio.TimeoutError:
                break
        
        writer.close()
        await writer.wait_closed()
        
        # Regex finds the slot number and the player name
        player_lines = re.findall(r"^\s*(\d+)\s+(.+)$", output, re.MULTILINE)

        for match in player_lines:
            player_num_str, player_name = match
            player_num = int(player_num_str)
            slot = player_num + 1
            players.append({"name": player_name.strip(), "slot": slot})
            
        return players

    except ConnectionRefusedError:
        messagebox.showerror("Connection Error", f"Connection refused on port {TELNET_PORT}.\n\nIs CS2 running with '-netconport {TELNET_PORT}' in launch options?")
        return []
    except Exception as e:
        messagebox.showerror("Telnet Error", f"An unexpected error occurred during fetch: {e}")
        return []

async def send_bind_commands_async(bind_commands):
    """Connects to CS2 and sends a list of command strings directly."""
    try:
        reader, writer = await telnetlib3.open_connection(
            TELNET_HOST, TELNET_PORT, shell=None
        )

        # Send a brief delay command to ensure connection is stable before sending binds
        writer.write("echo \"Sending observer binds...\"\n")
        await asyncio.sleep(0.1) 
        
        for command in bind_commands:
            # Sending the command as a string with a newline
            writer.write(command + '\n') 
            
        # FIX: Send the final confirmation command as a string instead of a bytes literal
        writer.write("echo \"Observer binds successfully applied.\"\n")

        writer.close()
        await writer.wait_closed()
        return True

    except ConnectionRefusedError:
        messagebox.showerror("Connection Error", f"Connection refused on port {TELNET_PORT}.\n\nIs CS2 running and fully loaded? Binds were not sent.")
        return False
    except Exception as e:
        messagebox.showerror("Telnet Error", f"Failed to send commands: {e}")
        return False

class ObserverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 Live Observer Bind Tool (Telnet)")
        self.root.geometry("500x500")
        
        self.players = []
        self.entry_widgets = []
        # Persistent storage: maps player name to key ('PlayerName': 'key_binding')
        self.persistent_bindings = self._load_bindings()

        if not os.path.isdir(CS2_CFG_PATH):
             pass 

        self.setup_ui()

    def _load_bindings(self):
        """Loads persistent bindings from a local JSON file."""
        try:
            if os.path.exists(BINDINGS_FILE):
                with open(BINDINGS_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            return {}
        return {}

    def _save_bindings(self):
        """Saves current key assignments to a local JSON file."""
        try:
            with open(BINDINGS_FILE, 'w') as f:
                json.dump(self.persistent_bindings, f, indent=4)
        except Exception as e:
            messagebox.showwarning("Save Error", f"Could not save persistent bindings: {e}")

    def setup_ui(self):
        controls_frame = tk.Frame(self.root, padx=10, pady=10)
        controls_frame.pack(fill=tk.X)
        
        self.refresh_button = tk.Button(controls_frame, text="1. Refresh Player List", command=self.threaded_refresh_players, bg='#475569', fg='white', relief=tk.RAISED, activebackground='#64748b')
        self.refresh_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, ipady=5)
        
        # Changed "Generate Binds File" to "Send Binds Live"
        self.send_button = tk.Button(controls_frame, text="2. Send Binds Live (via Telnet)", command=self.threaded_send_binds, font=("Segoe UI", 9, "bold"), bg='#10b981', fg='white', relief=tk.RAISED, activebackground='#059669')
        self.send_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, ipady=5)
        
        tk.Label(self.root, text="Current Player Bindings (Enter Key below)", font=("Segoe UI", 10, "bold"), pady=5).pack(fill=tk.X)

        self.player_canvas = tk.Canvas(self.root, borderwidth=0)
        self.player_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=(0, 5))

        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.player_canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.player_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.player_frame = tk.Frame(self.player_canvas)
        self.player_canvas.create_window((0, 0), window=self.player_frame, anchor="nw")
        
        self.player_frame.bind("<Configure>", lambda e: self.player_canvas.config(scrollregion=self.player_canvas.bbox("all")))
        
        self.status_label = tk.Label(self.root, text="Click 'Refresh' to get player list.", bd=1, relief=tk.SUNKEN, anchor=tk.W, pady=2)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
    def threaded_refresh_players(self):
        self.status_label.config(text="Connecting to CS2...")
        self.refresh_button.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        threading.Thread(target=self._run_async_fetch, daemon=True).start()

    def _run_async_fetch(self):
        fetched_players = asyncio.run(fetch_players_async())
        self.root.after(0, self.populate_player_list, fetched_players)

    def populate_player_list(self, fetched_players):
        """Clears and rebuilds the player list UI, pre-filling keys from persistent bindings."""
        for widget in self.player_frame.winfo_children():
            widget.destroy()
        self.entry_widgets.clear()
        
        self.players = fetched_players
        
        tk.Label(self.player_frame, text="Bind Key", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5, pady=5)
        tk.Label(self.player_frame, text="Player Name (Server Slot)", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=5, sticky="w")
        
        for i, player in enumerate(self.players):
            entry = tk.Entry(self.player_frame, width=8, justify='center')
            
            # --- Persistence Logic ---
            player_name_key = player['name']
            if player_name_key in self.persistent_bindings:
                # Pre-fill the entry with the saved key
                saved_key = self.persistent_bindings[player_name_key]
                entry.insert(0, saved_key)
            # -------------------------
                
            entry.grid(row=i + 1, column=0, padx=5, pady=2)
            self.entry_widgets.append(entry)
            
            label_text = f"{player['name']} (Slot: {player['slot']})"
            label = tk.Label(self.player_frame, text=label_text, anchor='w')
            label.grid(row=i + 1, column=1, padx=5, sticky="w")
            
        self.refresh_button.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
        if self.players:
            self.status_label.config(text=f"Successfully fetched {len(self.players)} players.")
        else:
            self.status_label.config(text="No players found. Ensure you are in a server/demo.")

    def threaded_send_binds(self):
        """Prepares commands, updates persistence, and runs async send function."""
        if not self.players:
            messagebox.showwarning("Warning", "Player list is empty. Refresh first.")
            return

        # Always start by disabling the default number keys to allow custom binds
        bind_commands = ['spec_usenumberkeys_nobinds false']
        new_bindings = {} # Temp dictionary to update persistence

        for i, player in enumerate(self.players):
            key = self.entry_widgets[i].get().strip()
            player_name_key = player['name']
            
            if key:
                # Create the bind command: bind "key" "spec_player slot"
                command = f'bind "{key}" "spec_player {player["slot"]}"'
                bind_commands.append(command)
                
                # Update persistent data with the current assignment
                new_bindings[player_name_key] = key
        
        # Store the updated bindings immediately for persistence
        self.persistent_bindings = new_bindings
        self._save_bindings()
        
        # Run the async send function in a thread
        self.status_label.config(text="Sending commands to CS2...")
        self.send_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        
        threading.Thread(target=self._run_async_send, args=(bind_commands,), daemon=True).start()
        
    def _run_async_send(self, bind_commands):
        success = asyncio.run(send_bind_commands_async(bind_commands))
        self.root.after(0, self._handle_send_completion, success)

    def _handle_send_completion(self, success):
        self.send_button.config(state=tk.NORMAL)
        self.refresh_button.config(state=tk.NORMAL)
        
        if success:
            self.status_label.config(text="SUCCESS: Binds sent live to CS2 via Telnet!")
        else:
            self.status_label.config(text="FAILED: Check connection error box above.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ObserverApp(root)
    root.mainloop()
