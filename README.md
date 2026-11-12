
Phone Screen Guard
A Windows desktop app that displays a black overlay when its webcam detects the selected trigger. Webcam frames are processed locally. The app starts at sign-in for the Windows account that installs it.

Choose an installer
Package	Trigger
PhoneScreenGuard-01-Phone-Only.zip	Phone detection
PhoneScreenGuard-02-Phone-and-Shutter.zip	Phone detection and shutter-like camera feed changes
PhoneScreenGuard-03-Phone-Shutter-and-Cover.zip	Phone detection, shutter-like changes, and low-detail lens covers
1. Check Python on Windows
Requirements are Windows 10 or 11 (x64), a working webcam, and 64-bit Python 3.12. Internet access is needed for the initial dependency and model downloads.

Open a fresh Command Prompt (CMD) and run:

python -c "import platform, struct, sys; print(sys.version.split()[0], struct.calcsize('P') * 8, platform.machine())"
Expected output looks like 3.12.10 64 AMD64. If python is unavailable or selects a different version, try the Python Launcher:

py -3.12 -c "import platform, struct, sys; print(sys.version.split()[0], struct.calcsize('P') * 8, platform.machine())"
If neither command finds Python 3.12 x64, install it and reopen CMD. If the Python installer offers Add python.exe to PATH, enable it. Either command working with the expected version is enough. Python downloads for Windows

2. Download and extract one installer
Click one ZIP in the table above and download it from GitHub.

In File Explorer, right-click the ZIP and select Extract All.

Open the extracted folder. It contains Install.cmd, Uninstall.cmd, guard.pyw and START-HERE.txt.

Install one mode per Windows account. To switch modes, exit the running app from the system tray first.

3. Run the installer
Double-click Install.cmd as the Windows user who will run the app. Administrator rights are unnecessary. To run the same setup from CMD, open the extracted folder in File Explorer, type cmd in the address bar and press Enter. Then run:

Install.cmd
The installer sets up a Python virtual environment under %USERPROFILE%\PhoneScreenGuard, installs dependencies, downloads the YOLO model, and creates a startup entry for the current user. Keep the window open until Setup complete appears.

4. Verify monitoring and automatic startup
Open the ^ system tray menu near the Windows clock and hover over the app icon. Confirm your mode number and Monitoring.

Hold a phone in view of the webcam. Test the shutter in Modes 2 and 3, and cover the entire lens with your palm in Mode 3.

Remove the phone or uncover the lens. The screen should return after about two seconds of clear conditions.

Sign out and sign in again to check that the app starts automatically. It works offline after the first successful setup.

Press Ctrl + Shift + F12 to pause or resume monitoring, including when the overlay is visible.

Troubleshooting
The tray icon is missing
Open a normal CMD under the same Windows account and run:

"%USERPROFILE%\PhoneScreenGuard\venv\Scripts\python.exe" "%USERPROFILE%\PhoneScreenGuard\guard.pyw"
If the app starts, keep this CMD window open during the test. To inspect the app log or open the current user's Startup folder, run:

notepad "%USERPROFILE%\PhoneScreenGuard\guard.log"
explorer shell:startup
The Startup folder should contain PhoneScreenGuard.cmd. If camera access fails, check Settings → Privacy & security → Camera → Let desktop apps access your camera and close other apps using the webcam.

The screen goes black in low light
Modes 2 and 3 use the webcam feed to infer shutter closure. A dark, uniform or unavailable feed can trigger either mode, including when an object covers the lens. Mode 3 also checks for extremely blurred, low-detail images. Partial covers and objects that leave visible detail may be missed.

Uninstall
Exit Phone Screen Guard from the system tray. Open CMD in the extracted installer folder as described above and run:

Uninstall.cmd
The script removes the app folder and startup entry for the current user.

Review the dependency and model terms for your intended use or redistribution. Ultralytics licensing

⋮⋮⋮⋮



