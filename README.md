# Phone Screen Guard

A Windows desktop app that displays a black overlay when its webcam detects the selected trigger. Webcam frames are processed locally. The app starts at sign-in for the Windows account that installs it.

## Choose an installer

| Package | Trigger |
| --- | --- |
| [PhoneScreenGuard-01-Phone-Only.zip](PhoneScreenGuard-01-Phone-Only.zip) | Phone detection |
| [PhoneScreenGuard-02-Phone-and-Shutter.zip](PhoneScreenGuard-02-Phone-and-Shutter.zip) | Phone detection and shutter-like camera feed changes |
| [PhoneScreenGuard-03-Phone-Shutter-and-Cover.zip](PhoneScreenGuard-03-Phone-Shutter-and-Cover.zip) | Phone detection, shutter-like changes, and low-detail lens covers |

## Install on Windows

1. Install 64-bit Python 3.12 on Windows 10 or 11 (x64).
2. Download and extract one installer ZIP. Open `START-HERE.txt` for the full guide.
3. Double-click `Install.cmd` as the user who will use the app. The first setup downloads the dependencies and detection model.
4. Check the system tray for Phone Screen Guard. Hover over the icon to confirm the mode and monitoring status, then test the selected triggers.

Install one mode per Windows account. To switch modes, exit the current app from the tray before running the other installer. The app works offline after setup. Use **Ctrl+Shift+F12** to pause or resume monitoring. To remove it, exit the app and run `Uninstall.cmd`.

Shutter and cover detection depend on what the webcam reports. Low light or interrupted camera feeds can trigger Modes 2 and 3. Some partial covers may be missed. Review the [Ultralytics licensing terms](https://www.ultralytics.com/license) for your intended use or redistribution.
