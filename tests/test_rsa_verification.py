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
MIIBCgKCAQEAtffR2+vw6fD5XiZaL1y6lQShlbxsU0UK6mEdsYKwDV0FZ5PUN4UW
mvKgQp4YUlQP80A2duoiouzsGlxSRR4/Q0bUEyYB1KYBN2svr0DIpvWgMvP7Bw1J
SRumWicKRjCVd+A5NpMh+H8WFpqnfww64A1O+AoR6p4/TwEPctiXjw9hq1Wi+JtP
5RBtbtz9nlWGGoj4caHsjjGT9vF2ao08JtsOn3+N6bja5nkkmguV5sw75v4C8H61
nWwMb0yC4vjsvXfcwQkF7WC//CXc77VTB5D/TqBZxsBP5WVgLZlJMuhDEaX60tAR
8NQIGnBk/xdTeRGe/0lUVK4OEAhtq+xHqQIDAQAB
-----END RSA PUBLIC KEY-----"""

TEST_MESSAGE = base64.b64decode(
    "U3Vkb1N5bmMgcmVhbCBSU0EgdGVzdCB2ZWN0b3IK"
)
TEST_SIGNATURE = base64.b64decode(
    "o2Q9WqfhKxxdKdHPKjQuQqrkOLsFsvH8Br3LUki9qAL16ygZGezM5znzp3zsYr31Cts42C3+HOKWNBTKEYUW5y2n4ZloJbjMmAyX1VSK3eumd0/7efxd3Xulf8P85eAtB4IP3Dfe67Q3rYrjuaaKFJmzOwT35SGnl9DVmnibGoa2KfRnScn+MuQAxjCvUpcZiGmwqzbUVuWxBk/o2P91BIFwDG+6qr2ujj0em9oGK7JLAA6Wv1qRbDt1R1MWTUVZXHBjOiPFs+JVEOqRpB2sgU6klfd6j0H+ZFzrVShvve+8p3THahMnmb+9Fbchaa5842xYsVQOmixSV2p9PTBA8g=="
)

TEST_ZIP = base64.b64decode(
    "UEsDBBQAAAAAAAAAIVBNn8+aNQAAADUAAAAaAAAAc2VydmljZS5zdWRvc3luYy9hZGRvbi54bWw8YWRkb24gaWQ9InNlcnZpY2Uuc3Vkb3N5bmMiIHZlcnNpb249IjEuMi4wIj48L2FkZG9uPlBLAwQUAAAAAAAAACFQVZQkQA4AAAAOAAAAGAAAAHNlcnZpY2Uuc3Vkb3N5bmMvdGVzdC5weXByaW50KCJoZWxsbyIpUEsBAhQDFAAAAAAAAAAhUE2fz5o1AAAANQAAABoAAAAAAAAAAAAAAKQBAAAAAHNlcnZpY2Uuc3Vkb3N5bmMvYWRkb24ueG1sUEsBAhQDFAAAAAAAAAAhUFWUJEAOAAAADgAAABgAAAAAAAAAAAAAAKQBbQAAAHNlcnZpY2Uuc3Vkb3N5bmMvdGVzdC5weXBLBQYAAAAAAgACAI4AAACxAAAAAAA="
)
TEST_ZIP_SIGNATURE = base64.b64decode(
    "ljjEVImyvCeTpPxxKTHsO7Ii1uDTCf7fu1F6KhH7OAJvrgbaJejfCx/Ss4DWNFSCZ7LrW4+PRgLnLWM0Doi3vJ4d4xBZGgSsl1w3QCDRqy1TskdCqSFf+8jK71DYE/wEe4ORvUY0qXZs8Jl1GePkCFRnmt+Rjljvez0sqz7kqmT9U2xkUC3XaiRJ2kvLfLw0EA8hw1G5Lvp+Kb3jXMUYRjbohxdJ59JWPGNJSDTIUGQO3/KBF0aKRfeCPKIynyLkZmxmEiX+s6Y5ID0fHI3gGrJV3zHo1w917VK2ZF58juQsJj1nSktUdo9N8/Ftn8VKdL8shjWlfkmrQgijikXQgQ=="
)


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
                    "field_versions": {},
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
                    "field_versions": {},
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
