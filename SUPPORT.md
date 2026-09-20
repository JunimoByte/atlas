# Support & Help

Thank you for using Atlas! If you encounter issues, have questions, or need guidance, here is how to get help.

---

## Troubleshooting Common Questions

### 1. "Skipped (I/O error / file in use)" Warnings
* **Why it happens:** Web browsers lock active database files (`LOCK`, `Cookies-journal`, `lockfile`) while running.
* **Resolution:** Close your web browser before initiating a backup to ensure all in-memory tabs and database sessions are committed to disk.

### 2. "Atlas Must Not Run as Administrator" Warning
* **Why it happens:** Atlas follows a strict non-elevated security model to protect your system files and ensure generated archives match your normal user account permissions.
* **Resolution:** Run Atlas as a standard user without right-clicking "Run as Administrator".

### 3. Missing Passwords in Restored Chromium Profiles
* **Why it happens:** Chromium-based browsers (Chrome, Edge, Brave) bind saved passwords to hardware-level Windows DPAPI keys unique to your Windows user account.
* **Resolution:** All bookmarks, history, extensions, and preferences back up and restore seamlessly. Passwords must be exported/imported via your browser's built-in password manager.

---

## Where to Get Help

### GitHub Issues & Discussions
* **Bug Reports:** If you discover a bug, unexpected crash, or issue with a specific browser, please [open a GitHub Issue](https://github.com/JunimoByte/atlas/issues).
* **Feature Requests & Ideas:** Share suggestions or discuss new browser support in [GitHub Discussions](https://github.com/JunimoByte/atlas/discussions).

### Security Vulnerabilities
If you discover a security issue or vulnerability, please do **not** post it publicly. Follow the instructions in our [Security Policy](SECURITY.md) to submit a private advisory.

---

## Microsoft Store Users
If you installed Atlas through the Microsoft Store, all updates are delivered automatically. For technical support, bug reports, and release notes, the [GitHub Repository](https://github.com/JunimoByte/atlas) is the primary channel maintained by the developer.
