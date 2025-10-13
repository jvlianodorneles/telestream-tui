
import io
import json
import os
import subprocess
import threading
from pathlib import Path
import gettext
import logging
import yt_dlp

# Setup gettext for internationalization
LOCALE_DIR = Path(__file__).parent / "locale"
gettext.bindtextdomain("messages", LOCALE_DIR)
gettext.textdomain("messages")
gettext.install("messages", LOCALE_DIR)
from gettext import gettext as _

import qrcode
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Header, Footer, Input, Label, Static, DirectoryTree, Log, Select, DataTable

CONFIG_FILE = Path("config.json")

DEFAULT_CONFIG = {
    "last_stream_key": "",
    "favorites": []
}

def load_config() -> dict:
    """Carrega a configuração do arquivo config.json."""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        # Merge com a configuração padrão para garantir que todas as chaves existam
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        return merged_config
    except json.JSONDecodeError:
        # Se o arquivo estiver corrompido, retorna a configuração padrão
        return DEFAULT_CONFIG.copy()

def save_config(config: dict) -> None:
    """Salva a configuração no arquivo config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)




class QuitScreen(ModalScreen):
    """Screen to confirm if the user wants to quit."""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="quit-dialog"):
            yield Label(_("Are you sure you want to quit?"), id="quit-question")
            with Horizontal(id="quit-buttons"):
                yield Button(_("✅ Yes"), variant="error", id="quit-yes")
                yield Button(_("❌ No"), variant="primary", id="quit-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit-yes":
            self.app.action_graceful_quit()
        else:
            self.app.pop_screen()


class FileBrowserScreen(Screen):
    """Screen to browse and select a video file."""

    BINDINGS = [("escape", "dismiss", "Back")]

    def compose(self) -> ComposeResult:
        yield Header(name=_("File Browser"))
        # Starts at the system root directory
        yield DirectoryTree(path="/", id="tree_view")
        with Horizontal(classes="button-container"):
            yield Button(_("⬅️ Back"), id="back_from_file_browser", variant="default")
        yield Footer()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Called when a file is selected."""
        self.dismiss(str(event.path))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_from_file_browser":
            self.dismiss()


