# -*- coding: utf-8 -*-
import base64
import io
import os
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import MagicMock, patch

sys.modules["xbmc"] = MagicMock()
sys.modules["xbmcaddon"] = MagicMock()
sys.modules["xbmcgui"] = MagicMock()
sys.modules["xbmcvfs"] = MagicMock()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "service.sudosync")))

import resources.lib.sudosync_core as sudosync_core
import resources.lib.sudosync_merge as sudosync_merge


TEST_PUBLIC_KEY = """-----BEGIN RSA PUBLIC KEY-----
MIIBCgKCAQEA1BZ02oXenW8L4FuHr66LkcTLbOFWKFBEXZyynB1hkwUdGNBV9kVz
ULGmeFUlntyct/J6OBSg99xl8iimAzTiE5KPF63BYRqzpe93xOk7lLl3W63LIg4L
LoGB4LhpgYACVU1pdAeYqV3PLzMZYENDrN5RwaexzuHc9oNeDdisueHmRJrtX3XI
qa+lJWYDqw1AZhFTpbHw1VnwrGb3Dd9WGJ0TZUo3UMPGZrsJTcnshQH7cSq2ysSe
5+Vf9JJtek3o9K9t0aHQ7T0TjfnRWRYZIgd8ARhWZY6H/BmA4JOzcP/3Wie85HnZ
flbA/elM8OIDTrht4mlpXbZLG602nC9m0QIDAQAB
-----END RSA PUBLIC KEY-----"""

TEST_MESSAGE = base64.b64decode(
    "U3Vkb1N5bmMgcmVhbCBSU0EgdGVzdCB2ZWN0b3IK"
)
TEST_SIGNATURE = base64.b64decode("PzPMcn3fEKOMMiVSpU8YAxLBVYwoGATnwNT/R3kRZBvoQqAy6KM6s7debbsWQuZW6fwrenHcmzE2bMu/2JKq6AFRaKhXHngMC3HRJVJxa2A8V1qW+lvNK8C+yVeZIateEJLDAwufaUneihoartwUWoUFFqP42XRWVX/c1KjB1cnyzijydd1hoCiiKtqax5aGvlHBVerB/4cMeM4KKvB1T99vcrRDhA3G+45rn5uU7026mrOp1Nk3XSlObhSW8BY2Gg5V3PRg3HDSkbmASx/BPHShShapZjoW7lQsGVhk+RZjNXj/WS5s7kAkIXW5/vQPuMvBYvFeosSrUFcsp4rsJQ==")

TEST_ZIP = base64.b64decode("UEsDBBQAAAAAAAAAIVBNn8+aNQAAADUAAAAaAAAAc2VydmljZS5zdWRvc3luYy9hZGRvbi54bWw8YWRkb24gaWQ9InNlcnZpY2Uuc3Vkb3N5bmMiIHZlcnNpb249IjEuMi4wIj48L2FkZG9uPlBLAwQUAAAAAAAAACFQVZQkQA4AAAAOAAAAGAAAAHNlcnZpY2Uuc3Vkb3N5bmMvdGVzdC5weXByaW50KCJoZWxsbyIpUEsBAhQAFAAAAAAAAAAhUE2fz5o1AAAANQAAABoAAAAAAAAAAAAAAIABAAAAAHNlcnZpY2Uuc3Vkb3N5bmMvYWRkb24ueG1sUEsBAhQAFAAAAAAAAAAhUFWUJEAOAAAADgAAABgAAAAAAAAAAAAAAIABbQAAAHNlcnZpY2Uuc3Vkb3N5bmMvdGVzdC5weVBLBQYAAAAAAgACAI4AAACxAAAAAAA=")
TEST_ZIP_SIGNATURE = base64.b64decode("GmToXnEgT5oAaQ4lZ2WKBS9nYTub30Mui4iimmtMb9j5L3Rrqv6nnOiN1rgFbN/L8u3Ed1Ac9+P6OUTkzQPw8o6WLgFQjTAXAoFsoHWuWNcNxp/j7WoTp9Z+hE1vt/DW6aSgsfDyjDE7SV3RBc97HAXcabqnGgRbQBbtm+AUekYpMmg2ttI7t9bPC11WBZGEC7+3Iq5/vnXwK8nrs6hQACaveEIV096//aNpRi6De+bG9lOnVzmo4XrsMGdW95Z3LUGtJgFbzY+yp/ZC6nUXu5l9p8ujE6i4afTEgkI5RB5bNV1X8oMBYW2v/QBV6u2RI5mXKlTdi7kcqgoXkO9K6Q==")


