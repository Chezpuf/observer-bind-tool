
# Chezpuf's CS2 Observer Bind Tool

This tool simplifies the process of managing player key bindings for CS2 observers via Telnet, especially during halftime swaps.

## Prerequisites

To use this tool, your CS2 client **must** be launched with the network console and developer tools enabled. Add the following to your CS2 Launch Options in Steam:

```
-netconport 2020 -tools

```

(Note: You can change the port number, but ensure it matches the setting in the application.)

## Features

-   **Live Player List:** Fetches all currently connected users (players and spectators) from the server.
    
-   **Persistent Binds:** Saves player key assignments locally, so they are remembered between matches.
    
-   **One-Click Swap:** The **Swap** button rotates the key binds for the two teams (1 → 6, 2 → 7, 5 → 0, etc.) and automatically sends the new binds to the game.
    
-   **Coach Exclusion:** Players identified as a 'Coach' or 'Spectator' will retain their custom bind keys during the swap.
    

## How to Use

1.  **Configure Connection:** Enter the IP address of your local machine (`127.0.0.1` by default) and the Telnet port (`2020` by default).
    
2.  **Refresh List:** Click **Refresh List** to fetch all current users from the game.
    
3.  **Set Binds:** Enter the desired player key (e.g., `1`, `2`, `q`, `e`) next to the corresponding player's name.
    
4.  **Send Binds:**
    
    -   Click **Send Binds** to immediately push the current key assignments to the game.
        
    -   Click **Swap** at halftime. This will rotate the keys in the GUI and automatically send the new binds live.
