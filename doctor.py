from adb_manager import ADBManager, AdbError


def main():
    print("PhonePhotoTransfer v0.2.2 - ADB diagnostic\n")
    print("Searching PATH, Android SDK variables, common SDK locations, and likely developer folders...\n")
    try:
        adb = ADBManager()
        adb.save_portable_path_hint()
        print(f"ADB FOUND: {adb.adb_path}")
        print(f"Discovery: {adb.discovery_method}")
        devices = adb.list_devices()
    except AdbError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)

    if not devices:
        print("\nADB works, but no Android device is currently detected.")
        print("Connect the phone, enable USB debugging, and accept the RSA prompt.")
        raise SystemExit(2)

    print("\nDevices:")
    for d in devices:
        print(f"{d.serial}\t{d.state}\t{d.details}")

    ready = [d for d in devices if d.state == "device"]
    if ready:
        print("\nOK: at least one device is ready.")
        raise SystemExit(0)
    print("\nDevice detected but not ready. If unauthorized, unlock the phone and tap Allow on the RSA dialog.")
    raise SystemExit(3)


if __name__ == "__main__":
    main()
