# Contributing Translations to TeleStream TUI

We welcome contributions to translate TeleStream TUI into various languages! Your help makes the application accessible to a wider audience.

This guide will walk you through the process of contributing new translations or improving existing ones.

## Getting Started

1.  **Fork the Repository**: Start by forking the [TeleStream TUI repository](https://github.com/jvlianodorneles/telestream-tui) to your GitHub account.
2.  **Clone Your Fork**: Clone your forked repository to your local machine:
    ```bash
    git clone https://github.com/YOUR_USERNAME/telestream-tui.git
    cd telestream-tui
    ```
3.  **Create a New Branch**: Create a new branch for your translation work:
    ```bash
    git checkout -b feature/add-language-xx
    # or for updates
    git checkout -b fix/update-language-xx
    ```
    Replace `xx` with the ISO 639-1 code for the language (e.g., `pt_BR`, `es`, `fr`).

## Translation Process

TeleStream TUI uses `gettext` for internationalization, managed by the `Babel` library.

### 1. Install Babel
If you haven't already, install Babel:
```bash
pip install Babel
```

### 2. Extract Translatable Strings (Generate `.pot` file)
This step creates or updates the template file (`messages.pot`) containing all strings marked for translation in the application.
```bash
pybabel extract -F babel.cfg -o locale/messages.pot .
```

### 3. Initialize or Update Language-Specific `.po` Files

*   **To initialize a new language (e.g., French `fr`):**
    ```bash
    pybabel init -i locale/messages.pot -d locale -l fr
    ```
    This will create `locale/fr/LC_MESSAGES/messages.po`.

*   **To update an existing language (e.g., Portuguese `pt_BR`) with new strings:**
    ```bash
    pybabel update -i locale/messages.pot -d locale -l pt_BR
    ```

### 4. Translate the `.po` File

This is the most important step. Open the generated `.po` file (e.g., `locale/fr/LC_MESSAGES/messages.po`) using a text editor or a dedicated PO editor like [Poedit](https://poedit.net/).

For each `msgid` (the original English string), you need to provide a `msgstr` (the translated string).

**Example:**
```po
msgid "Are you sure you want to quit?"
msgstr "Êtes-vous sûr de vouloir quitter ?"
```

**Important:**
*   **Do not leave `msgstr` empty.** If `msgstr` is empty, the application will display the original English `msgid`.
*   **Remove `#, fuzzy` tags.** If you see `#, fuzzy` above a `msgid`/`msgstr` pair, it means the translation might be outdated or needs review. After you've reviewed/corrected the translation, remove this line.
*   **Preserve placeholders.** If a string contains placeholders like `{variable_name}` (e.g., `[ERROR] File not found: {video_path}`), ensure these placeholders are included exactly as they are in the `msgid` within your `msgstr`.

### 5. Compile `.po` Files to `.mo` Files

After translating and saving your `.po` file, compile it into a `.mo` file. This is the binary format the application uses.

```bash
pybabel compile -d locale -l fr
```
    (Replace `fr` with your language code).

### 6. Test Your Translation Locally

Run the application with your new translation by setting the `LANG` environment variable:

```bash
LANG=fr_FR.UTF-8 python app.py
```
    (Replace `fr_FR.UTF-8` with the appropriate locale for your language, e.g., `es_ES.UTF-8`, `pt_BR.UTF-8`).

## Submitting Your Contribution

1.  **Add and Commit Your Changes**: Stage your changes (the `.po` and `.mo` files, and any new `locale` directories).
    ```bash
    git add locale/
    git commit -m "feat: Add French translation" # or "fix: Update Portuguese translation"
    ```
2.  **Push to Your Fork**: Push your branch to your forked repository on GitHub.
    ```bash
    git push origin feature/add-language-fr
    ```
3.  **Open a Pull Request**: Go to the original TeleStream TUI repository on GitHub and open a Pull Request from your branch to the `main` branch. Describe your changes clearly.

Thank you for helping to make TeleStream TUI accessible to everyone!