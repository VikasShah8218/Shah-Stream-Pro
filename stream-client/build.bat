@echo off
echo Cleaning old builds...
rmdir /s /q build
rmdir /s /q dist

echo Building Shah-Stream with PyInstaller...
pyinstaller --clean --noconfirm --onefile --windowed --name stream_v1.1 ^
    --icon "assests/img/shah-logo.ico" ^
    --add-data "ui/styles;stream-client/ui/styles" ^
    --add-data "assests;stream-client/assests" ^
    main.py

echo Build complete! Your executable is in the 'dist' folder.
pause
