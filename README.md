# TeleStream TUI

This is a simple Terminal User Interface (TUI) application, built in Python with the [Textual](https://textual.textualize.io/) library, to stream local video files or YouTube streams to a Telegram channel using `ffmpeg`.

<img width="1066" height="795" alt="telestream1" src="https://github.com/user-attachments/assets/8b89a921-6307-4086-8b64-7d7b36b31340" />

<img width="1066" height="795" alt="telestream2" src="https://github.com/user-attachments/assets/7ebcf299-cbb1-4391-b882-876b25b360bf" />


## Features

-   Simple text-based user interface for easy use.
-   Stream a local video file or a YouTube video.
-   Saves the last used stream key for convenience.
-   Displays basic status and error logs.
-   Buttons to start and stop streaming.
-   **Favorite Servers Management**: Add, edit, and remove favorite streaming servers (Name, URL, and Stream Key) for quick access.

## Prerequisites

-   **Python 3.7+**
-   **ffmpeg**: You need to have `ffmpeg` installed and accessible in your system's `PATH`.
    -   For Debian/Ubuntu: `sudo apt update && sudo apt install ffmpeg`
    -   For Arch Linux: `sudo pacman -S ffmpeg`
    -   For macOS (using Homebrew): `brew install ffmpeg`

## Installation

1.  Clone this repository or download the files.
2.  Navigate to the project directory:
    ```bash
    cd telestream-tui
    ```
3.  Install the necessary Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## How to Use

1.  Run the application:
    ```bash
    python app.py
    ```
2.  **Video Source**: You have two options for the video source, which are mutually exclusive:
    *   **Video Path**: Enter the absolute path to the local video file you want to stream (e.g., `/home/user/my_video.mp4`).
    *   **Or YouTube URL**: Paste the URL of the YouTube video you want to stream (e.g., `https://www.youtube.com/watch?v=...`).
3.  **Favorite Servers Management**:
    *   Click the "Manage Favorites" button to open the management screen.
    *   On this screen, you can add new favorite servers by providing a Name, the Server URL (e.g., `rtmps://dc1-1.rtmp.t.me/s/`), and the Stream Key.
    *   Select a favorite from the table to edit its details or remove it.
    *   Changes are automatically saved to `config.json`.
4.  **Server Selection**: On the main screen, use the "Favorite Server" dropdown to select one of your saved servers. The Server URL and Stream Key will be automatically filled.
5.  **Server URL**: This field will be automatically filled when selecting a favorite. You can also edit it manually if you are not using a favorite.
6.  **Stream Key**: This field will be automatically filled when selecting a favorite. You can also edit it manually if you are not using a favorite. The field hides the key for privacy.
7.  **Start Stream**: Press the "Start Stream" button to begin streaming.
8.  **Stop Stream**: Press the "Stop Stream" button to end the `ffmpeg` process. You can also exit the application with `Esc` and confirming the exit.
