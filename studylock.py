import ctypes
import json
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.parse import urlparse


APP_NAME = "StudyLock"
CONFIG_PATH = Path(__file__).with_name("studylock_config.json")
HOSTS_PATH = Path(os.environ.get("SystemRoot", r"C:\Windows")) / r"System32\drivers\etc\hosts"
RUNONCE_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce"
HOSTS_BEGIN = "# STUDYLOCK-BEGIN"
HOSTS_END = "# STUDYLOCK-END"
MAX_BREAK_MINUTES = 10
SITE_PACK_VERSION = 2

DISTRACTING_APP_KEYWORDS = {
    "among us",
    "amongus",
    "apex",
    "battle.net",
    "battlenet",
    "baldur",
    "blizzard",
    "cod",
    "counter-strike",
    "counterstrike",
    "cs2",
    "csgo",
    "cyberpunk",
    "deadbydaylight",
    "destiny",
    "discord",
    "dota",
    "ea app",
    "eldenring",
    "epic",
    "facebook",
    "fallguys",
    "fifa",
    "finalfantasy",
    "footballmanager",
    "fortnite",
    "forza",
    "genshin",
    "gog",
    "gta",
    "gta5",
    "halo",
    "hearthstone",
    "honkai",
    "instagram",
    "league",
    "leagueclient",
    "lolclient",
    "minecraft",
    "netflix",
    "osu",
    "origin",
    "palworld",
    "prime video",
    "pubg",
    "rdr2",
    "reddit",
    "riot",
    "roblox",
    "rocketleague",
    "snapchat",
    "spotify",
    "starrail",
    "stardew",
    "steam",
    "terraria",
    "telegram",
    "tiktok",
    "twitch",
    "ubisoft",
    "valorant",
    "warframe",
    "warzone",
    "xbox",
}

DEFAULT_BLOCKED_SITES = [
    "tiktok.com",
    "instagram.com",
    "x.com",
    "twitter.com",
    "threads.net",
    "reddit.com",
    "twitch.tv",
    "kick.com",
    "facebook.com",
    "messenger.com",
    "netflix.com",
    "primevideo.com",
    "disneyplus.com",
    "hulu.com",
    "max.com",
    "crunchyroll.com",
    "funimation.com",
    "9gag.com",
    "buzzfeed.com",
    "pinterest.com",
    "tumblr.com",
    "snapchat.com",
    "discord.com",
    "discord.gg",
    "steampowered.com",
    "steamcommunity.com",
    "epicgames.com",
    "store.epicgames.com",
    "battle.net",
    "ea.com",
    "ubisoft.com",
    "riotgames.com",
    "roblox.com",
    "minecraft.net",
    "xbox.com",
    "playstation.com",
    "ign.com",
    "gamespot.com",
    "polygon.com",
    "kotaku.com",
    "twitchtracker.com",
    "amazon.com",
    "ebay.com",
    "etsy.com",
    "temu.com",
    "shein.com",
]

WEBSITE_PRESETS = DEFAULT_BLOCKED_SITES

IGNORED_EXE_FRAGMENTS = {
    "adpcmencode",
    "anticheat",
    "bootstrapper",
    "codecoverage",
    "codegen",
    "crash",
    "diagnostic",
    "driver",
    "dxsetup",
    "eac",
    "frcode",
    "gamesense",
    "ggtablemigrations",
    "gpgtar",
    "helper",
    "inject",
    "install",
    "launcherpatcher",
    "monitor",
    "overlay",
    "redist",
    "redownload",
    "reporter",
    "resourcecompiler",
    "prelauncher",
    "service",
    "setup",
    "sysinfo",
    "uninstall",
    "updater",
    "util",
    "wallpaper",
    "webhelper",
}

IGNORED_EXE_NAMES = {
    "launcher.exe",
    "x64launcher.exe",
    "x86launcher.exe",
}

