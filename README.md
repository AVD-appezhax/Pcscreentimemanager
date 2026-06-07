# PC Screen Time Manager

PC Screen Time Manager is a small Windows study app that blocks distracting apps and custom websites while a focus timer is active.

## What it does

- Closes blocked apps during study time.
- Blocks custom websites by adding temporary entries to the Windows hosts file.
- Starts with broader default blocks for social media, streaming, gaming, shopping, and entertainment sites.
- Keeps YouTube out of the default block list so study videos remain available.
- Suggests distracting apps by scanning common PC app folders, Steam libraries, and Epic Games installs for `.exe` files.
- Ignores wallpaper/background tools while scanning.
- Lets you save the edited scanned app list so it loads next time.
- Adds an editable preset list of distracting websites.
- Supports a manual `Take break now` button during an active session, with a 30-second wait before the break starts and a 10-minute cap.
- Supports emergency exit after a 15-second wait.
- Uses a dark desktop UI.
- Does not hide itself, install a service, or survive reboot as a lock.
- Adds a transparent Windows RunOnce cleanup entry only while website blocking is active, so a forced restart can remove temporary hosts-file blocks.

## Run it

Use `run_studylock.bat` for app-only blocking.

Use `run_as_admin.bat` for whole-device website blocking. Windows will show a UAC prompt because editing the hosts file requires admin access.

## Notes

- App blocking works for normal user processes by executable name, such as `discord.exe` or `steam.exe`.
- Website blocking works best with domains like `tiktok.com`, `instagram.com`, or `reddit.com`.
- The PC scan is a suggestion tool. It looks in common app folders and game libraries, then adds likely distracting executables to the editable app list.
- After scanning, edit the app list and click `Save app list` to keep it for future sessions.
- Breaks are never scheduled automatically. Request one whenever you need it during an active session; blocks stay active for 30 seconds, then the break starts and ends automatically after the selected break length, up to 10 minutes.
- The website suggestions are presets because Windows does not keep a reliable list of every distracting site you visit.
- Some apps and browsers cache DNS. StudyLock flushes DNS when website blocks are applied or restored, but already-open pages may need to be refreshed.
- If something goes wrong with website blocking, run StudyLock as admin and click `Restore website blocks`.

## Test it

Run `py -3 -m unittest discover -s tests -v` from this folder.
