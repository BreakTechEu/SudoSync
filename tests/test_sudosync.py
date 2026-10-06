import os
import sys
import unittest
from unittest.mock import MagicMock

# Mock xbmc modules
sys.modules['xbmc'] = MagicMock()
sys.modules['xbmcaddon'] = MagicMock()
sys.modules['xbmcgui'] = MagicMock()
sys.modules['xbmcvfs'] = MagicMock()

# Append the resources/lib directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'service.sudosync')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'service.sudosync', 'resources', 'lib')))

import sudosync_merge
import sudosync_core

class TestSudoSync(unittest.TestCase):

    def test_version_ordering(self):
        v1 = {"lc": 1, "ts": "2026-10-06T10:00:00Z", "seq": 1, "client_id": "A"}
        v2 = {"lc": 2, "ts": "2026-10-06T09:00:00Z", "seq": 2, "client_id": "B"}
        v3 = {"lc": 2, "ts": "2026-10-06T09:00:00Z", "seq": 3, "client_id": "B"}
        
        # lc=2 is newer than lc=1, even if ts is older (drifting clock)
        self.assertGreater(sudosync_merge._version_tuple(v2), sudosync_merge._version_tuple(v1))
        # lc=2, seq=3 is newer than lc=2, seq=2
        self.assertGreater(sudosync_merge._version_tuple(v3), sudosync_merge._version_tuple(v2))
        
    def test_mirror_detection(self):
        # same path
        cluster1 = [
            {"client_id": "A", "record": {"type": "movie", "title": "Test", "year": 2000, "file": "smb://A"}},
            {"client_id": "A", "record": {"type": "movie", "title": "Test", "year": 2000, "file": "smb://A"}},
        ]
        self.assertTrue(sudosync_merge._safe_mirror_cluster(cluster1))
        
        # local + network with same name
        cluster2 = [
            {"client_id": "B", "record": {"type": "movie", "title": "Film", "year": 2000, "file": "C:/Movies/film.mkv"}},
            {"client_id": "B", "record": {"type": "movie", "title": "Film", "year": 2000, "file": "smb://NAS/film.mkv"}},
        ]
        self.assertTrue(sudosync_merge._safe_mirror_cluster(cluster2))
        
        # two networks (not a safe mirror)
        cluster3 = [
            {"client_id": "B", "record": {"type": "movie", "title": "Film", "year": 2000, "file": "smb://NAS1/film.mkv"}},
            {"client_id": "B", "record": {"type": "movie", "title": "Film", "year": 2000, "file": "smb://NAS2/film.mkv"}},
        ]
        self.assertFalse(sudosync_merge._safe_mirror_cluster(cluster3))

    def test_numeric_version(self):
        self.assertEqual(sudosync_core._numeric_version("1.1.0-alpha"), (1, 1, 0, 0))
        self.assertEqual(sudosync_core._numeric_version("1.1.0-beta"), (1, 1, 0, 1))
        self.assertEqual(sudosync_core._numeric_version("1.1.0-rc"), (1, 1, 0, 2))
        self.assertEqual(sudosync_core._numeric_version("1.1.0"), (1, 1, 0, 3))
        self.assertEqual(sudosync_core._numeric_version("1.2.0"), (1, 2, 0, 3))
        
        self.assertGreater(sudosync_core._numeric_version("1.1.0-beta"), sudosync_core._numeric_version("1.1.0-alpha"))
        self.assertGreater(sudosync_core._numeric_version("1.1.0"), sudosync_core._numeric_version("1.1.0-beta"))

if __name__ == '__main__':
    unittest.main()
