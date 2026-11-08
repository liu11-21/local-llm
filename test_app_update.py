import hashlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch
from urllib.parse import quote

from app_update import RELEASES, ReleaseRedirect, download_update, select_update, select_workspace_update
from downloads import DownloadCancelled


class Reply(io.BytesIO):
    status = 200
    headers = {}


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.data = b"MZ update contents"
        tag = "v0.10.0"
        name = f"LocalLLM-{tag}-Windows-x64.exe"
        self.asset = {"name": name, "state": "uploaded", "size": len(self.data),
                      "digest": "sha256:" + hashlib.sha256(self.data).hexdigest(),
                      "browser_download_url": f"{RELEASES}/download/{tag}/{name}"}
        self.release = {"tag_name": tag, "draft": False, "prerelease": False, "assets": [self.asset]}

    def test_only_official_newer_asset_is_offered(self):
        self.assertEqual(select_update(self.release, "0.9.9").tag, "v0.10.0")
        self.assertIsNone(select_update(self.release, "0.10.0"))
        self.assertIsNone(select_update(self.release, "1.0.0"))
        self.asset["browser_download_url"] = "https://example.invalid/update.exe"
        with self.assertRaises(ValueError):
            select_update(self.release, "0.9.9")
        with self.assertRaises(ValueError):
            ReleaseRedirect().redirect_request(None, None, 302, "", {}, "https://example.invalid/update.exe")

    def test_installed_and_portable_builds_get_matching_updates(self):
        installer = dict(self.asset)
        installer["name"] = installer["name"].replace(".exe", "-Setup.exe")
        installer["browser_download_url"] = installer["browser_download_url"].replace(".exe", "-Setup.exe")
        self.release["assets"].append(installer)
        self.assertEqual(select_update(self.release, "0.6.2", installer=True).name, installer["name"])
        self.assertEqual(select_update(self.release, "0.6.2").name, self.asset["name"])

    def test_corrupt_and_cancelled_downloads_never_publish_exe(self):
        offer = select_update(self.release, "0.9.9")
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            with patch("app_update.open_github", return_value=Reply(b"X" * offer.size)):
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    download_update(offer, folder, Event(), lambda *_: None)
            self.assertEqual(list(folder.iterdir()), [])
            cancel = Event()
            with patch("app_update.open_github", return_value=Reply(self.data)):
                with self.assertRaises(DownloadCancelled):
                    download_update(offer, folder, cancel, lambda *_: cancel.set())
            self.assertEqual(list(folder.iterdir()), [])

    def test_workspace_updates_ignore_legacy_releases_and_unverified_assets(self):
        name = "Local LLM Workspace_0.6.3_x64-setup.exe"
        tag = "workspace-v0.6.3"
        asset = dict(self.asset, name=name, browser_download_url=f"{RELEASES}/download/{tag}/{quote(name)}")
        release = {"tag_name": tag, "assets": [asset]}
        self.assertIsNone(select_workspace_update([self.release], "0.6.2"))
        self.assertIsNone(select_workspace_update([dict(release, prerelease=True)], "0.6.2"))
        self.assertEqual(select_workspace_update([self.release, release], "0.6.2").name, name)
        self.assertIsNone(select_workspace_update([release], "0.6.3"))
        asset["digest"] = None
        self.assertIsNone(select_workspace_update([release], "0.6.2"))


if __name__ == "__main__":
    unittest.main()
