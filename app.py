
import io
import json
import os
import subprocess
import threading
from pathlib import Path

import qrcode
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Header, Footer, Input, Label, Static, DirectoryTree, Log, Select, DataTable, Select

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
    """Tela de confirmação de saída."""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="quit-dialog"):
            yield Label("Are you sure you want to quit?", id="quit-question")
            with Horizontal(id="quit-buttons"):
                yield Button("Yes", variant="error", id="quit-yes")
                yield Button("No", variant="primary", id="quit-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit-yes":
            self.app.action_graceful_quit()
        else:
            self.app.pop_screen()


class FileBrowserScreen(Screen):
    """Tela para navegar e selecionar um arquivo de vídeo."""

    def compose(self) -> ComposeResult:
        yield Header(name="File Browser")
        # Começa no diretório raiz do sistema
        yield DirectoryTree(path="/", id="tree_view")
        yield Footer()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Chamado quando um arquivo é selecionado."""
        self.dismiss(str(event.path))


class AboutScreen(Screen):
    """Tela de informações do desenvolvedor e doações."""

    BINDINGS = [("escape", "app.pop_screen", "Voltar")]

    def compose(self) -> ComposeResult:
        yield Header(name="About/Donate")
        with Vertical(classes="about-container"):
            yield Static("PIX:", id="pix-label")
            with Horizontal(classes="qr-code-container"):
                yield Static(self.get_pix_qr_code(), id="qr-code")
            yield Static("\nEnjoying the app? Consider sending a collectible gift on Telegram: https://t.me/jvlianodorneles", id="telegram-gift-label")
            with Horizontal(classes="button-container"):
                yield Button("Back", id="back", variant="primary")
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
        yield Header(name="Manage Favorites")
        with Container(id="favorites-container"):
            yield Label("Favorite Servers", classes="screen-title")
            yield DataTable(id="favorites_table", cursor_type="row")
            with Vertical(id="favorite-form"):
                yield Label("Name:")
                yield Input(placeholder="Server Name", id="fav_name_input")
                yield Label("Server URL:")
                yield Input(placeholder="rtmps://...", id="fav_url_input")
                yield Label("Stream Key:")
                with Horizontal():
                    yield Input(placeholder="secret_key", id="fav_key_input", password=True)
                    yield Button("Show", id="toggle_fav_password", variant="default")
                with Horizontal(id="fav-buttons"):
                    yield Button("Add", id="add_favorite", variant="primary")
                    yield Button("Save Edit", id="edit_favorite", variant="default", disabled=True)
                    yield Button("Remove", id="remove_favorite", variant="error", disabled=True)
                    yield Button("Clear Fields", id="clear_fields", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#favorites_table", DataTable)
        table.add_columns("Name", "URL", "Key")
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

        elif event.button.id == "toggle_fav_password":
            fav_key_input = self.query_one("#fav_key_input", Input)
            fav_key_input.password = not fav_key_input.password
            button = self.query_one("#toggle_fav_password", Button)
            button.label = "Show" if fav_key_input.password else "Hide"
            return

        if not name or not url or not key:
            self.app.log_message("[ERROR] All fields (Name, URL, Key) are required.")
            return

        if event.button.id == "add_favorite":
            if any(fav["name"] == name for fav in self.app.favorites):
                self.app.log_message(f"[ERROR] A favorite with the name '{name}' already exists.")
                return
            self.app.favorites.append({"name": name, "url": url, "key": key})
            self.app.log_message(f"Favorite '{name}' added.")
        elif event.button.id == "edit_favorite":
            if self.editing_favorite_original_name is None:
                self.app.log_message("[ERROR] No favorite selected for editing.")
                return
            
            # Checks if the new name already exists and is not the original name of the favorite being edited
            if name != self.editing_favorite_original_name and any(fav["name"] == name for fav in self.app.favorites):
                self.app.log_message(f"[ERROR] Another favorite with the name '{name}' already exists.")
                return

            found = False
            for i, fav in enumerate(self.app.favorites):
                if fav["name"] == self.editing_favorite_original_name: # Uses the original name to find
                    self.app.favorites[i] = {"name": name, "url": url, "key": key}
                    found = True
                    self.app.log_message(f"Favorite '{self.editing_favorite_original_name}' updated to '{name}'.")
                    break
            if not found:
                self.app.log_message(f"[ERROR] Original favorite '{self.editing_favorite_original_name}' not found for editing.")
                return
            self.editing_favorite_original_name = None # Clears the editing state after saving
        elif event.button.id == "remove_favorite":
            if self.editing_favorite_original_name is None:
                self.app.log_message("[ERROR] No favorite selected for removal.")
                return
            
            initial_len = len(self.app.favorites)
            self.app.favorites = [fav for fav in self.app.favorites if fav["name"] != self.editing_favorite_original_name]
            if len(self.app.favorites) < initial_len:
                self.app.log_message(f"Favorite '{self.editing_favorite_original_name}' removed.")
            else:
                self.app.log_message(f"[ERROR] Favorite '{self.editing_favorite_original_name}' not found for removal.")
                return
            self.editing_favorite_original_name = None # Clears the editing state after removing
        
        self.app.config["favorites"] = self.app.favorites
        save_config(self.app.config)
        self.load_favorites_to_table()
        self.app.populate_favorites_dropdown() # Updates the dropdown on the main screen
        self.clear_form_fields()


class TeleStreamApp(App):
    """Um aplicativo TUI para transmitir vídeos para o Telegram."""

    CSS_PATH = "app.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("escape", "show_quit_dialog", "Quit"),
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
            yield Label("Video Path:")
            with Horizontal():
                yield Input(placeholder="e.g.: /home/user/video.mp4", id="video_path")
                yield Button("Browse...", id="browse", variant="default")
            
            yield Label("Favorite Server:")
            with Horizontal():
                yield Select([], id="favorite_server_select")
                yield Button("Manage Favorites", id="manage_favorites", variant="default")
            
            yield Label("Server URL (RTMP/RTMPS):")
            yield Input(placeholder="e.g.: rtmps://dc1-1.rtmp.t.me/s/", id="server_url")
            
            yield Label("Telegram Stream Key:")
            with Horizontal():
                yield Input(placeholder="e.g.: 123456:abc-123", id="stream_key", password=True)
                yield Button("Show", id="toggle_password", variant="default")
            
            with Horizontal():
                yield Button("Start Stream", id="start", variant="primary")
                yield Button("Stop Stream", id="stop", variant="error", disabled=True)
            with Horizontal():
                yield Button("Hide Log", id="toggle_log", variant="default")
                yield Button("About/Donate", id="about", variant="default")
            yield Log(id="log_viewer")
        yield Footer()

    def on_mount(self) -> None:
        """Chamado quando o aplicativo é montado."""
        self.config = load_config()
        self.favorites = self.config.get("favorites", [])
        self.streaming_process = None
        self.populate_favorites_dropdown()
        self.load_last_stream_key()

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
        """Displays a message in the log viewer."""
        log_viewer = self.query_one("#log_viewer", Log)
        log_viewer.write_line(message.strip())

    def show_file_browser(self) -> None:
        """Shows the file browser screen."""
        def on_file_select(path: str) -> None:
            """Callback for when a file is selected."""
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
            button.label = "Show" if stream_key_input.password else "Hide"

        elif event.button.id == "toggle_log":
            log_viewer = self.query_one("#log_viewer")
            log_viewer.toggle_class("hidden")
            button = self.query_one("#toggle_log", Button)
            button.label = "Show Log" if log_viewer.has_class("hidden") else "Hide Log"

        elif event.button.id == "about":
            self.push_screen(AboutScreen())

        elif event.button.id == "manage_favorites":
            self.push_screen(FavoritesScreen())

        elif event.button.id == "start":
            video_path = self.query_one("#video_path", Input).value
            server_url = self.query_one("#server_url", Input).value
            stream_key = self.query_one("#stream_key", Input).value

            if not video_path or not server_url or not stream_key:
                self.log_message("[ERROR] Video path, server URL, and stream key are required.")
                return

            if not os.path.exists(video_path):
                self.log_message(f"[ERROR] File not found: {video_path}")
                return

            # Saves the last stream key and the name of the favorite used
            self.config["last_stream_key"] = stream_key
            selected_favorite_name = self.query_one("#favorite_server_select", Select).value
            if selected_favorite_name:
                self.config["last_favorite_name"] = selected_favorite_name
            else:
                self.config.pop("last_favorite_name", None) # Removes last favorite if none selected
            save_config(self.config)

            self.start_streaming(video_path, server_url, stream_key)

        elif event.button.id == "stop":
            self.stop_streaming()

    def start_streaming(self, video_path: str, server_url: str, stream_key: str):
        """Starts the streaming process with ffmpeg."""
        self.log_message("Starting stream...")
        self.query_one("#start", Button).disabled = True
        self.query_one("#stop", Button).disabled = False

        # The full URL is the server URL + stream key
        full_rtmp_url = f"{server_url}/{stream_key}"
        command = [
            "ffmpeg",
            "-stream_loop", "-1",
            "-i", video_path,
            "-vcodec", "libx264",
            "-b:v", "10M",
            "-acodec", "aac",
            "-b:a", "128k",
            "-f", "flv",
            full_rtmp_url,
        ]

        try:
            self.streaming_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            self.log_message(f"Streaming started with PID: {self.streaming_process.pid}")

            # Starts the thread to read ffmpeg output
            thread = threading.Thread(
                target=self._stream_ffmpeg_output, 
                args=(self.streaming_process,),
                daemon=True
            )
            thread.start()

        except FileNotFoundError:
            self.log_message("[ERROR] ffmpeg not found. Check if it's installed and in PATH.")
            self.query_one("#start", Button).disabled = False
            self.query_one("#stop", Button).disabled = True
        except Exception as e:
            self.log_message(f"[ERROR] Failed to start ffmpeg: {e}")
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
            self.log_message("Stopping stream...")
            self.streaming_process.terminate()
            try:
                self.streaming_process.wait(timeout=5)
                self.log_message("Stream stopped successfully.")
            except subprocess.TimeoutExpired:
                self.log_message("ffmpeg did not respond, forcing termination.")
                self.streaming_process.kill()
                self.log_message("Stream forced to stop.")
            self.streaming_process = None
        else:
            self.log_message("No active stream to stop.")


if __name__ == "__main__":
    app = TeleStreamApp()
    app.run()
