import tempfile
import unittest
from pathlib import Path

from adb_manager import AdbError, DeviceUnavailable
from transfer_database import TransferDatabase
from transfer_engine import TransferEngine


class DummyADB:
    pass


class FakeADB:
    def __init__(self, files):
        self.files = dict(files)
        self.deleted = []
        self.pull_count = 0

    def ensure_ready(self, serial):
        return None

    def list_files(self, root, *, serial, cancel_event=None):
        return list(self.files)

    def file_size(self, path, *, serial, cancel_event=None):
        return len(self.files[path])

    def pull(self, path, local, *, serial, cancel_event=None, on_process=None):
        self.pull_count += 1
        Path(local).write_bytes(self.files[path])
        return "ok"

    def delete_file(self, path, *, serial, cancel_event=None):
        self.deleted.append(path)
        self.files.pop(path, None)


class DisconnectADB(FakeADB):
    def __init__(self, files):
        super().__init__(files)
        self.ready_calls = 0

    def ensure_ready(self, serial):
        self.ready_calls += 1
        if self.ready_calls > 1:
            raise DeviceUnavailable("offline")

    def pull(self, path, local, *, serial, cancel_event=None, on_process=None):
        raise AdbError("device offline")


class TransferTests(unittest.TestCase):
    def test_local_path_preserves_relative_tree(self):
        with tempfile.TemporaryDirectory() as td:
            e = TransferEngine(
                DummyADB(),
                serial="x",
                remote_root="/sdcard/DCIM/Camera",
                destination_root=td,
            )
            try:
                p = e.local_path_for("/sdcard/DCIM/Camera/2026/IMG_1.jpg")
                self.assertEqual(p, Path(td) / "2026" / "IMG_1.jpg")
            finally:
                e.db.close()

    def test_database_resume_record(self):
        with tempfile.TemporaryDirectory() as td:
            local = Path(td) / "a.jpg"
            local.write_bytes(b"abc")
            db = TransferDatabase(td)
            try:
                db.mark_completed("/sdcard/a.jpg", 3, str(local), False)
                row = db.get_completed("/sdcard/a.jpg")
                self.assertEqual(row[0], 3)
                self.assertEqual(Path(row[1]), local)
                self.assertEqual(row[2], 0)
            finally:
                db.close()

    def test_copy_then_resume_skips_already_verified_file(self):
        remote = "/sdcard/DCIM/Camera/IMG_1.jpg"
        adb = FakeADB({remote: b"photo-bytes"})
        with tempfile.TemporaryDirectory() as td:
            stats1 = TransferEngine(adb, serial="x", remote_root="/sdcard/DCIM/Camera", destination_root=td).run()
            self.assertEqual(stats1.copied, 1)
            self.assertEqual(adb.pull_count, 1)
            self.assertEqual((Path(td) / "IMG_1.jpg").read_bytes(), b"photo-bytes")

            stats2 = TransferEngine(adb, serial="x", remote_root="/sdcard/DCIM/Camera", destination_root=td).run()
            self.assertEqual(stats2.skipped, 1)
            self.assertEqual(adb.pull_count, 1)

    def test_move_deletes_only_after_verified_copy(self):
        remote = "/sdcard/DCIM/Camera/VID_1.mp4"
        adb = FakeADB({remote: b"video"})
        with tempfile.TemporaryDirectory() as td:
            stats = TransferEngine(
                adb,
                serial="x",
                remote_root="/sdcard/DCIM/Camera",
                destination_root=td,
                move_after_verify=True,
            ).run()
            self.assertEqual(stats.copied, 1)
            self.assertEqual(stats.deleted, 1)
            self.assertEqual(adb.deleted, [remote])
            self.assertTrue((Path(td) / "VID_1.mp4").exists())

    def test_disconnect_aborts_run_for_clean_resume(self):
        remote = "/sdcard/DCIM/Camera/IMG_2.jpg"
        adb = DisconnectADB({remote: b"x"})
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(DeviceUnavailable):
                TransferEngine(
                    adb,
                    serial="x",
                    remote_root="/sdcard/DCIM/Camera",
                    destination_root=td,
                    retries=3,
                ).run()
            self.assertFalse((Path(td) / "IMG_2.jpg").exists())
            self.assertFalse((Path(td) / "IMG_2.jpg.part").exists())


if __name__ == "__main__":
    unittest.main()