class AboutScreen(Screen):
    """Tela de informações do desenvolvedor e doações."""

    BINDINGS = [("escape", "app.pop_screen", _("Back"))]

    def compose(self) -> ComposeResult:
        yield Header(name=_("About/Donate"))
        with Vertical(classes="about-container"):
            yield Static(_("PIX:"), id="pix-label")
            with Horizontal(classes="qr-code-container"):
                yield Static(self.get_pix_qr_code(), id="qr-code")
            yield Static(_("\nEnjoying the app? Consider sending a collectible gift on Telegram: https://t.me/jvlianodorneles"), id="telegram-gift-label")
            with Horizontal(classes="button-container"):
                yield Button(_("⬅️ Back"), id="back", variant="primary")
        yield Footer()

    def get_pix_qr_code(self) -> str:
        """Gera um QR code ASCII para o código PIX."""
        pix_string = "00020126580014br.gov.bcb.pix0136aa97cd56-b793-4c39-94be-c190a29f40865204000053039865802BR5925JULIANO_DORNELES_DOS_SANT6012Santo_Angelo610998803-41762290525C7X00138965117602953262656304D7E8"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,  # Borda mínima para o menor tamanho possível
        )
        qr.add_data(pix_string)
        qr.make(fit=True)

        f = io.StringIO()
        qr.print_ascii(out=f)
        f.seek(0)
        return f.read()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Gerencia o clique do botão de voltar."""
        if event.button.id == "back":
            self.app.pop_screen()


class FavoritesScreen(Screen):
    """Tela para gerenciar servidores favoritos."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header(name=_("Manage Favorites"))
        with Container(id="favorites-container"):
            yield Label(_("Favorite Servers"), classes="screen-title")
            yield DataTable(id="favorites_table", cursor_type="row")
            with Vertical(id="favorite-form"):
                yield Label(_("Name:"))
                yield Input(placeholder=_("Server Name"), id="fav_name_input")
                yield Label(_("Server URL:"))
                yield Input(placeholder=_("rtmps://..."), id="fav_url_input")
                yield Label(_("Stream Key:"))
                with Horizontal():
                    yield Input(placeholder=_("secret_key"), id="fav_key_input", password=True)
                    yield Button(_("👁️ Show"), id="toggle_fav_password", variant="default")
                with Horizontal(id="fav-buttons"):
                    yield Button(_("➕ Add"), id="add_favorite", variant="primary")
                    yield Button(_("💾 Save Edit"), id="edit_favorite", variant="default", disabled=True)
                    yield Button(_("🗑️ Remove"), id="remove_favorite", variant="error", disabled=True)
                    yield Button(_("🧹 Clear Fields"), id="clear_fields", variant="default")
                    yield Button(_("⬅️ Back"), id="back_from_favorites", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#favorites_table", DataTable)
        table.add_columns(_("Name"), _("URL"), _("Key"))
        self.editing_favorite_original_name = None # Para rastrear o favorito sendo editado
        self.load_favorites_to_table()

    def load_favorites_to_table(self) -> None:
        table = self.query_one("#favorites_table", DataTable)
        table.clear()
        for fav in self.app.favorites:
            # Exibir apenas os primeiros 10 caracteres da chave por segurança
            display_key = fav["key"][:10] + "..." if len(fav["key"]) > 10 else fav["key"]
            table.add_row(fav["name"], fav["url"], display_key, key=fav["name"])
        self.query_one("#edit_favorite", Button).disabled = True
        self.query_one("#remove_favorite", Button).disabled = True
        self.clear_form_fields()

    def clear_form_fields(self) -> None:
        self.query_one("#fav_name_input", Input).value = ""
        self.query_one("#fav_url_input", Input).value = ""
        self.query_one("#fav_key_input", Input).value = ""
        self.query_one("#add_favorite", Button).disabled = False
        self.query_one("#edit_favorite", Button).disabled = True
        self.query_one("#remove_favorite", Button).disabled = True

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        selected_name = str(event.row_key.value)
        self.app.log_message(f"Favorite selected in table: {selected_name}")
        self.editing_favorite_original_name = selected_name # Stores the original name for editing
        for fav in self.app.favorites:
            if fav["name"] == selected_name:
                self.query_one("#fav_name_input", Input).value = fav["name"]
                self.query_one("#fav_url_input", Input).value = fav["url"]
                self.query_one("#fav_key_input", Input).value = fav["key"]
                self.query_one("#add_favorite", Button).disabled = True
                self.query_one("#edit_favorite", Button).disabled = False
                self.query_one("#remove_favorite", Button).disabled = False
                self.app.log_message(f"Fields populated for {selected_name}")
                break

    def on_button_pressed(self, event: Button.Pressed) -> None:
        name = self.query_one("#fav_name_input", Input).value.strip()
        url = self.query_one("#fav_url_input", Input).value.strip()
        key = self.query_one("#fav_key_input", Input).value.strip()

        if event.button.id == "clear_fields":
            self.clear_form_fields()
            self.editing_favorite_original_name = None # Clears the editing state
            return

        elif event.button.id == "back_from_favorites":
            self.app.pop_screen()
            return

        elif event.button.id == "toggle_fav_password":
            fav_key_input = self.query_one("#fav_key_input", Input)
            fav_key_input.password = not fav_key_input.password
            button = self.query_one("#toggle_fav_password", Button)
            button.label = _("👁️ Show") if fav_key_input.password else _("🙈 Hide")
            return

        if not name or not url or not key:
            self.app.log_message(_("[ERROR] All fields (Name, URL, Key) are required."))
            return

        if event.button.id == "add_favorite":
            if any(fav["name"] == name for fav in self.app.favorites):
                self.app.log_message(_(f"[ERROR] A favorite with the name '{name}' already exists."))
                return
            self.app.favorites.append({"name": name, "url": url, "key": key})
            self.app.log_message(_(f"Favorite '{name}' added."))
        elif event.button.id == "edit_favorite":
            if self.editing_favorite_original_name is None:
                self.app.log_message(_("[ERROR] No favorite selected for editing."))
                return
            
            # Checks if the new name already exists and is not the original name of the favorite being edited
            if name != self.editing_favorite_original_name and any(fav["name"] == name for fav in self.app.favorites):
                self.app.log_message(_(f"[ERROR] Another favorite with the name '{name}' already exists."))
                return

            found = False
            for i, fav in enumerate(self.app.favorites):
                if fav["name"] == self.editing_favorite_original_name: # Uses the original name to find
                    self.app.favorites[i] = {"name": name, "url": url, "key": key}
                    found = True
                    self.app.log_message(_(f"Favorite '{self.editing_favorite_original_name}' updated to '{name}'."))
                    break
            if not found:
                self.app.log_message(_(f"[ERROR] Original favorite '{self.editing_favorite_original_name}' not found for editing."))
                return
            self.editing_favorite_original_name = None # Clears the editing state after saving
        elif event.button.id == "remove_favorite":
            if self.editing_favorite_original_name is None:
                self.app.log_message(_("[ERROR] No favorite selected for removal."))
                return
            
            initial_len = len(self.app.favorites)
            self.app.favorites = [fav for fav in self.app.favorites if fav["name"] != self.editing_favorite_original_name]
            if len(self.app.favorites) < initial_len:
                self.app.log_message(_(f"Favorite '{self.editing_favorite_original_name}' removed."))
            else:
                self.app.log_message(_(f"[ERROR] Favorite '{self.editing_favorite_original_name}' not found for removal."))
                return
            self.editing_favorite_original_name = None # Clears the editing state after removing
        
        self.app.config["favorites"] = self.app.favorites
        save_config(self.app.config)
        self.load_favorites_to_table()
        self.app.populate_favorites_dropdown() # Updates the dropdown on the main screen
        self.clear_form_fields()


class LogScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", _("Back"))]

    def compose(self) -> ComposeResult:
        yield Header(name=_("Application Log"))
        with Container(id="log-screen-container"):
            yield Log(id="log_viewer_screen")
            with Horizontal(classes="button-container"):
                yield Button(_("⬅️ Back"), id="back_from_log", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        # Populate log viewer with history
        log_viewer = self.query_one("#log_viewer_screen", Log)
        for message in self.app.log_history:
            log_viewer.write_line(message)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_from_log":
            self.app.pop_screen()


class TeleStreamApp(App):
    """Um aplicativo TUI para transmitir vídeos para o Telegram."""

    CSS_PATH = "app.css"
    BINDINGS = [
        ("d", "toggle_dark", _("Toggle dark mode")),
        ("escape", "show_quit_dialog", _("Quit")),
    ]

    def action_show_quit_dialog(self) -> None:
        """Mostra a tela de confirmação de saída."""
        self.push_screen(QuitScreen())

    def action_graceful_quit(self) -> None:
        """Para a transmissão (se estiver ativa) e sai do app."""
        if self.streaming_process and self.streaming_process.poll() is None:
            self.stop_streaming()
        self.exit()


    def compose(self) -> ComposeResult:
        """Cria os widgets filhos para o aplicativo."""
        yield Header(name="TeleStream TUI")
        with Container():
            yield Label(_("Video Path:"))
            with Horizontal():
                yield Input(placeholder=_("e.g.: /home/user/video.mp4"), id="video_path")
                yield Button(_("📁 Browse..."), id="browse", variant="default")

            yield Label(_("Or YouTube URL:"))
            yield Input(placeholder=_("e.g.: https://www.youtube.com/watch?v=..."), id="youtube_url")
            
            yield Label(_("Favorite Server:"))
            with Horizontal():
                yield Select([], id="favorite_server_select")
            
            yield Label(_("Server URL (RTMP/RTMPS):"))
            yield Input(placeholder=_("e.g.: rtmps://dc1-1.rtmp.t.me/s/"), id="server_url")            
            yield Label(_("Telegram Stream Key:"))
            with Horizontal():
                yield Input(placeholder=_("e.g.: 123456:abc-123"), id="stream_key", password=True)
                yield Button(_("👁️ Show"), id="toggle_password", variant="default")
            
            with Horizontal(id="main-action-buttons"):
                yield Button(_("▶️ Start Stream"), id="start", variant="primary")
                yield Button(_("⏹️ Stop Stream"), id="stop", variant="error", disabled=True)
            with Horizontal(id="main-utility-buttons"):
                yield Button(_("📜 Show Log"), id="show_log", variant="default")
                yield Button(_("ℹ️ About/Donate"), id="about", variant="default")
                yield Button(_("⭐ Manage Favorites"), id="manage_favorites", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        """Chamado quando o aplicativo é montado."""
        self.setup_logging()
        self.config = load_config()
        self.favorites = self.config.get("favorites", [])
        self.streaming_process = None
        self.populate_favorites_dropdown()
        self.load_last_stream_key()
        self.log_history = [] # Initialize log history

    def setup_logging(self):
        """Configures logging to a file."""
        log_file = "telestream.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file)
            ]
        )


    def populate_favorites_dropdown(self) -> None:
        """Popula o dropdown de servidores favoritos."""
        select_widget = self.query_one("#favorite_server_select", Select)
        options = [(fav["name"], fav["name"]) for fav in self.favorites]
        select_widget.set_options(options)
        if self.favorites:
            # Tenta selecionar o último favorito usado, se existir
            last_fav_name = self.config.get("last_favorite_name")
            # Verifica se o último favorito ainda existe na lista atual
            if last_fav_name and any(fav["name"] == last_fav_name for fav in self.favorites):
                select_widget.value = last_fav_name
            else:
                # Se o último favorito não existe mais, seleciona o primeiro da lista
                select_widget.value = self.favorites[0]["name"]
                self.config["last_favorite_name"] = self.favorites[0]["name"]
                save_config(self.config)
            # Dispara o evento de mudança para preencher os campos de URL e chave
            self.on_select_changed(Select.Changed(select_widget, select_widget.value))
        else:
            select_widget.clear()
            self.query_one("#server_url", Input).value = ""
            self.query_one("#stream_key", Input).value = ""
            self.config.pop("last_favorite_name", None) # Remove o último favorito se a lista estiver vazia
            save_config(self.config)

    def load_last_stream_key(self) -> None:
        """Loads the last saved stream key and fills the field if no favorite is selected."""
        if not self.query_one("#stream_key", Input).value:
            self.query_one("#stream_key", Input).value = self.config.get("last_stream_key", "")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Called when the value of an input changes."""
        if event.input.id == "video_path":
            if event.value:
                self.query_one("#youtube_url", Input).value = ""
                self.query_one("#youtube_url", Input).disabled = True
            else:
                self.query_one("#youtube_url", Input).disabled = False
        elif event.input.id == "youtube_url":
            if event.value:
                self.query_one("#video_path", Input).value = ""
                self.query_one("#video_path", Input).disabled = True
                self.query_one("#browse", Button).disabled = True
            else:
                self.query_one("#video_path", Input).disabled = False
                self.query_one("#browse", Button).disabled = False

    def on_select_changed(self, event: Select.Changed) -> None:
        """Called when a favorite is selected from the dropdown."""
        if event.control.id == "favorite_server_select":
            selected_name = event.value
            if selected_name:
                for fav in self.favorites:
                    if fav["name"] == selected_name:
                        self.query_one("#server_url", Input).value = fav["url"]
                        self.query_one("#stream_key", Input).value = fav["key"]
                        self.config["last_favorite_name"] = selected_name
                        save_config(self.config)
                        break
            else:
                self.query_one("#server_url", Input).value = ""
                self.query_one("#stream_key", Input).value = self.config.get("last_stream_key", "")

    def log_message(self, message: str) -> None:
        """Displays a message in the log viewer, stores it in history, and logs to a file."""
        message = message.strip()
        self.log_history.append(message)
        logging.info(message)
        # If LogScreen is active, update its log viewer
        if isinstance(self.screen, LogScreen):
            log_viewer = self.screen.query_one("#log_viewer_screen", Log)
            log_viewer.write_line(message)

    def show_file_browser(self) -> None:
        """Shows the file browser screen."""
        def on_file_select(path: str) -> None:
            """Callback for when a file is selected."""
            if path is not None:
                self.query_one("#video_path", Input).value = path

        self.push_screen(FileBrowserScreen(), on_file_select)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles button clicks."""
        if event.button.id == "browse":
            self.show_file_browser()

        elif event.button.id == "toggle_password":
            stream_key_input = self.query_one("#stream_key", Input)
            stream_key_input.password = not stream_key_input.password
            button = self.query_one("#toggle_password", Button)
            button.label = _("👁️ Show") if stream_key_input.password else _("🙈 Hide")

        elif event.button.id == "show_log":
            self.push_screen(LogScreen())

        elif event.button.id == "about":
            self.push_screen(AboutScreen())

        elif event.button.id == "manage_favorites":
            self.push_screen(FavoritesScreen())

        elif event.button.id == "start":
            video_path = self.query_one("#video_path", Input).value
            youtube_url = self.query_one("#youtube_url", Input).value
            server_url = self.query_one("#server_url", Input).value
            stream_key = self.query_one("#stream_key", Input).value

            if not (video_path or youtube_url) or not server_url or not stream_key:
                self.log_message(_("[ERROR] Server URL and stream key are required, plus a video path or YouTube URL."))
                return

            if video_path and not os.path.exists(video_path):
                self.log_message(_(f"[ERROR] File not found: {video_path}"))
                return

            # Saves the last stream key and the name of the favorite used
            self.config["last_stream_key"] = stream_key
            selected_favorite_name = self.query_one("#favorite_server_select", Select).value
            if selected_favorite_name:
                self.config["last_favorite_name"] = selected_favorite_name
            else:
                self.config.pop("last_favorite_name", None) # Removes last favorite if none selected
            save_config(self.config)

            stream_source = video_path if video_path else youtube_url
            self.start_streaming(stream_source, server_url, stream_key)

        elif event.button.id == "stop":
            self.stop_streaming()

    def start_streaming(self, stream_source: str, server_url: str, stream_key: str):
        """Starts the streaming process with ffmpeg."""
        self.log_message(_("Starting stream..."))
        self.query_one("#start", Button).disabled = True
        self.query_one("#stop", Button).disabled = False

        input_source = stream_source

        # If it's a YouTube URL, get the direct stream URL
        if stream_source.startswith("http"): 
            try:
                self.log_message(_("Fetching YouTube stream URL..."))
                ydl_opts = {
                    'format': 'best[ext=mp4]/best',
                    'quiet': True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(stream_source, download=False)
                    input_source = info['url']
                self.log_message(_("Successfully fetched stream URL."))
            except Exception as e:
                self.log_message(_(f"[ERROR] Failed to get YouTube stream URL: {e}"))
                self.query_one("#start", Button).disabled = False
                self.query_one("#stop", Button).disabled = True
                return

        # The full URL is the server URL + stream key
        full_rtmp_url = f"{server_url}/{stream_key}"
        
        command = [
            "ffmpeg",
        ]

        # Add loop for local files, not for URLs
        if not stream_source.startswith("http"):
            command.extend(["-stream_loop", "-1"])

        command.extend([
            "-i", input_source,
            "-vcodec", "libx264",
            "-b:v", "10M",
            "-acodec", "aac",
            "-b:a", "128k",
            "-f", "flv",
            full_rtmp_url,
        ])

        try:
            self.streaming_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            self.log_message(_(f"Streaming started with PID: {self.streaming_process.pid}"))

            # Starts the thread to read ffmpeg output
            thread = threading.Thread(
                target=self._stream_ffmpeg_output, 
                args=(self.streaming_process,),
                daemon=True
            )
            thread.start()

        except FileNotFoundError:
            self.log_message(_("[ERROR] ffmpeg not found. Check if it's installed and in PATH."))
            self.query_one("#start", Button).disabled = False
            self.query_one("#stop", Button).disabled = True
        except Exception as e:
            self.log_message(_(f"[ERROR] Failed to start ffmpeg: {e}"))
            self.query_one("#start", Button).disabled = False
            self.query_one("#stop", Button).disabled = True

    def _stream_ffmpeg_output(self, process: subprocess.Popen):
        """Reads and displays process output in a thread."""
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                self.call_from_thread(self.log_message, line)
            process.stdout.close()

    def stop_streaming(self):
        """Stops the streaming process."""
        if self.streaming_process and self.streaming_process.poll() is None:
            self.log_message(_("Stopping stream..."))
            self.streaming_process.terminate()
            try:
                self.streaming_process.wait(timeout=5)
                self.log_message(_("Stream stopped successfully."))
            except subprocess.TimeoutExpired:
                self.log_message(_("ffmpeg did not respond, forcing termination."))
                self.streaming_process.kill()
                self.log_message(_("Stream forced to stop."))
            finally:
                self.streaming_process = None
                self.query_one("#start", Button).disabled = False
                self.query_one("#stop", Button).disabled = True
                self.log_message(_("Stream stopped."))
        else:
            self.log_message(_("No active stream to stop."))


if __name__ == "__main__":
    app = TeleStreamApp()
    app.run()
