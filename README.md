**English** | [Polski](README.pl.md)

---

# SudoSync for Kodi

A lightweight background service add-on for Kodi that provides automatic, two-way synchronization of watch states, resume points, user ratings, and last-played timestamps across multiple Kodi instances in the same local network — without requiring an external MySQL/MariaDB server.

Synchronization relies on a shared network directory (SMB, NFS, or local share) and safe JSON-RPC API calls.

---

## Key Features

- **No Dedicated Database Required:** Uses a shared network path accessible by your devices (NAS, local PC, or network share).
- **Safe & Non-Destructive:** Interacts exclusively through Kodi's official JSON-RPC API. It never touches or locks internal SQLite files (`MyVideos*.db`) directly.
- **Robust Conflict Model:** Each synchronized field maintains its own timestamp and client version, preventing race conditions and feedback loops.
- **Optimized for Android TV & Streaming Devices:** A lightweight state diff engine handles platforms where Kodi occasionally fails to trigger `OnUpdate` or `OnStop` notifications.
- **Scraper & NFO Quarantine:** Newly scanned library items and NFO imports receive older internal versions to prevent accidental overwrites of existing shared playback progress.

---

## Synchronized Attributes

- Watch state & play count (watched / unwatched),
- Exact playback resume position,
- Last played timestamp,
- User ratings (1–10).

---

## Installation & Setup

1. **Download:**
   - Go to the **Releases** section on the right side of this repository.
   - Download the latest `service.sudosync-1.0.0.zip` package.

2. **Install in Kodi:**
   - In Kodi, navigate to: *Settings -> Add-ons -> Install from zip file*.
   - Select the downloaded archive.

3. **Configure Network Path:**
   - Open SudoSync add-on settings in Kodi.
   - Specify the shared network folder where all Kodi instances have read and write permissions, e.g.:
     ```text
     smb://192.168.1.100/SharedFolder/.SudoSync/
     ```

---

## Compatibility

- Kodi v19 Matrix, v20 Nexus, and v21 Omega.
- Multi-platform: Windows, Android / Google TV, Linux, CoreELEC / LibreELEC.

---

## License

This project is open-source software licensed under the GPL-3.0 License.