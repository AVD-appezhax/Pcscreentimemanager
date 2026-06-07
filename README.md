# PC Screen Time Manager

PC Screen Time Manager is a small Windows study app that blocks distracting apps and custom websites while a focus timer is active.

## What it does

- Closes blocked apps during study time.
- Blocks custom websites by adding temporary entries to the Windows hosts file.
- Suggests distracting apps by scanning common PC app folders for `.exe` files.
- Adds an editable preset list of distracting websites.
- Supports manual breaks that you choose during the session, capped at 10 minutes.
- Supports emergency exit after a 15-second wait.
- Does not hide itself, install a service, or survive reboot as a lock.
- Adds a transparent Windows RunOnce cleanup entry only while website blocking is active, so a forced restart can remove temporary hosts-file blocks.

## Run it

Use `run_studylock.bat` for app-only blocking.

Use `run_as_admin.bat` for whole-device website blocking. Windows will show a UAC prompt because editing the hosts file requires admin access.

## Notes

- App blocking works for normal user processes by executable name, such as `discord.exe` or `steam.exe`.
- Website blocking works best with domains like `youtube.com`, `tiktok.com`, or `reddit.com`.
- The PC scan is a suggestion tool. It looks in common app folders and adds likely distracting executables to the editable app list.
- The website suggestions are presets because Windows does not keep a reliable list of every distracting site you visit.
- Some apps and browsers cache DNS. StudyLock flushes DNS when website blocks are applied or restored, but already-open pages may need to be refreshed.
- If something goes wrong with website blocking, run StudyLock as admin and click `Restore website blocks`.
