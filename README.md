# SuperLibraryMachine (Experimental)

This codebase is experimental. The steps below have been validated only on macOS 26 with Apple Silicon and assume a clean machine without Homebrew or pyenv.

## Quick Start (Web Server)

Run each command exactly as shown from the project root.

1. Install Python 3.12 using the official package:
   ```zsh
   curl -LO https://www.python.org/ftp/python/3.12.7/python-3.12.7-macos11.pkg
   sudo installer -pkg python-3.12.7-macos11.pkg -target /
   ```
2. Create a virtual environment with that interpreter:
   ```zsh
   /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m venv .venv
   ```
3. Activate the environment and upgrade pip:
   ```zsh
   source .venv/bin/activate
   python -m pip install --upgrade pip
   ```
4. Install project dependencies:
   ```zsh
   python -m pip install -r requirements.txt
   ```
5. Provide your OpenAI API key (optional now, required before the first query):
   ```zsh
   export OPENAI_API_KEY=sk-your-key-here
   ```
6. Start the web server:
   ```zsh
   python web/app.py
   ```
7. Open `http://localhost:7860` in a browser. If you did not export the key, use the Settings panel in the UI to save it.

## Optional Desktop Shell

Use the same virtual environment created above (keep `.venv` activated).

1. Install desktop-specific dependencies:
   ```zsh
   python -m pip install -r requirements-mac-desktop.txt
   ```
2. Launch the desktop shell:
   ```zsh
   python mac_app/launcher.py
   ```

The launcher wraps the Flask app in a native window and stores configuration under `~/Library/Application Support/SuperLibraryMachine/`.

## Additional Notes

- Python 3.13 and newer are not supported because the current `faiss-cpu` wheels depend on `numpy<2.0`.
- Set `RAG_DB_ROOT=/path/to/databases` before launching if you need to point at a different database directory.
- Desktop packaging scripts (`mac_app/build_app.sh`, `windows_app/build_exe.ps1`) assume you already followed the commands above and are using the same environment.
