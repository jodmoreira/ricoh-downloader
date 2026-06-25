# Ricoh Downloader App

An Android App in Flutter to download photos from a Ricoh GR IIIx (via Wi-Fi).

Just like in `ped-admin`, this repository only stores the main Flutter code (`lib/` and `pubspec.yaml`) to avoid versioning gigabytes of Gradle-generated binaries in the `android/` directory.
The GitHub Action creates the Android structure at build time and injects the necessary permissions.

## Features
- Input for the camera's Wi-Fi SSID and Password.
- Connects automatically to the provided Wi-Fi network.
- Lists and compares the history of downloaded photos (prevents downloading duplicates).
- Downloads photos directly to the public Android gallery (`Pictures/Ricoh`).

## CI/CD and Obtainium

1. **Obtainium**: Install it on your phone and point it to this GitHub repository. Obtainium will track the **Releases** that are automatically generated whenever the code is updated.
2. **Automatic Build**: When you push commits modifying `mobile/` or `build-apk.yml`, GitHub Actions will build the `.apk` and create a Release.

### Signing (for automatic Obtainium Updates)

In order for Android to allow updates without having to uninstall the app (thus keeping your saved settings), the versions must be signed with the same Keystore.

Go to **Settings -> Secrets and variables -> Actions** in your repository and create the following repository Secrets:
- `ANDROID_KEYSTORE_BASE64`: The base64 encoding of your `.p12` or `.jks` keystore (`base64 keystore.jks`)
- `ANDROID_KEYSTORE_PASSWORD`: The password for your keystore
- `ANDROID_KEY_ALIAS`: The alias of your key (e.g., `ricoh-dl`)

If these secrets are not present, GitHub Actions will still build and upload an unsigned/debug APK, but future updates via Obtainium might fail to seamlessly overwrite the old app.
