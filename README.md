# SuperLibraryMachine
An easy to use pipeline for setting up retrieval augmented generation of scientific text.

## Web Interface

The repository now bundles a simple Flask web app that can answer questions over any
processed RAG database (i.e. a folder containing `faiss_index.idx` and
`faiss_metadata.pkl`). A sample database, `Paper_DB_Sample`, is provided under
`exampleDBs/` and is used by default.

1. Create and activate a virtual environment (recommended).
2. Install dependencies: `pip install --upgrade pip && pip install -r requirements-mac.txt` (tested on macOS
   13+/Apple Silicon and Intel). The requirements file pins `numpy<2.0` so `faiss-cpu` avoids the
   `AttributeError: module 'numpy' has no attribute '_ARRAY_API'` crash seen with newer wheels.
3. Provide your OpenAI API key:
   - Command line: `export OPENAI_API_KEY=sk-...` before running the server, or
   - Desktop shell: launch it once and paste the key into the built-in Settings
     window (it is stored locally and reused).
4. (Optional) Point the app at a different database root:
   `export RAG_DB_ROOT=/path/to/your/databases`.
5. Start the server from the project root: `python web/app.py`.
6. Visit `http://localhost:7860`—the interface is open locally once the server starts.

If no databases are detected at startup, the UI will display guidance on where to place
them.

### Optional desktop shell

To run the site inside a lightweight desktop window instead of a browser:

1. Ensure the web dependencies above are installed (or let the desktop bundle pull them in automatically).
2. Install the optional desktop extras:
   - macOS: `pip install -r requirements-mac-desktop.txt`
   - Windows: `pip install -r requirements-windows-desktop.txt`
3. Launch the shell: `python mac_app/launcher.py`. The app works even without an API key;
   use the Settings menu (or floating button) whenever you are ready to add one.

The script spins up the Flask app in the background and opens a platform-native web view
that points at the local site. Set `SLM_HOST`/`SLM_PORT` to override the defaults. On
systems where the native menu is unavailable, a small “Settings” button appears in the
top-right corner of the window instead. API keys are cached under the OS-appropriate
configuration directory (for example,
`~/Library/Application Support/SuperLibraryMachine/config.json` on macOS and
`%APPDATA%\SuperLibraryMachine\config.json` on Windows).

#### Package for macOS (.app)

1. Inside the `rag` environment run `pip install pyinstaller` (already included in
   `requirements-mac-desktop.txt`).
2. Execute `bash mac_app/build_app.sh` from the project root (the script sets
   `PYINSTALLER_NO_CODESIGN=1` so PyInstaller skips its auto-sign step).
3. Move `dist/SuperLibraryMachine.app` into `/Applications` (or wherever you keep apps).
4. Double-click the app once to trust it, then pin it to the Dock for one-click launches.

#### Package for Windows (.exe)

1. From the same environment, install the desktop extras if you have not already:
   `pip install -r requirements-windows-desktop.txt`.
2. Open PowerShell in the project root and run `./windows_app/build_exe.ps1`.
3. The distributable lives under `dist\SuperLibraryMachine\SuperLibraryMachine.exe`; copy
   that folder anywhere you want to run the app.

The Windows bundle stores its configuration alongside other application data inside
`%APPDATA%\SuperLibraryMachine` so API keys persist across launches.

> Ensure your build environment also has the core web dependencies (Flask, OpenAI SDK,
> etc.) installed—e.g. `pip install -r requirements-mac.txt` on macOS or install the
> analogous packages individually on Windows—before running PyInstaller. Otherwise the
> packaged bundle cannot import them at runtime and will exit with a `ModuleNotFoundError`.

> If the build script reports `No module named PyInstaller`, reinstall the optional
> desktop requirements (`pip install -r requirements-mac-desktop.txt` on macOS or
> `pip install -r requirements-windows-desktop.txt` on Windows) inside the `rag`
> environment to pull in the packaging tools.

> Need a signed bundle? After building, run
> `codesign --force --deep --sign - --timestamp=none dist/SuperLibraryMachine.app`
> (or use a real signing identity) before moving it into `/Applications`.

> On Apple Silicon Macs, if `sentence-transformers` does not pull in a compatible
> PyTorch wheel automatically, install it manually with
> `pip install torch --index-url https://download.pytorch.org/whl/cpu` before rerunning
> `pip install -r requirements-mac.txt`.

> `faiss-cpu` wheels ship per-architecture. If pip still complains that no matching
> distribution is found, upgrade pip inside the environment (`pip install --upgrade pip`)
> and retry.
