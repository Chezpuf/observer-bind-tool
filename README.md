
# Observer Bind Tool

This Python tool simplifies the process of setting custom keybinds for observing players in Counter-Strike 2. Unlike older methods, this tool sends binds directly to the game via Telnet and remembers your key assignments for each player across map changes.

## Features

-   **Live Binding:** Sends `bind` commands directly to CS2 instantly, bypassing the need to generate and `exec` configuration files.
    
-   **Persistence:** Saves your custom key assignments (e.g., "Player A" is always bound to "F1") to a local file, so you don't have to re-enter them after a map change or game restart.
    

## Prerequisites

1.  **Python 3.x**
    
2.  **Required Library:** Install `telnetlib3` using pip:
    
    ```
    pip install telnetlib3
    
    ```
    

## CS2 Setup (Mandatory)

You must enable the in-game console server (NetCon) via CS2 launch options to allow the tool to communicate with the game.

1.  Open **Steam** > **Library** > **CS2 Properties**.
    
2.  Add the following command to the **Launch Options**:
    
    ```
    -netconport 2020 -tools
    
    ```
    

## Usage Instructions

### 1. Start the Game and Tool

1.  Launch **Counter-Strike 2** and join a server or start a demo (you must be in a game state).
    
2.  Run the Python script:
    
    ```
    python observer_binds.py
    
    ```
    

### 2. Fetch and Assign Binds

1.  Click **"1. Refresh Player List"**. The tool will fetch the current player list and their corresponding server slots.
    
2.  The list will automatically pre-fill any saved key assignments (persistence).
    
3.  Manually enter or adjust the **Bind Key** next to each player.
    

### 3. Send Binds Live

1.  Click **"2. Send Binds Live (via Telnet)"**.
    
2.  The tool immediately sends the configured `bind` commands to CS2. A success message will appear in the status bar.
    
3.  Your custom observer binds are now active in the game.
    

**Note on Persistence:** The first time you assign keys and click "Send Binds Live," the assignments are saved to `observer_tool_bindings.json`. Next time you play, those keys will automatically load for the corresponding players.