class TestSecurityFixes(unittest.TestCase):
    def setUp(self):
        self.original_key = sudosync_core.PUBLIC_KEY_PEM
        sudosync_core.PUBLIC_KEY_PEM = TEST_PUBLIC_KEY

    def tearDown(self):
        sudosync_core.PUBLIC_KEY_PEM = self.original_key

    def test_real_rsa_sha256_signature_verifies(self):
        self.assertTrue(
            sudosync_core._verify_rsa_pkcs1_sha256(
                TEST_PUBLIC_KEY, TEST_MESSAGE, TEST_SIGNATURE
            )
        )
        modified = TEST_MESSAGE[:-1] + bytes([TEST_MESSAGE[-1] ^ 1])
        self.assertFalse(
            sudosync_core._verify_rsa_pkcs1_sha256(
                TEST_PUBLIC_KEY, modified, TEST_SIGNATURE
            )
        )

    def test_signed_zip_is_validated_before_install_parser(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "service.sudosync-1.2.0.zip")
            with open(path, "wb") as handle:
                handle.write(TEST_ZIP + TEST_ZIP_SIGNATURE)

            version = sudosync_core._validate_update_zip(path, "1.2.0")
            self.assertEqual(version, "1.2.0")
            verified = path + ".verified"
            self.assertTrue(os.path.isfile(verified))
            with open(verified, "rb") as handle:
                self.assertEqual(handle.read(), TEST_ZIP)

    def test_modified_or_wrong_signature_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.zip")
            modified = TEST_ZIP[:-1] + bytes([TEST_ZIP[-1] ^ 1])
            with open(path, "wb") as handle:
                handle.write(modified + TEST_ZIP_SIGNATURE)
            with self.assertRaises(ValueError):
                sudosync_core._validate_update_zip(path)

            with open(path, "wb") as handle:
                bad_sig = bytearray(TEST_ZIP_SIGNATURE)
                bad_sig[-1] ^= 1
                handle.write(TEST_ZIP + bytes(bad_sig))
            with self.assertRaises(ValueError):
                sudosync_core._validate_update_zip(path)

    def test_apply_uses_only_local_kodi_id(self):
        calls = []
        item = {
            "type": "movie",
            "display": "Test",
            "file": "C:/Movies/test.mkv",
            "aliases": ["movie:tmdb:12345"],
            "local": {"movieid": 999999},
            "changes": {"playcount": {"from": 0, "to": 1}},
        }
        secure_map = {
            ("movie", "C:/Movies/test.mkv"): {
                "id": 42,
                "aliases": {"movie:tmdb:12345"},
            }
        }

        with patch.object(sudosync_core, "rpc", side_effect=lambda method, params: calls.append((method, params)) or {}):
            sudosync_core._apply_one_planned_item(item, secure_map)

        self.assertEqual(calls[0][0], "VideoLibrary.SetMovieDetails")
        self.assertEqual(calls[0][1]["movieid"], 42)
        self.assertNotEqual(calls[0][1]["movieid"], 999999)

    def test_apply_without_secure_map_is_rejected(self):
        item = {
            "type": "movie",
            "file": "C:/Movies/test.mkv",
            "aliases": ["movie:tmdb:12345"],
            "changes": {"playcount": {"from": 0, "to": 1}},
        }
        with self.assertRaises(ValueError):
            sudosync_core._apply_one_planned_item(item, None)

    def test_non_base_cannot_publish_shared_sudosync_alias(self):
        addon = MagicMock()
        addon.getSetting.side_effect = lambda key: {
            "sudosync_id_prefix": "EVIL",
            "sudosync_id_prefix_last_synced": "OLD",
        }.get(key, "")
        config = {
            "initialization": {"base_client_id": "BASE"},
            "sudosync_network_id": "NET-1234",
            "sudosync_network_alias": "GOOD",
        }

        with patch.object(sudosync_core.xbmcaddon, "Addon", return_value=addon),              patch.object(sudosync_core, "addon_settings", return_value={"base_path": "smb://nas/share/"}),              patch.object(sudosync_core, "read_shared_config", return_value=config),              patch.object(sudosync_core, "get_or_create_client_id", return_value="PEER"),              patch.object(sudosync_core, "update_shared_config") as update_shared:
            result = sudosync_core.get_or_sync_network_id_and_alias("smb://nas/share/")

        self.assertEqual(result, "NET-1234")
        update_shared.assert_not_called()
        addon.setSetting.assert_any_call("sudosync_id_prefix", "GOOD")
        addon.setSetting.assert_any_call("sudosync_id_prefix_last_synced", "GOOD")

    def test_non_base_cannot_create_shared_sudosync_network_id(self):
        addon = MagicMock()
        addon.getSetting.side_effect = lambda key: {
            "sudosync_id_prefix": "EVIL",
            "sudosync_id_prefix_last_synced": "",
        }.get(key, "")
        config = {"initialization": {"base_client_id": "BASE"}}

        with patch.object(sudosync_core.xbmcaddon, "Addon", return_value=addon),              patch.object(sudosync_core, "addon_settings", return_value={"base_path": "smb://nas/share/"}),              patch.object(sudosync_core, "read_shared_config", return_value=config),              patch.object(sudosync_core, "get_or_create_client_id", return_value="PEER"),              patch.object(sudosync_core, "update_shared_config") as update_shared:
            with self.assertRaises(RuntimeError):
                sudosync_core.get_or_sync_network_id_and_alias("smb://nas/share/")

        update_shared.assert_not_called()

    def test_base_may_publish_changed_shared_sudosync_alias(self):
        addon = MagicMock()
        addon.getSetting.side_effect = lambda key: {
            "sudosync_id_prefix": "NEW",
            "sudosync_id_prefix_last_synced": "OLD",
        }.get(key, "")
        config = {
            "initialization": {"base_client_id": "BASE"},
            "sudosync_network_id": "NET-1234",
            "sudosync_network_alias": "OLD",
        }

        with patch.object(sudosync_core.xbmcaddon, "Addon", return_value=addon),              patch.object(sudosync_core, "addon_settings", return_value={"base_path": "smb://nas/share/"}),              patch.object(sudosync_core, "read_shared_config", return_value=config),              patch.object(sudosync_core, "get_or_create_client_id", return_value="BASE"),              patch.object(sudosync_core, "update_shared_config") as update_shared:
            result = sudosync_core.get_or_sync_network_id_and_alias("smb://nas/share/")

        self.assertEqual(result, "NET-1234")
        update_shared.assert_called_once()
        addon.setSetting.assert_any_call("sudosync_id_prefix_last_synced", "NEW")

    def test_live_plan_propagates_aliases(self):
        snapshots = [
            {
                "client": {"id": "A", "name": "A"},
                "movies": [{
                    "type": "movie",
                    "title": "Test",
                    "year": 2020,
                    "file": "C:/Movies/test.mkv",
                    "ids": {"tmdb": "12345"},
                    "state": {"playcount": 1, "lastplayed": "", "userrating": 0, "resume": {"position": 0, "total": 0}},
                    "field_versions": {
                        "playcount": {"lc": 2, "ts": "2026-10-08T10:00:00.000Z", "seq": 2, "client_id": "A"},
                        "lastplayed": {"lc": 1, "ts": "2026-10-08T10:00:00.000Z", "seq": 1, "client_id": "A"},
                        "userrating": {"lc": 1, "ts": "2026-10-08T10:00:00.000Z", "seq": 1, "client_id": "A"},
                        "resume": {"lc": 1, "ts": "2026-10-08T10:00:00.000Z", "seq": 1, "client_id": "A"}
                    },
                }],
                "episodes": [],
            },
            {
                "client": {"id": "B", "name": "B"},
                "movies": [{
                    "type": "movie",
                    "title": "Test",
                    "year": 2020,
                    "file": "D:/Movies/test.mkv",
                    "ids": {"tmdb": "12345"},
                    "state": {"playcount": 0, "lastplayed": "", "userrating": 0, "resume": {"position": 0, "total": 0}},
                    "field_versions": {
                        "playcount": {"lc": 1, "ts": "2026-10-08T09:00:00.000Z", "seq": 1, "client_id": "B"},
                        "lastplayed": {"lc": 1, "ts": "2026-10-08T09:00:00.000Z", "seq": 1, "client_id": "B"},
                        "userrating": {"lc": 1, "ts": "2026-10-08T09:00:00.000Z", "seq": 1, "client_id": "B"},
                        "resume": {"lc": 1, "ts": "2026-10-08T09:00:00.000Z", "seq": 1, "client_id": "B"}
                    },
                }],
                "episodes": [],
            },
        ]
        plan = sudosync_merge.build_live_plan(snapshots)
        items = plan["planned_changes"].get("B") or []
        self.assertTrue(items)
        self.assertIn("movie:tmdb:12345", items[0]["aliases"])


if __name__ == "__main__":
    unittest.main()