ALWAYS_ALLOWED_SITES = {
    "youtube.com",
    "youtu.be",
}


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def normalize_app_name(value: str) -> str:
    value = value.strip().strip('"')
    if not value:
        return ""
    name = Path(value).name
    if "." not in name:
        name = f"{name}.exe"
    return name.lower()


def normalize_domain(value: str) -> str:
    value = value.strip().lower()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    host = parsed.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host.strip(".")


def split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def unique_sorted(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def merge_text(text: tk.Text, values: list[str]) -> None:
    current = split_lines(text.get("1.0", "end"))
    merged = unique_sorted(current + values)
    text.delete("1.0", "end")
    text.insert("1.0", "\n".join(merged))


def is_ignored_exe(filename: str) -> bool:
    lower_filename = normalize_app_name(filename)
    return lower_filename in IGNORED_EXE_NAMES or any(fragment in lower_filename for fragment in IGNORED_EXE_FRAGMENTS)


def add_exe_candidate(matches: set[str], filename: str) -> None:
    lower_filename = normalize_app_name(filename)
    if not lower_filename.endswith(".exe") or is_ignored_exe(lower_filename):
        return
    matches.add(lower_filename)


def quoted_value(text: str, key: str) -> str:
    match = re.search(rf'"{re.escape(key)}"\s+"([^"]+)"', text, flags=re.IGNORECASE)
    return match.group(1).replace("\\\\", "\\") if match else ""


def steam_roots() -> list[Path]:
    roots = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Steam",
        Path(os.environ.get("ProgramFiles", "")) / "Steam",
    ]
    appdata = os.environ.get("LOCALAPPDATA", "")
    if appdata:
        roots.append(Path(appdata) / "Steam")
    return [root for root in roots if root.exists()]


def steam_libraries() -> list[Path]:
    libraries: set[Path] = set()
    for root in steam_roots():
        libraries.add(root)
        library_file = root / "steamapps" / "libraryfolders.vdf"
        if not library_file.exists():
            continue
        text = library_file.read_text(encoding="utf-8", errors="ignore")
        for path_text in re.findall(r'"path"\s+"([^"]+)"', text, flags=re.IGNORECASE):
            path = Path(path_text.replace("\\\\", "\\"))
            if path.exists():
                libraries.add(path)
    return sorted(libraries)


def add_game_folder_exes(matches: set[str], folder: Path, deadline: float, max_depth: int = 2) -> None:
    if not folder.exists() or time.monotonic() > deadline:
        return
    base_depth = len(folder.parts)
    for dirpath, dirnames, filenames in os.walk(folder):
        if time.monotonic() > deadline:
            return
        current_depth = len(Path(dirpath).parts) - base_depth
        if current_depth >= max_depth:
            dirnames[:] = []
        dirnames[:] = [
            name
            for name in dirnames
            if name.lower()
            not in {
                "_commonredist",
                "cache",
                "engine",
                "extras",
                "logs",
                "redist",
                "support",
                "temp",
                "tmp",
            }
        ]
        for filename in filenames:
            if filename.lower().endswith(".exe"):
                add_exe_candidate(matches, filename)


def add_steam_games(matches: set[str], deadline: float) -> None:
    for library in steam_libraries():
        steamapps = library / "steamapps"
        common = steamapps / "common"
        if not steamapps.exists() or time.monotonic() > deadline:
            continue
        for manifest in steamapps.glob("appmanifest_*.acf"):
            text = manifest.read_text(encoding="utf-8", errors="ignore")
            install_dir = quoted_value(text, "installdir")
            if install_dir:
                add_game_folder_exes(matches, common / install_dir, deadline)


