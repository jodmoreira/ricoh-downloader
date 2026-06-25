# Ricoh Downloader

A set of tools to automate the download of photos from the **Ricoh GR IIIx** camera via Wi-Fi. 

This project contains two solutions for the same goal:
1. **Android App (Flutter)**: To sync photos directly to your smartphone.
2. **Python Script**: To download photos via command line on your computer.

Both versions keep a local history of what has already been downloaded, allowing you to run them multiple times without duplicating files in your gallery or folder.

---

## 📱 1. Android App

The app allows you to download photos from the camera wirelessly and autonomously. Just fill in the Wi-Fi information in the interface, and it will automatically connect to the camera, download the new photos to the `Pictures/Ricoh` folder (visible in the system gallery), and disconnect on its own.

### How to install via Obtainium (Recommended)
The application is not on the Google Play Store. Every code update automatically generates an installable `.apk` file in the "Releases" tab of this GitHub repository.

The best way to install and receive updates is through [Obtainium](https://github.com/ImranR98/Obtainium):
1. Install **Obtainium** on your Android device.
2. Open Obtainium, go to **Add App** and paste the link to this repository:
   `https://github.com/jodmoreira/ricoh-downloader`
3. Click **Add**. Obtainium will find the latest version in the Releases tab and offer to install the application (named "Ricoh DL").
4. Next time an app update is released here on Github, Obtainium will notify you and perform the update with a single tap.

> **Manual Installation:** If you don't want to use Obtainium, just open this repository on Github from your phone, click on **Releases**, download the `.apk` file of the latest version, and tap to install (you need to allow installation from unknown sources on Android).

### Basic Usage
1. Turn on the wireless connection of your Ricoh (it will create a Wi-Fi network that starts with `RICOH_...`).
2. Open the "Ricoh DL" app.
3. Enter the network name (SSID) and password (shown on your camera screen).
4. Click on **Sincronizar Fotos** (Sync Photos). The app will ask for permissions to manage Wi-Fi and save files in your photos, and will handle the entire process by itself!

For more technical details about the mobile version, see the [`mobile/`](./mobile/) directory.

---

## 💻 2. Computer Script (Python)

A solution aimed at running on **Linux**, **Windows**, or **WSL2** to sync your photos to a directory on your PC.

### Prerequisites
- Python 3.8+
- Be connected in some way to the camera's network (manually by the PC, or automatically if using Windows/WSL by providing SSID and password so the script can handle `netsh`).

### Installation

Open the terminal, clone the repository, and install the dependencies:
```bash
git clone https://github.com/jodmoreira/ricoh-downloader.git
cd ricoh-downloader

# It is recommended to create a virtual environment (optional, but a good practice)
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

pip install -r requirements.txt
```

### Basic Usage

**Manual Mode (Any OS):**
Connect your computer to the camera's Wi-Fi manually, then run:
```bash
python ricoh_downloader.py --dest ~/Pictures/Ricoh
```

**Automatic Mode (Windows / WSL2):**
Let the script manage the Wi-Fi and connect automatically to the camera for you. Pass the SSID and password:
```bash
python ricoh_downloader.py --ssid RICOH_XXXXXX --password THE-CAMERA-PASSWORD --dest ~/Pictures/Ricoh
```
> *Tip*: Instead of passing the password in the command (which is saved in the terminal history), you can use `--password-env RICOH_WIFI_PASS` and define the environment variable.

**Useful options:**
- `--dry-run`: Checks and lists which photos would be downloaded, without actually downloading anything.
- `--reset-history`: Ignores the database and tries to download everything again (local files with the same name will be overwritten if they still exist, useful to force a repair).
- `--ext JPG --ext DNG`: Downloads only specific file formats.

The download history is saved in a lightweight database `download_history.db` in the directory where the script is run.
