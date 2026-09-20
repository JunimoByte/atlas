# Privacy Policy

**Last Updated:** September 2026

Atlas is committed to protecting your privacy. This policy outlines how Atlas interacts with your data.

---

## 1. The Core Principle: 100% Offline & Local

Atlas is an **offline-first desktop backup utility**. 
* **Zero Telemetry:** Atlas contains no analytics, crash reporters, tracking cookies, or usage telemetry.
* **Zero Network Traffic:** Atlas makes **no outbound network requests**. In fact, production binary builds explicitly strip and exclude standard Python and Qt networking libraries (`socket`, `ssl`, `http`, `QtNetwork`) at packaging time.
* **No Cloud Storage:** Atlas does not upload your files to any server, cloud provider, or remote repository. All data remains exclusively on your physical storage device.

---

## 2. What Data Atlas Accesses

To create backups, Atlas requires read-only access to local files on your machine:
* **Browser Profiles:** Atlas scans standard application data directories (`%APPDATA%`, `%LOCALAPPDATA%`, `~/.config`, etc.) for installed browser profile folders.
* **Content:** Backups may contain your local browser bookmarks, history, settings, and extension configurations.
* **Excluded Data:** Atlas automatically filters out cache files, shader caches, temporary assets, and uninstaller executables to reduce archive size.
* **No Decryption:** Atlas **never** attempts to decrypt Windows DPAPI secrets, master keys, or saved browser passwords. Files are copied directly into standard compressed ZIP archives without inspection or modification.

---

## 3. How Data is Stored and Handled

* **Read-Only Source:** Atlas treats all browser profile directories as read-only. It never modifies, writes to, or deletes any file inside your live browser folders.
* **Destination Control:** Archive files (`.zip`) are written directly to your local destination (defaulting to your local `Downloads\Backup` directory) under standard user-level permissions.
* **User Retention:** You have complete ownership and control over your generated backup archives. Deleting the generated `.zip` files removes all traces of the backup from your system.

---

## 4. Third-Party Disclosures

Atlas does not share, sell, rent, or disclose any personal information or backup archives to any third parties or external services under any circumstances.

---

## 5. Contact & Questions

If you have any questions, concerns, or security inquiries regarding this Privacy Policy, please open an issue or private vulnerability report on our [GitHub repository](https://github.com/JunimoByte/atlas).
