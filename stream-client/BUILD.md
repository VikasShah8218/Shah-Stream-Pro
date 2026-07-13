# Building Shah-Stream into a single .exe

Shah-Stream ships as one self-contained Windows executable — Python, PyQt6, the
logo image and the theme are all packed inside `Shah-Stream.exe`. Packaging is
done with [PyInstaller](https://pyinstaller.org) using [`shah-stream.spec`](shah-stream.spec).

## Prerequisites

- **Windows, 64-bit Python 3.10+** (match your app's architecture).
- **64-bit VLC installed** on the build machine (python-vlc loads libVLC at runtime).
- The app's runtime deps **plus** the build tooling:

  ```powershell
  pip install -r requirements.txt -r requirements-build.txt
  ```

## Build

From the project root:

```powershell
pyinstaller --noconfirm --clean shah-stream.spec
```

Result: **`dist/Shah-Stream.exe`** — a single ~40 MB file. Double-click to run.
Intermediate files land in `build/` (safe to delete).

That's it. The logo (taskbar / title bar / About) and the dark theme are embedded
in the exe — no loose files to ship next to it.

## Important: libVLC at runtime

python-vlc does **not** contain VLC itself — it uses the machine's `libvlc.dll`.
So there are two ways to ship:

### Option A — require VLC on the target machine (default, recommended)

The exe from the command above expects **64-bit VLC** to be installed wherever it
runs. This keeps the exe small and is the simplest, most reliable option. If VLC
is missing, playback fails with a libVLC error while the UI still opens.

### Option B — fully standalone (bundle libVLC too)

To make an exe that runs with **no VLC installed**, bundle libVLC and its plugins:

1. Open [`shah-stream.spec`](shah-stream.spec) and **uncomment** the `VLC_DIR`
   block, pointing `VLC_DIR` at your 64-bit VLC install (default
   `C:\Program Files\VideoLAN\VLC`).
2. Rebuild: `pyinstaller --noconfirm --clean shah-stream.spec`.

The included runtime hook ([`tools/rthook_vlc.py`](tools/rthook_vlc.py)) then points
python-vlc at the bundled `libvlc.dll` and `plugins/` automatically. The exe grows
by ~120 MB but needs nothing installed. (VLC is LGPL/GPL — mind licensing when
redistributing it.)

## Regenerating the app icon

The exe icon is [`src/shah_stream/assests/img/shah-stream.ico`](src/shah_stream/assests/img/),
generated from the logo (composited onto a white rounded card so it reads on a
dark taskbar). If you change the logo, regenerate it:

```powershell
pip install pillow
python tools/make_icon.py
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| App opens but video won't play / libVLC error | Install 64-bit VLC (Option A), or build standalone (Option B). |
| Antivirus flags the exe | Common for unsigned PyInstaller one-file exes. Sign the exe, or ship the `--onedir` variant. UPX is already disabled to reduce this. |
| "Failed to execute script run" | Rebuild after `pip install -r requirements.txt`; ensure PyQt6 + python-vlc import cleanly first. |
| Missing logo/theme in the exe | Confirm `shah-stream.spec` `datas` paths exist; both are embedded by default. |

## Notes

- The build is **one-file, windowed** (no console). For debugging, set
  `console=True` in the spec to see tracebacks in a console window.
- 32-bit vs 64-bit must match across Python, PyQt6, VLC and the target machine.
