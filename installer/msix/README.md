# Microsoft Store Submission & Certification Guide

This document contains all metadata, reviewer notes, and packaging steps required for Microsoft Store certification.

---

## 1. Store Listing Metadata (Copy & Paste)

### Product Name
`Atlas` (or `Atlas Browser Backup`)

### Short Description (Under 100 characters)
Reliable, offline browser-profile backups for 300+ web browsers.

### Full Description
```text
Atlas is a lightweight, offline utility designed to preserve your browsing profiles safely and reliably. 

Whether you are switching PCs, reinstalling Windows, or backing up your bookmarks, history, and extension settings, Atlas automatically detects installed browsers and compresses their profile directories into clean, space-efficient ZIP archives.

Key Features:
• Supports 300+ Chromium, Gecko, and legacy browser variants (Chrome, Firefox, Edge, Brave, Zen, Opera, Vivaldi, etc.).
• Smart Exclusion: Automatically strips caches, shader caches, and temporary download files, drastically reducing archive sizes.
• 100% Offline & Private: No telemetry, no cloud sync, and zero outbound network connections.
• Non-Destructive: Reads profile directories strictly in read-only mode and never writes to your live browser folders.
• Standard User Execution: Operates under standard user privileges without requiring administrator elevation.
```

### Search Keywords (Tags)
`browser backup`, `bookmarks`, `firefox`, `chrome`, `edge`, `profile backup`, `offline backup`, `zip backup`

### Privacy Policy URL
`https://github.com/JunimoByte/atlas/blob/main/PRIVACY.md`

### Support Contact Info
`https://github.com/JunimoByte/atlas/blob/main/SUPPORT.md`

---

## 2. Notes for Certification (For the Microsoft Tester)

> [!IMPORTANT]
> Copy and paste this exact text into the **"Notes for certification"** text box in the Microsoft Partner Center during submission:

```text
TESTER INSTRUCTIONS:
1. Atlas is a desktop utility that detects locally installed web browsers (such as Microsoft Edge, Chrome, or Firefox) and backs up their profile folders into standard .zip files in the user's Downloads folder.
2. No login credentials, cloud accounts, or hardware keys are required to test the application.
3. Tester Prerequisite: Please ensure Microsoft Edge (or another browser) has been launched at least once on the test VM to generate a local profile directory prior to running Atlas.
4. To test:
   a. Launch the application.
   b. The application will scan and show the estimated backup size of detected local browsers.
   c. Click "OK" to begin backup.
   d. The progress bar will update and complete, saving standard .zip files to your local Downloads\Backup directory.
   e. Click "Open Folder" to view the generated archives, or "Cancel" to close.

SECURITY & PERMISSION DISCLOSURE:
• Restricted Capability (runFullTrust): Required to read standard user configuration directories (%APPDATA% and %LOCALAPPDATA%) where web browsers store local profiles.
• 100% Offline Architecture: The application declares NO network capabilities in AppxManifest.xml (no internetClient capability) and makes zero outbound network requests. Production binaries explicitly strip and exclude all networking libraries (socket, ssl, http, QtNetwork) from the runtime.
• Airplane Mode Verification: Testers may execute this application with all network adapters disabled or in Airplane Mode — Atlas operates 100% locally with zero internet dependency.
• No Password Decryption: Atlas does not crack, access, or decrypt DPAPI credentials or master passwords. Files are copied directly into standard compressed archives under user control.
• Read-Only Access: Original browser directories are never written to, altered, or deleted.
```

---

## 3. Restricted Capability Justification (`runFullTrust`)

During submission under the **App capabilities** or **Package submission** section, Microsoft requires an explanation for declaring `rescap:runFullTrust`:

> **Question:** Why does your application require the `runFullTrust` capability?
>
> **Copy & Paste Answer:**
> *"Atlas is a Win32 desktop utility packaged via Desktop Bridge. The `runFullTrust` capability is strictly required to enumerate and read standard local browser configuration directories in `%APPDATA%` and `%LOCALAPPDATA%` (e.g. `%LOCALAPPDATA%\Google\Chrome\User Data`) to generate user-initiated backup archives. The application declares no network capabilities (no internetClient), operates strictly offline, does not decrypt passwords, does not modify source files, and can be verified running in Airplane Mode."*

---

## 4. Age Ratings (IARC Questionnaire)

When completing the required International Age Rating Coalition (IARC) questionnaire in Partner Center:
* **Category:** Utility, Productivity, or Tools.
* **Violence / Sexual Content / Profanity:** No.
* **Online Interactions / Social Sharing / User Chat:** No.
* **Shares Physical Location:** No.
* **Shares Personal Information with Third Parties:** No.
* **Allows digital purchases / in-app purchases:** No.
* **Result:** Instant **PEGI 3 / ESRB Everyone** rating with zero certification friction.

---

## 5. Finding Your Publisher ID in Partner Center

Your Publisher ID is required in `AppxManifest.xml` (`Publisher="CN=..."`).
1. In Partner Center, click the **Gear Icon (Settings)** at the top right.
2. Navigate to **Account settings > Legal info > Developer tab**.
3. Under **Seller ID / Publisher ID**, copy your exact **CN** string (e.g., `CN=12345678-ABCD-EF01-2345-6789ABCDEF01`).
4. Replace `CN=YOUR-PUBLISHER-ID-FROM-PARTNER-CENTER` in `installer/msix/AppxManifest.xml`.

---

## 6. Packaging for Official Store Upload

### Prerequisites
* Windows SDK (`makeappx.exe` located at `C:\Program Files (x86)\Windows Kits\10\bin\<version>\x64`).

### Build & Package Steps
1. **Build Windows Executable:**
   ```powershell
   python -m PyInstaller main.spec --noconfirm
   ```
2. **Stage Directory (`dist/msix_store_stage/`):**
   * Copy `AppxManifest.xml` (with your real `CN=...` Publisher ID).
   * Copy `dist/Atlas-x86_64-Portable.exe` as `dist/msix_store_stage/Atlas.exe`.
   * Copy `installer/msix/Assets/` to `dist/msix_store_stage/Assets/`.
3. **Pack into MSIX:**
   ```powershell
   & "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe" pack /d dist/msix_store_stage /p dist/Atlas-1.2.0.0-Release.msix /o
   ```
4. **Upload:**
   * In Partner Center > Apps > Atlas > Packages, upload `dist/Atlas-1.2.0.0-Release.msix`.
   * *Note: Do NOT sign the Release package locally; Microsoft signs it automatically with their trusted Store root upon passing certification.*

---

## 7. First-Try Approval Pre-Flight Checklist

- [ ] `PRIVACY.md` URL is public and verified accessible: `https://github.com/JunimoByte/atlas/blob/main/PRIVACY.md`
- [ ] `SUPPORT.md` URL is public and verified accessible: `https://github.com/JunimoByte/atlas/blob/main/SUPPORT.md`
- [ ] `AppxManifest.xml` has `Publisher="CN=..."` matching Partner Center exactly.
- [ ] `Notes for Certification` from Section 2 pasted into the submission form.
- [ ] `runFullTrust` justification from Section 3 pasted into the capabilities form.
- [ ] Price set to **Free**; Markets set to **All** (or preferred regions).