def add_epic_games(matches: set[str], deadline: float) -> None:
    program_data = os.environ.get("ProgramData", r"C:\ProgramData")
    manifests = Path(program_data) / "Epic" / "EpicGamesLauncher" / "Data" / "Manifests"
    if not manifests.exists():
        return
    for manifest in manifests.glob("*.item"):
        if time.monotonic() > deadline:
            return
        try:
            data = json.loads(manifest.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            continue
        launch_exe = data.get("LaunchExecutable", "")
        if launch_exe:
            add_exe_candidate(matches, Path(launch_exe).name)
        install_location = data.get("InstallLocation", "")
        if install_location:
            add_game_folder_exes(matches, Path(install_location), deadline)


def scan_distracting_exes() -> list[str]:
    drive_roots = [f"{letter}:\\" for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{letter}:\\").exists()]
    roots = unique_sorted(
        drive_roots
        + [
            os.environ.get("ProgramFiles", ""),
            os.environ.get("ProgramFiles(x86)", ""),
            os.environ.get("LOCALAPPDATA", ""),
            os.environ.get("APPDATA", ""),
            str(Path.home() / "Desktop"),
            str(Path.home() / "Downloads"),
        ]
    )
    matches: set[str] = set()
    deadline = time.monotonic() + 90
    add_steam_games(matches, deadline)
    add_epic_games(matches, deadline)

    for root in roots:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root_path):
            if time.monotonic() > deadline:
                return sorted(matches)
            dirnames[:] = [
                name
                for name in dirnames
                if name.lower()
                not in {
                    "$recycle.bin",
                    ".git",
                    "cache",
                    "logs",
                    "microsoft",
                    "node_modules",
                    "temp",
                    "tmp",
                    "windows",
                    "windowsapps",
                    "winsxs",
                }
            ]
            for filename in filenames:
                lower_filename = filename.lower()
                if not lower_filename.endswith(".exe"):
                    continue
                if is_ignored_exe(lower_filename):
                    continue
                if any(keyword in lower_filename for keyword in DISTRACTING_APP_KEYWORDS):
                    matches.add(normalize_app_name(filename))

    return sorted(matches)


@dataclass
class StudyConfig:
    duration_minutes: int = 60
    max_break_minutes: int = MAX_BREAK_MINUTES
    blocked_apps: list[str] = field(default_factory=lambda: ["discord.exe", "steam.exe"])
    blocked_sites: list[str] = field(default_factory=lambda: DEFAULT_BLOCKED_SITES.copy())
    site_pack_version: int = SITE_PACK_VERSION

    @classmethod
    def load(cls) -> "StudyConfig":
        if not CONFIG_PATH.exists():
            return cls()
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            site_pack_version = int(data.get("site_pack_version", 0))
            loaded_sites = [normalize_domain(x) for x in data.get("blocked_sites", []) if normalize_domain(x)]
            if site_pack_version < SITE_PACK_VERSION:
                loaded_sites = DEFAULT_BLOCKED_SITES + loaded_sites
            return cls(
                duration_minutes=max(1, int(data.get("duration_minutes", 60))),
                max_break_minutes=min(MAX_BREAK_MINUTES, max(1, int(data.get("max_break_minutes", data.get("break_length_minutes", MAX_BREAK_MINUTES))))),
                blocked_apps=[normalize_app_name(x) for x in data.get("blocked_apps", []) if normalize_app_name(x)],
                blocked_sites=unique_sorted([site for site in loaded_sites if site not in ALWAYS_ALLOWED_SITES]),
                site_pack_version=SITE_PACK_VERSION,
            )
        except Exception:
            return cls()

    def save(self) -> None:
        CONFIG_PATH.write_text(
            json.dumps(
                {
                    "duration_minutes": self.duration_minutes,
                    "max_break_minutes": self.max_break_minutes,
                    "blocked_apps": self.blocked_apps,
                    "blocked_sites": self.blocked_sites,
                    "site_pack_version": self.site_pack_version,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


class HostsBlocker:
    def __init__(self, domains: list[str]) -> None:
        self.domains = sorted({domain for domain in domains if domain})

    def apply(self, unlock_at: datetime) -> None:
        if not self.domains:
            return
        current = self._without_studylock_block()
        entries = [HOSTS_BEGIN, f"# unlock_at={unlock_at.isoformat(timespec='seconds')}"]
        for domain in self.domains:
            entries.append(f"0.0.0.0 {domain}")
            entries.append(f"0.0.0.0 www.{domain}")
        entries.append(HOSTS_END)
        HOSTS_PATH.write_text(current.rstrip() + "\n\n" + "\n".join(entries) + "\n", encoding="utf-8")
        self._flush_dns()
        self._register_restart_cleanup()

    def restore(self) -> None:
        if not HOSTS_PATH.exists():
            return
        HOSTS_PATH.write_text(self._without_studylock_block().rstrip() + "\n", encoding="utf-8")
        self._flush_dns()
        self._clear_restart_cleanup()

    def _without_studylock_block(self) -> str:
        text = HOSTS_PATH.read_text(encoding="utf-8", errors="ignore") if HOSTS_PATH.exists() else ""
        output: list[str] = []
        skipping = False
        for line in text.splitlines():
            if line.strip() == HOSTS_BEGIN:
                skipping = True
                continue
            if line.strip() == HOSTS_END:
                skipping = False
                continue
            if not skipping:
                output.append(line)
        return "\n".join(output)

    def _flush_dns(self) -> None:
        subprocess.run(["ipconfig", "/flushdns"], creationflags=subprocess.CREATE_NO_WINDOW, check=False)

    def _register_restart_cleanup(self) -> None:
        command = f'"{sys.executable}" "{Path(__file__).resolve()}" --cleanup'
        subprocess.run(
            ["reg", "add", RUNONCE_KEY, "/v", APP_NAME, "/t", "REG_SZ", "/d", command, "/f"],
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )

    def _clear_restart_cleanup(self) -> None:
        subprocess.run(
            ["reg", "delete", RUNONCE_KEY, "/v", APP_NAME, "/f"],
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )


class ProcessBlocker:
    def __init__(self, apps: list[str]) -> None:
        self.apps = sorted({normalize_app_name(app) for app in apps if normalize_app_name(app)})

    def enforce(self) -> None:
        for app in self.apps:
            subprocess.run(
                ["taskkill", "/F", "/IM", app],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=False,
            )


class StudyLockApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("880x700")
        self.minsize(780, 620)

        self.config_data = StudyConfig.load()
        self.session_active = False
        self.session_stop = threading.Event()
        self.unlock_at: datetime | None = None
        self.break_until: datetime | None = None
        self.hosts_paused = False
        self.hosts_blocker: HostsBlocker | None = None
        self.process_blocker: ProcessBlocker | None = None

        self._build_ui()
        self._load_form()
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text="StudyLock", font=("Segoe UI", 22, "bold")).pack(side="left")
        admin_text = "Admin: website blocking enabled" if is_admin() else "Not admin: app blocking only"
        self.admin_label = ttk.Label(header, text=admin_text)
        self.admin_label.pack(side="right")

        settings = ttk.LabelFrame(root, text="Session")
        settings.pack(fill="x", pady=(16, 10))
        settings.columnconfigure(0, weight=1)
        settings.columnconfigure(1, weight=1)

        self.duration_var = tk.IntVar(value=60)
        self.max_break_var = tk.IntVar(value=MAX_BREAK_MINUTES)
        self._number_field(settings, "Study minutes", self.duration_var, 0, 1, 480)
        self._number_field(settings, "Max break minutes", self.max_break_var, 1, 1, MAX_BREAK_MINUTES)

        suggestion_bar = ttk.Frame(root)
        suggestion_bar.pack(fill="x", pady=(0, 8))
        self.scan_button = ttk.Button(suggestion_bar, text="Scan PC for distracting apps", command=self._scan_apps)
        self.scan_button.pack(side="left")
        ttk.Button(suggestion_bar, text="Add suggested websites", command=self._add_site_presets).pack(side="left", padx=8)
        self.suggestion_var = tk.StringVar(value="Suggestions are editable before you start.")
        ttk.Label(suggestion_bar, textvariable=self.suggestion_var).pack(side="left", padx=8)

        lists = ttk.Frame(root)
        lists.pack(fill="both", expand=True, pady=8)
        lists.columnconfigure(0, weight=1)
        lists.columnconfigure(1, weight=1)
        lists.rowconfigure(1, weight=1)

        ttk.Label(lists, text="Blocked apps, one per line").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Label(lists, text="Blocked websites, one per line").grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.apps_text = tk.Text(lists, height=14, wrap="none", font=("Consolas", 10))
        self.apps_text.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(4, 0))
        self.sites_text = tk.Text(lists, height=14, wrap="none", font=("Consolas", 10))
        self.sites_text.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(4, 0))

        status_box = ttk.LabelFrame(root, text="Status")
        status_box.pack(fill="x", pady=(8, 10))
        self.status_var = tk.StringVar(value="Ready")
        self.timer_var = tk.StringVar(value="No active study session")
        ttk.Label(status_box, textvariable=self.status_var).pack(anchor="w", padx=10, pady=(8, 2))
        ttk.Label(status_box, textvariable=self.timer_var, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(0, 8))

        actions = ttk.Frame(root)
        actions.pack(fill="x")
        self.start_button = ttk.Button(actions, text="Start study session", command=self._start_session)
        self.start_button.pack(side="left")
        self.break_button = ttk.Button(actions, text="Start break", command=self._start_break, state="disabled")
        self.break_button.pack(side="left", padx=8)
        self.resume_button = ttk.Button(actions, text="Resume now", command=self._resume_from_break, state="disabled")
        self.resume_button.pack(side="left")
        ttk.Button(actions, text="Save settings", command=self._save_form).pack(side="left", padx=8)
        self.exit_button = ttk.Button(actions, text="Emergency exit", command=self._emergency_exit, state="disabled")
        self.exit_button.pack(side="right")
        ttk.Button(actions, text="Restore website blocks", command=self._manual_restore).pack(side="right", padx=8)

    def _number_field(self, parent: ttk.Frame, label: str, variable: tk.IntVar, column: int, from_: int, to: int) -> None:
        frame = ttk.Frame(parent, padding=10)
        frame.grid(row=0, column=column, sticky="ew")
        ttk.Label(frame, text=label).pack(anchor="w")
        spin = ttk.Spinbox(frame, from_=from_, to=to, textvariable=variable, width=8)
        spin.pack(anchor="w", pady=(4, 0))

    def _load_form(self) -> None:
        self.duration_var.set(self.config_data.duration_minutes)
        self.max_break_var.set(self.config_data.max_break_minutes)
        self.apps_text.delete("1.0", "end")
        self.apps_text.insert("1.0", "\n".join(self.config_data.blocked_apps))
        self.sites_text.delete("1.0", "end")
        self.sites_text.insert("1.0", "\n".join(self.config_data.blocked_sites))

    def _read_form(self) -> StudyConfig:
        blocked_apps = [normalize_app_name(x) for x in split_lines(self.apps_text.get("1.0", "end"))]
        blocked_sites = [normalize_domain(x) for x in split_lines(self.sites_text.get("1.0", "end"))]
        return StudyConfig(
            duration_minutes=max(1, int(self.duration_var.get())),
            max_break_minutes=min(MAX_BREAK_MINUTES, max(1, int(self.max_break_var.get()))),
            blocked_apps=unique_sorted(blocked_apps),
            blocked_sites=unique_sorted([site for site in blocked_sites if site not in ALWAYS_ALLOWED_SITES]),
            site_pack_version=SITE_PACK_VERSION,
        )

    def _save_form(self) -> None:
        self.config_data = self._read_form()
        self.config_data.save()
        self.status_var.set("Settings saved")

    def _scan_apps(self) -> None:
        self.scan_button.configure(state="disabled")
        self.suggestion_var.set("Scanning common app folders for distracting .exe files...")
        threading.Thread(target=self._scan_apps_worker, daemon=True).start()

    def _scan_apps_worker(self) -> None:
        try:
            matches = scan_distracting_exes()
            self.after(0, lambda: self._finish_app_scan(matches))
        except Exception as exc:
            self.after(0, lambda: self._scan_failed(exc))

    def _finish_app_scan(self, matches: list[str]) -> None:
        merge_text(self.apps_text, matches)
        self.scan_button.configure(state="normal")
        self.suggestion_var.set(f"Added {len(matches)} suggested app entries. Edit the list before starting.")

    def _scan_failed(self, exc: Exception) -> None:
        self.scan_button.configure(state="normal")
        self.suggestion_var.set(f"Scan failed: {exc}")

    def _add_site_presets(self) -> None:
        merge_text(self.sites_text, WEBSITE_PRESETS)
        self.suggestion_var.set(f"Added {len(WEBSITE_PRESETS)} suggested websites. Edit the list before starting.")

    def _start_session(self) -> None:
        if self.session_active:
            return
        try:
            self._save_form()
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not save settings:\n{exc}")
            return

        if self.config_data.blocked_sites and not is_admin():
            messagebox.showwarning(
                APP_NAME,
                "Website blocking needs admin access. Start this app as administrator to block websites for the whole PC.",
            )

        now = datetime.now()
        self.unlock_at = now + timedelta(minutes=self.config_data.duration_minutes)
        self.break_until = None
        self.hosts_paused = False
        self.session_stop.clear()
        self.session_active = True
        self._set_editing_enabled(False)

        self.hosts_blocker = HostsBlocker(self.config_data.blocked_sites)
        self.process_blocker = ProcessBlocker(self.config_data.blocked_apps)

        if is_admin():
            try:
                self.hosts_blocker.apply(self.unlock_at)
            except Exception as exc:
                messagebox.showerror(APP_NAME, f"Could not apply website blocks:\n{exc}")

        worker = threading.Thread(target=self._session_worker, daemon=True)
        worker.start()
        self._tick_ui()

    def _set_editing_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.start_button.configure(state=state)
        self.scan_button.configure(state=state)
        self.apps_text.configure(state=state)
        self.sites_text.configure(state=state)
        self.break_button.configure(state="disabled" if enabled else "normal")
        self.resume_button.configure(state="disabled")
        self.exit_button.configure(state="disabled" if enabled else "normal")

    def _session_worker(self) -> None:
        while not self.session_stop.is_set():
            now = datetime.now()
            if self.unlock_at and now >= self.unlock_at:
                self.after(0, self._finish_session)
                return

            in_break = self.break_until is not None and now < self.break_until
            if self.break_until and now >= self.break_until:
                self.after(0, self._resume_from_break)
                in_break = False

            if in_break:
                if self.hosts_blocker and is_admin() and not self.hosts_paused:
                    self.hosts_blocker.restore()
                    self.hosts_paused = True
            else:
                if self.hosts_blocker and is_admin() and self.hosts_paused and self.unlock_at:
                    self.hosts_blocker.apply(self.unlock_at)
                    self.hosts_paused = False
                if self.process_blocker:
                    self.process_blocker.enforce()

            time.sleep(3)

    def _start_break(self) -> None:
        if not self.session_active:
            return
        max_minutes = min(MAX_BREAK_MINUTES, max(1, int(self.max_break_var.get())))
        self.break_until = datetime.now() + timedelta(minutes=max_minutes)
        self.break_button.configure(state="disabled")
        self.resume_button.configure(state="normal")
        self.status_var.set(f"Break active for up to {max_minutes} minutes.")

    def _resume_from_break(self) -> None:
        if not self.session_active:
            return
        self.break_until = None
        self.break_button.configure(state="normal")
        self.resume_button.configure(state="disabled")
        if self.hosts_blocker and is_admin() and self.hosts_paused and self.unlock_at:
            try:
                self.hosts_blocker.apply(self.unlock_at)
                self.hosts_paused = False
            except Exception as exc:
                messagebox.showwarning(APP_NAME, f"Could not reapply website blocks:\n{exc}")

    def _tick_ui(self) -> None:
        if not self.session_active or not self.unlock_at:
            return
        now = datetime.now()
        remaining = max(0, int((self.unlock_at - now).total_seconds()))
        mins, secs = divmod(remaining, 60)

        if self.break_until and now < self.break_until:
            break_remaining = max(0, int((self.break_until - now).total_seconds()))
            bmins, bsecs = divmod(break_remaining, 60)
            self.status_var.set("Break active. Blocks resume automatically when the break ends.")
            self.timer_var.set(f"Unlocks in {mins:02d}:{secs:02d}. Break left {bmins:02d}:{bsecs:02d}.")
        else:
            self.status_var.set("Study lock active. Use Emergency exit if you genuinely need out.")
            self.timer_var.set(f"Unlocks in {mins:02d}:{secs:02d}.")

        self.after(1000, self._tick_ui)

    def _finish_session(self) -> None:
        if not self.session_active:
            return
        self.session_stop.set()
        self._restore_blocks()
        self.session_active = False
        self._set_editing_enabled(True)
        self.status_var.set("Session complete")
        self.timer_var.set("Unlocked")

    def _restore_blocks(self) -> None:
        if self.hosts_blocker and is_admin():
            try:
                self.hosts_blocker.restore()
                self.hosts_paused = False
            except Exception as exc:
                messagebox.showwarning(APP_NAME, f"Website blocks could not be restored:\n{exc}")

    def _manual_restore(self) -> None:
        if not is_admin():
            messagebox.showinfo(APP_NAME, "Run as administrator to restore hosts-file website blocks.")
            return
        try:
            HostsBlocker([]).restore()
            self.status_var.set("Website blocks restored")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not restore website blocks:\n{exc}")

    def _emergency_exit(self) -> None:
        if not self.session_active:
            self.destroy()
            return
        dialog = EmergencyExitDialog(self)
        self.wait_window(dialog)
        if dialog.confirmed:
            self._finish_session()

    def _handle_close(self) -> None:
        if self.session_active:
            self._emergency_exit()
            return
        self.destroy()


class EmergencyExitDialog(tk.Toplevel):
    def __init__(self, parent: StudyLockApp) -> None:
        super().__init__(parent)
        self.title("Emergency exit")
        self.resizable(False, False)
        self.confirmed = False
        self.remaining = 15
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Emergency exit", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Wait 15 seconds before unlocking. Use this only when you really need access.",
            wraplength=360,
        ).pack(anchor="w", pady=(8, 12))
        self.countdown_var = tk.StringVar(value="Exit available in 15 seconds")
        ttk.Label(frame, textvariable=self.countdown_var, font=("Segoe UI", 11, "bold")).pack(anchor="w")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(16, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left")
        self.exit_now_button = ttk.Button(buttons, text="Exit now", command=self._confirm, state="disabled")
        self.exit_now_button.pack(side="right")
        self.after(1000, self._tick)

    def _tick(self) -> None:
        self.remaining -= 1
        if self.remaining <= 0:
            self.countdown_var.set("Exit is available")
            self.exit_now_button.configure(state="normal")
            return
        self.countdown_var.set(f"Exit available in {self.remaining} seconds")
        self.after(1000, self._tick)

    def _confirm(self) -> None:
        self.confirmed = True
        self.destroy()


def cleanup_hosts() -> None:
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{Path(__file__).resolve()}" --cleanup', None, 1)
        return
    HostsBlocker([]).restore()


def main() -> None:
    if "--cleanup" in sys.argv:
        cleanup_hosts()
        return
    app = StudyLockApp()
    app.mainloop()


if __name__ == "__main__":
    main()
