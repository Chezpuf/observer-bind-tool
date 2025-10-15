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
DEFAULT_TELNET_HOST = "127.0.0.1" # Used as default in the hosts list
DEFAULT_TELNET_PORT = 2020

# File for saving and loading key assignments and settings (IPs/Port)
BINDINGS_FILE = "observer_bind_tool.json"

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
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 Live Observer Bind Tool (Telnet)")
        self.root.geometry("500x550") # Slightly taller for new controls
        
        self.players = []
        self.entry_widgets = []
        
        # Persistent storage: maps player name to key ('PlayerName': 'key_binding')
        # Also stores last used IPs/Port
        self.persistent_data = self._load_data()
        
        # hosts_var holds a comma-separated string of IPs
        hosts_str = self.persistent_data.get('hosts', DEFAULT_TELNET_HOST)
        # Handle backward compatibility from single 'host' key
        if 'host' in self.persistent_data and self.persistent_data['host'] != hosts_str:
            hosts_str = self.persistent_data['host']
            
        self.hosts_var = tk.StringVar(value=hosts_str)
        self.port_var = tk.StringVar(value=self.persistent_data.get('port', DEFAULT_TELNET_PORT))
        self.persistent_bindings = self.persistent_data.get('bindings', {})

        if not os.path.isdir(CS2_CFG_PATH):
             pass 

        self.setup_ui()
        
        # Initial save of defaults if file didn't exist
        self._save_data()

    def _load_data(self):
        """Loads persistent data (bindings, hosts, port) from a local JSON file."""
        try:
            if os.path.exists(BINDINGS_FILE):
                with open(BINDINGS_FILE, 'r') as f:
                    data = json.load(f)
                    
                    # Handle transition from single 'host' key to 'hosts'
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
        # Update current values from GUI vars before saving
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
        
        # Split by comma or semicolon, clean up spaces, and filter out empty strings
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
        
        self.refresh_button = tk.Button(controls_frame, text="1. Refresh Player List", command=self.threaded_refresh_players, bg='#475569', fg='white', relief=tk.RAISED, activebackground='#64748b')
        self.refresh_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, ipady=5)
        
        self.send_button = tk.Button(controls_frame, text="2. Send Binds Live (via Telnet)", command=self.threaded_send_binds, font=("Segoe UI", 9, "bold"), bg='#10b981', fg='white', relief=tk.RAISED, activebackground='#059669')
        self.send_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, ipady=5)
        
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
        
        # Status Bar at the bottom, left-aligned content (anchor=tk.W)
        # Added padx=10 here to visually push the text content away from the left edge.
        self.status_label = tk.Label(self.root, text="Set IPs/Port and click 'Refresh'.", bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=10, pady=2, fg='#475569')
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
    def threaded_refresh_players(self):
        hosts = self._get_hosts_list()
        
        if not hosts:
            messagebox.showerror("Configuration Error", "Please enter at least one Host IP.")
            return

        # We only fetch player data from the FIRST host in the list
        host = hosts[0] 
        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("Configuration Error", "Port must be a valid number.")
            return
        
        # Save current settings
        self._save_data() 
        
        self.status_label.config(text=f"Connecting to {host}:{port} to fetch players...")
        self.refresh_button.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        
        threading.Thread(target=self._run_async_fetch, args=(host, port), daemon=True).start()

    def _run_async_fetch(self, host, port):
        # Runs in a separate thread, fetches players and potential error message
        fetched_players, error_message = asyncio.run(fetch_players_async(host, port))
        
        # Schedule the UI update back on the main Tkinter thread
        self.root.after(0, self.populate_player_list, fetched_players, error_message)

    def populate_player_list(self, fetched_players, error_message):
        """Clears and rebuilds the player list UI, pre-filling keys from persistent bindings."""
        
        # Re-enable buttons immediately
        self.refresh_button.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)

        # Handle errors before updating the list
        if error_message:
            messagebox.showerror("Connection/Telnet Error", error_message)
            self.status_label.config(text=f"ERROR: Failed to connect to {self._get_hosts_list()[0]}. See error box.")
            return
            
        # Clear existing player list UI
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
            
        if self.players:
            self.status_label.config(text=f"Successfully fetched {len(self.players)} players from first IP.")
        else:
            self.status_label.config(text="No players found. Ensure you are in a server/demo.")

    def threaded_send_binds(self):
        """Prepares commands, updates persistence, and runs async send function."""
        if not self.players:
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
        new_bindings = {} # Temp dictionary to update player persistence

        for i, player in enumerate(self.players):
            key = self.entry_widgets[i].get().strip()
            player_name_key = player['name']
            
            if key:
                # Create the bind command: bind "key" "spec_player slot"
                command = f'bind "{key}" "spec_player {player["slot"]}"'
                bind_commands.append(command)
                
                # Update persistent data with the current assignment
                new_bindings[player_name_key] = key
        
        # Store the updated bindings and settings immediately for persistence
        self.persistent_bindings = new_bindings
        self._save_data()
        
        # Run the async send function in a thread
        self.status_label.config(text=f"Sending commands to {len(hosts)} host(s)...")
        self.send_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        
        # Pass all hosts to the async runner
        threading.Thread(target=self._run_async_send, args=(hosts, port, bind_commands), daemon=True).start()
        
    def _run_async_send(self, hosts, port, bind_commands):
        """Iterates through all hosts and runs the async send for each one."""
        all_results = []
        
        for host in hosts:
            # We must run asyncio for each host sequentially in the single thread
            success, error_message = asyncio.run(send_bind_commands_async(host, port, bind_commands))
            all_results.append((host, success, error_message))
                
        # Schedule the UI update back on the main Tkinter thread
        self.root.after(0, self._handle_send_completion, all_results)

    def _handle_send_completion(self, all_results):
        self.send_button.config(state=tk.NORMAL)
        self.refresh_button.config(state=tk.NORMAL)
        
        failed_hosts = [host for host, success, error in all_results if not success]
        
        if not failed_hosts:
            self.status_label.config(text="SUCCESS: Binds sent live to all configured CS2 instances!")
        else:
            first_fail_message = next((error for host, success, error in all_results if not success and error), "One or more hosts failed to connect.")
            # Use a message box to show the full detail of the failures
            messagebox.showwarning("Partial Success / Failure", f"Failed to connect to the following hosts: {', '.join(failed_hosts)}\n\nFirst error encountered: {first_fail_message}")
            self.status_label.config(text=f"FAILED: Binds failed on {len(failed_hosts)} of {len(all_results)} hosts. Check warning box.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ObserverApp(root)
    root.mainloop()
