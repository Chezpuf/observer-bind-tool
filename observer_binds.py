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

# Default Telnet connection details (used if no saved values exist)
DEFAULT_TELNET_HOST = "127.00.1" # Used as default in the hosts list
DEFAULT_TELNET_PORT = 2020

# Full path to your CS2 'cfg' directory. (Optional for this version, but good to keep)
CS2_CFG_PATH = "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/cfg"

# File for saving and loading key assignments and settings (IPs/Port)
BINDINGS_FILE = "observer_tool_bindings.json"

# --- ^ ^ ^ ---  END OF USER CONFIGURATION --- ^ ^ ^ ---

async def fetch_players_async(host, port):
    """
    Connects to CS2, runs 'voice_show_mute', and parses the output.
    Returns: (list of players, error_message or None)
    """
    players = []
    output = ""
    error_message = None
    try:
        reader, writer = await telnetlib3.open_connection(
            host, port, shell=None
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
            
    except ConnectionRefusedError:
        error_message = f"Connection refused on {host}:{port}.\n\nIs CS2 running with '-netconport {port}' in launch options?"
    except Exception as e:
        error_message = f"An unexpected error occurred during fetch: {e}"
        
    return players, error_message

async def send_bind_commands_async(host, port, bind_commands):
    """
    Connects to CS2 and sends a list of command strings directly to a single host.
    Returns: (success_boolean, error_message or None)
    """
    error_message = None
    try:
        reader, writer = await telnetlib3.open_connection(
            host, port, shell=None
        )

        # Send a brief delay command to ensure connection is stable before sending binds
        writer.write(f"echo \"Sending observer binds to {host}...\n")
        await asyncio.sleep(0.1) 
        
        for command in bind_commands:
            # Sending the command as a string with a newline
            writer.write(command + '\n') 
            
        # Send the final confirmation command as a string
        writer.write(f"echo \"Observer binds successfully applied on {host}.\n")

        writer.close()
        await writer.wait_closed()
        return True, None

    except ConnectionRefusedError:
        error_message = f"Connection refused on {host}:{port}.\n\nIs CS2 running and fully loaded? Binds were not sent."
    except Exception as e:
        error_message = f"Failed to send commands to {host}: {e}"
        
    return False, error_message

class ObserverApp:
    
    # Terms used to identify users who should be excluded from the Halftime Swap
    EXCLUSION_TERMS = ["coach", "spectator", "spec", "caster", "admin"]
    
    # Fixed key map for the halftime swap (Old Key -> New Key)
    # The user specifies: 1->6, 2->7, 3->8, 4->9, 5->0, 6->1, 7->2, 8->3, 9->4, 0->5
    SWAP_KEY_MAP = {
        '1': '6', '2': '7', '3': '8', '4': '9', '5': '0',
        '6': '1', '7': '2', '8': '3', '9': '4', '0': '5'
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Chezpuf's Observer Bind Tool")
        self.root.geometry("500x550") 
        
        # self.players holds a unified list of ALL *connected* slots being displayed
        self.players = [] 
        # Maps slot number to the index in self.players and self.entry_widgets
        self.slot_to_index = {} 
        self.entry_widgets = [] 
        
        # Persistent storage
        self.persistent_data = self._load_data()
        
        hosts_str = self.persistent_data.get('hosts', DEFAULT_TELNET_HOST)
        if 'host' in self.persistent_data and self.persistent_data['host'] != hosts_str:
            hosts_str = self.persistent_data['host']
            
        self.hosts_var = tk.StringVar(value=hosts_str)
        self.port_var = tk.StringVar(value=self.persistent_data.get('port', DEFAULT_TELNET_PORT))
        self.persistent_bindings = self.persistent_data.get('bindings', {})

        self.setup_ui()
        self._save_data()

    def _load_data(self):
        """Loads persistent data (bindings, hosts, port) from a local JSON file."""
        try:
            bindings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), BINDINGS_FILE) if hasattr(os, 'path') and os.path.abspath(__file__) else BINDINGS_FILE

            if os.path.exists(bindings_path):
                with open(bindings_path, 'r') as f:
                    data = json.load(f)
                    
                    host_single = data.pop('host', None)
                    data.setdefault('hosts', host_single or DEFAULT_TELNET_HOST)
                    
                    data.setdefault('bindings', {})
                    data.setdefault('port', DEFAULT_TELNET_PORT)
                    return data
        except Exception:
            pass
        
        return {'bindings': {}, 'hosts': DEFAULT_TELNET_HOST, 'port': DEFAULT_TELNET_PORT}

    def _save_data(self):
        """Saves current data (bindings, hosts, port) to a local JSON file."""
        self.persistent_data['hosts'] = self.hosts_var.get()
        self.persistent_data['port'] = self.port_var.get()
        self.persistent_data['bindings'] = self.persistent_bindings

        try:
            with open(BINDINGS_FILE, 'w') as f:
                json.dump(self.persistent_data, f, indent=4)
        except Exception as e:
            messagebox.showwarning("Save Error", f"Could not save persistent data: {e}")

    def _get_hosts_list(self):
        """Parses the comma-separated hosts string into a clean list of IPs."""
        hosts_string = self.hosts_var.get()
        if not hosts_string:
            return []
        
        hosts = [h.strip() for h in re.split(r'[;,\s]+', hosts_string) if h.strip()]
        return hosts

    def setup_ui(self):
        # --- Connection Configuration Frame ---
        config_frame = tk.Frame(self.root, padx=10, pady=5, bd=2, relief=tk.GROOVE)
        config_frame.pack(fill=tk.X)

        tk.Label(config_frame, text="Telnet Host IPs (comma-separated):", anchor="w").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        hosts_entry = tk.Entry(config_frame, textvariable=self.hosts_var, relief=tk.SUNKEN)
        hosts_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew", columnspan=3)

        tk.Label(config_frame, text="Port:", anchor="w").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        port_entry = tk.Entry(config_frame, textvariable=self.port_var, width=8, relief=tk.SUNKEN)
        port_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        
        config_frame.grid_columnconfigure(1, weight=1)
        
        # --- Control Buttons Frame ---
        controls_frame = tk.Frame(self.root, padx=10, pady=10)
        controls_frame.pack(fill=tk.X)
        
        # Renamed from "1. Refresh Player List"
        self.refresh_button = tk.Button(controls_frame, text="Refresh List", command=self.threaded_refresh_players, bg='#475569', fg='white', relief=tk.RAISED, activebackground='#64748b')
        self.refresh_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, ipady=5)
        
        # Renamed from "2. Send Binds Live (via Telnet)"
        self.send_button = tk.Button(controls_frame, text="Send Binds", command=self.threaded_send_binds, font=("Segoe UI", 9, "bold"), bg='#10b981', fg='white', relief=tk.RAISED, activebackground='#059669')
        self.send_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, ipady=5)
        
        # Renamed from "3. Halftime Swap (Keys 1-5 <-> 6-0)"
        self.swap_button = tk.Button(controls_frame, text="Swap", command=self.halftime_swap, font=("Segoe UI", 9, "bold"), bg='#f97316', fg='white', relief=tk.RAISED, activebackground='#ea580c')
        self.swap_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, ipady=5)
        
        tk.Label(self.root, text="Current Player Bindings (Enter Key below)", font=("Segoe UI", 10, "bold"), pady=5).pack(fill=tk.X)

        # --- Player List Scrollable Area ---
        self.player_canvas = tk.Canvas(self.root, borderwidth=0)
        self.player_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=(0, 5))

        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.player_canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.player_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.player_frame = tk.Frame(self.player_canvas)
        self.player_canvas.create_window((0, 0), window=self.player_frame, anchor="nw")
        
        self.player_frame.bind("<Configure>", lambda e: self.player_canvas.config(scrollregion=self.player_canvas.bbox("all")))
        
        # Status Bar
        self.status_label = tk.Label(self.root, text="Set IPs/Port and click 'Refresh'.", bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=10, pady=2, fg='#475569')
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _is_player_excluded(self, player_obj):
        """Helper to check if a player should be excluded from the symmetrical swap."""
        if player_obj and player_obj['name']:
            name = player_obj['name'].lower()
            return any(term in name for term in self.EXCLUSION_TERMS)
        return False
    
    def halftime_swap(self):
        """
        Performs a rotational swap of the bind keys (1<->6, 2<->7, etc.) on the GUI,
        saves the new configuration, and then automatically triggers the Telnet send.
        """
        if not self.players:
             messagebox.showwarning("Swap Failed", "Player list is empty. Please 'Refresh List' first.")
             return

        # 1. Store the keys BEFORE the swap for status message (sampling 1 and 6)
        pre_swap_keys = {
            '1': self.entry_widgets[self.slot_to_index.get(1)].get().strip() if 1 in self.slot_to_index else '',
            '6': self.entry_widgets[self.slot_to_index.get(6)].get().strip() if 6 in self.slot_to_index else ''
        }
        
        # 2. Iterate over all displayed players and swap the keys in the GUI entries
        for i, player in enumerate(self.players):
            
            data = self.players[i]
            entry = self.entry_widgets[i]
            
            if self._is_player_excluded(data):
                continue

            current_key = entry.get().strip()
            
            if current_key in self.SWAP_KEY_MAP:
                new_key = self.SWAP_KEY_MAP[current_key]
                
                entry.delete(0, tk.END)
                entry.insert(0, new_key)
            
        # 3. Update persistent bindings based on the final state of the GUI
        self.persistent_bindings = {}
        for i, player in enumerate(self.players):
            key = self.entry_widgets[i].get().strip()
            
            if key:
                self.persistent_bindings[player['name']] = key
        
        # 4. Save to file
        self._save_data() 

        # 5. Update status bar and show message *before* starting the send thread
        post_swap_keys = {
            '1': self.entry_widgets[self.slot_to_index.get(1)].get().strip() if 1 in self.slot_to_index else '',
            '6': self.entry_widgets[self.slot_to_index.get(6)].get().strip() if 6 in self.slot_to_index else ''
        }
        
        status_text = (
            f"GUI Swap Complete. Keys rotated: 1->{post_swap_keys.get('1', 'N/A')}, 6->{post_swap_keys.get('6', 'N/A')}. "
            f"NOW SENDING BINDS LIVE..."
        )
        self.status_label.config(text=status_text)
        
        messagebox.showinfo("Swap & Send Initiated", "Keys have been rotated (1<->6, etc.) and the commands are now being sent live to CS2 via Telnet.")

        # 6. CRITICAL CHANGE: Automatically trigger the send function
        self.threaded_send_binds()


    def threaded_refresh_players(self):
        hosts = self._get_hosts_list()
        
        if not hosts:
            messagebox.showerror("Configuration Error", "Please enter at least one Host IP.")
            return

        host = hosts[0] 
        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("Configuration Error", "Port must be a valid number.")
            return
        
        self._save_data() 
        
        self.status_label.config(text=f"Connecting to {host}:{port} to fetch players...")
        self.refresh_button.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.swap_button.config(state=tk.DISABLED) 
        
        threading.Thread(target=self._run_async_fetch, args=(host, port), daemon=True).start()

    def _run_async_fetch(self, host, port):
        fetched_players, error_message = asyncio.run(fetch_players_async(host, port))
        self.root.after(0, self.populate_player_list, fetched_players, error_message)

    def populate_player_list(self, fetched_players, error_message):
        """
        Clears and rebuilds the UI, showing *only* connected players, 
        and updates the self.players list used by all other functions.
        """
        
        self.refresh_button.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
        self.swap_button.config(state=tk.NORMAL) 
        
        if error_message:
            messagebox.showerror("Connection/Telnet Error", error_message)
            self.status_label.config(text=f"ERROR: Failed to connect to {self._get_hosts_list()[0]}. See error box.")
            return
        
        # 1. Filter out any slots that were returned but have empty names
        connected_players = [p for p in fetched_players if p.get('name')]
        connected_players.sort(key=lambda p: p['slot'])
        
        # 2. Update the master list used by all other functions
        self.players = connected_players
        self.slot_to_index = {p['slot']: i for i, p in enumerate(self.players)}

        # Clear existing player list UI
        for widget in self.player_frame.winfo_children():
            widget.destroy()
        self.entry_widgets.clear()
        
        # Draw Headers
        tk.Label(self.player_frame, text="Bind Key", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5, pady=5)
        tk.Label(self.player_frame, text="Player Name (Slot)", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, padx=5, sticky="w")
        
        # 3. Draw rows for all connected players
        for i, player in enumerate(self.players):
            entry = tk.Entry(self.player_frame, width=8, justify='center')
            
            # Persistence Load: Try to load the key based on the player's name
            if player['name'] in self.persistent_bindings:
                saved_key = self.persistent_bindings[player['name']]
                entry.insert(0, saved_key)
            
            entry.grid(row=i + 1, column=0, padx=5, pady=2)
            self.entry_widgets.append(entry)
            
            # Display Label 
            label_text = f"{player['name']} (Slot: {player['slot']})"
            label = tk.Label(self.player_frame, text=label_text, anchor='w')
            label.grid(row=i + 1, column=1, padx=5, sticky="w")
            
        # Update scroll region and status bar
        self.player_canvas.update_idletasks()
        self.player_canvas.config(scrollregion=self.player_canvas.bbox("all"))

        active_count = len([p for p in self.players if 1 <= p['slot'] <= 10])
        spectator_count = len([p for p in self.players if p['slot'] > 10])
            
        status_text = f"Successfully fetched {len(self.players)} connected users ({active_count} players, {spectator_count} spectators)."
        self.status_label.config(text=status_text)


    def threaded_send_binds(self):
        """Prepares commands, updates persistence, and runs async send function."""
        # Note: This function is called by both the 'Send' button and the 'Swap' button.
        if not self.players:
            # Only show this error if called directly by the button and data is missing
            if self.send_button['state'] == tk.NORMAL:
                messagebox.showwarning("Warning", "Player list is empty. Refresh first.")
            return

        hosts = self._get_hosts_list()
        if not hosts:
            messagebox.showerror("Configuration Error", "Please enter at least one Host IP.")
            return

        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("Configuration Error", "Port must be a valid number.")
            return
        
        # Always start by disabling the default number keys to allow custom binds
        bind_commands = ['spec_usenumberkeys_nobinds false']
        new_bindings = {} 

        # This loop processes commands for *all* connected players
        for i, player in enumerate(self.players):
            key = self.entry_widgets[i].get().strip()
            player_name_key = player['name']
            
            # Only send a bind command if a key is entered
            if key:
                # The command uses the current Server Slot (player['slot']) and the key in the GUI
                command = f'bind "{key}" "spec_player {player["slot"]}"'
                bind_commands.append(command)
                
                # Update persistent data with the current assignment (Player Name -> Key)
                new_bindings[player_name_key] = key
        
        # Store the updated bindings and settings immediately for persistence
        self.persistent_bindings = new_bindings
        self._save_data()
        
        # Run the async send function in a thread
        self.status_label.config(text=f"Sending commands to {len(hosts)} host(s)...")
        self.send_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        self.swap_button.config(state=tk.DISABLED) 
        
        threading.Thread(target=self._run_async_send, args=(hosts, port, bind_commands), daemon=True).start()
        
    def _run_async_send(self, hosts, port, bind_commands):
        """Iterates through all hosts and runs the async send for each one."""
        all_results = []
        
        for host in hosts:
            success, error_message = asyncio.run(send_bind_commands_async(host, port, bind_commands))
            all_results.append((host, success, error_message))
                
        self.root.after(0, self._handle_send_completion, all_results)

    def _handle_send_completion(self, all_results):
        self.send_button.config(state=tk.NORMAL)
        self.refresh_button.config(state=tk.NORMAL)
        self.swap_button.config(state=tk.NORMAL) 
        
        failed_hosts = [host for host, success, error in all_results if not success]
        
        if not failed_hosts:
            self.status_label.config(text="SUCCESS: Binds sent live to all configured CS2 instances!")
        else:
            first_fail_message = next((error for host, success, error in all_results if not success and error), "One or more hosts failed to connect.")
            messagebox.showwarning("Partial Success / Failure", f"Failed to connect to the following hosts: {', '.join(failed_hosts)}\n\nFirst error encountered: {first_fail_message}")
            self.status_label.config(text=f"FAILED: Binds failed on {len(failed_hosts)} of {len(all_results)} hosts. Check warning box.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ObserverApp(root)
    root.mainloop()
