
# CS2 Observer Bind Tool
This Python tool connects to Counter-Strike 2 via Telnet to retrieve the official server player slots. It allows you to manually assign custom keybinds to spectators slots and automatically generates a complete configuration file for easy use in CS2. The tool uses the  `telnetlib3` library for network communication.
## Prerequisites
Python 3.x: Ensure you have Python installed.
Required Library: You must install the `telnetlib3` library using pip:

    pip install telnetlib3

## Setup


The script connects to CS2 using the NetCon server, which must be enabled via launch options.

 1. Open your Steam Library.
 2. Right-click on Counter-Strike 2 and select Properties.
 3. Under the General tab, find the Launch Options text box.
 4. Add the following command:

    `-netconport 2020`
    (Note: If you use a different port in your Python script, change this number to match.)

### 2. Tool Configuration
Before running the script, you must edit the `CS2_CFG_PATH` variable to point to your local CS2 configuration folder.

Open the Python script and modify the USER CONFIGURATION section:

    CS2_CFG_PATH = "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/cfg"

Crucial: Verify this path is correct for your system. Using forward slashes (`/`) is recommended, even on Windows.

### 3. Usage Instructions

**Step 1: Run the Tool and CS2**
1. Launch CS2 and join a server or start a demo (you must be in a game state to fetch players).
2. Run the Python script.

**Step 2: Fetch Player List**
1. In the GUI tool, click the "Refresh Player List" button.
2. The script will connect to CS2 and populate the list with players.
- If you get a connection error, ensure CS2 is running and the `-netconport` is correctly set.

**Step 3: Assign Keybinds**
1. The list will show each player and their calculated Server Slot number (Player # + 1).
2. Manually type the desired Bind Key (e.g., 1, f1, mouse5) into the input box next to each player.

**Step 4: Generate Configuration File**
1. Click the "Generate Binds File" button.
2. This creates the file `binds.cfg` inside your CS2 `cfg` folder, containing lines like:

bind "1" "spec_player 5" // PlayerName1
bind "2" "spec_player 6" // PlayerName2
spec_usenumberkeys_nobinds false

    bind "1" "spec_player 5" // PlayerName1
    bind "2" "spec_player 6" // PlayerName2
    spec_usenumberkeys_nobinds false

Step 5: Activate Binds In-Game
1. Go back into CS2.
2. You can execute the file directly in the console:

       exec binds.cfg

Recommendation: Bind the execution to a single key for quick reloading:

    bind "F11" "binds.cfg"

Now, pressing F11 will load your custom binds whenever you need them.

### Troubleshooting
|Problem|Cause|Solution|
|--|--|--|
|`Connection Refused`|CS2 is not running or Telnet is not enabled.|Ensure CS2 is running and you have `-netconport 2020` in your launch options.|
|`...CS2 CFG path is invalid...`|The `CS2_CFG_PATH` variable is wrong.|Find the correct `.../csgo/cfg` path on your system and update the Python script.|
|`ModuleNotFoundError: telnetlib3`|The required library is not installed.|Run `pip install telnetlib3` in your terminal.|
