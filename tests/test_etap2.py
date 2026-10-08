# -*- coding: utf-8 -*-
import os
import sys
import unittest
import tempfile
import json
import zipfile
import io
import shutil
import base64
import copy
from xml.etree import ElementTree as ET

from unittest.mock import MagicMock, patch
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

sys.modules['xbmc'] = MagicMock()
sys.modules['xbmcaddon'] = MagicMock()
sys.modules['xbmcgui'] = MagicMock()

class MockFile:
    def __init__(self, p, m="r"):
        self.p = p
        self.m = m
        self.b = bytearray()
        self._read_done = False
    def write(self, b):
        self.b.extend(b)
        return True
    def read(self, limit=-1):
        if self._read_done: return bytearray()
        self._read_done = True
        with open(self.p, "rb") as f: return bytearray(f.read())
    def readBytes(self, chunk=None):
        return self.read()
    def close(self):
        if "w" in self.m:
            with open(self.p, "wb") as f: f.write(self.b)
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

class MockXbmcvfs:
    File = MockFile
    @staticmethod
    def exists(path): return os.path.exists(path)
    @staticmethod
    def delete(path):
        try:
            os.remove(path)
            return True
        except: return False
    @staticmethod
    def rename(src, dst):
        try:
            os.rename(src, dst)
            return True
        except: return False
    @staticmethod
    def copy(src, dst):
        try:
            shutil.copy(src, dst)
            return True
        except: return False
    @staticmethod
    def mkdirs(path):
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except: return False
    @staticmethod
    def listdir(path):
        try:
            entries = os.listdir(path)
            dirs = [e for e in entries if os.path.isdir(os.path.join(path, e))]
            files = [e for e in entries if os.path.isfile(os.path.join(path, e))]
            return dirs, files
        except: return [], []
    @staticmethod
    def translatePath(p):
        if "packages" in p: return os.path.join(os.path.dirname(__file__), "packages")
        return p.replace("special://home", os.path.dirname(__file__))

sys.modules['xbmcvfs'] = MockXbmcvfs

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'service.sudosync')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'service.sudosync', 'resources', 'lib')))
import sudosync_core

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()
pem_pub = public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')

def sign_payload(data):
    return private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())

def gen_zip(files, version="1.2.0", corrupt=False, add_mode=None):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w") as zf:
        if not files: zf.writestr("service.sudosync/dummy.txt", b"1")
        for fname, content in files.items():
            zf.writestr(fname, content)
            if add_mode:
                info = zf.getinfo(fname)
                info.external_attr = add_mode << 16
        if version is not None:
            zf.writestr("service.sudosync/addon.xml", f'<addon id="service.sudosync" version="{version}"></addon>')
    data = mem.getvalue()
    if corrupt:
        data = data[:len(data)//2]
    return data

def build_signed_zip(files, version="1.2.0", corrupt=False, add_mode=None):
    payload = gen_zip(files, version=version, corrupt=corrupt, add_mode=add_mode)
    return payload + sign_payload(payload)

class TestEtap2SignedUpdateFailures(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_key = sudosync_core.PUBLIC_KEY_PEM
        sudosync_core.PUBLIC_KEY_PEM = pem_pub

    def tearDown(self):
        sudosync_core.PUBLIC_KEY_PEM = self.original_key
        self.tmpdir.cleanup()

    def test_signed_update_failures(self):
        # invalid signature
        p = os.path.join(self.tmpdir.name, "bad_sig.zip")
        with open(p, "wb") as f: f.write(gen_zip({}) + b"X" * 256)
        with self.assertRaisesRegex(ValueError, "Odmowa.*podpis"): sudosync_core._validate_update_zip(p, "1.2.0")
        
        # modified payload
        p = os.path.join(self.tmpdir.name, "mod_payload.zip")
        payload = gen_zip({})
        payload_mod = payload[:-1] + bytes([payload[-1] ^ 1])
        with open(p, "wb") as f: f.write(payload_mod + sign_payload(payload))
        with self.assertRaisesRegex(ValueError, "Odmowa.*podpis"): sudosync_core._validate_update_zip(p, "1.2.0")

        # path traversal
        p = os.path.join(self.tmpdir.name, "traversal.zip")
        with open(p, "wb") as f: f.write(build_signed_zip({"../etc/passwd": b"1"}))
        with self.assertRaisesRegex(ValueError, "Niedozwolona"): sudosync_core._validate_update_zip(p, "1.2.0")
        
        # symlink
        p = os.path.join(self.tmpdir.name, "symlink.zip")
        with open(p, "wb") as f: f.write(build_signed_zip({"service.sudosync/symlink": b"t"}, add_mode=(0xA000 | 0o777)))
        with self.assertRaisesRegex(ValueError, "dowi.zany"): sudosync_core._validate_update_zip(p, "1.2.0")

        # duplicate member
        p = os.path.join(self.tmpdir.name, "dup.zip")
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w") as zf:
            zf.writestr("service.sudosync/test.txt", b"A")
            zf.writestr("service.sudosync/test.txt", b"B")
            zf.writestr("service.sudosync/addon.xml", b'<addon id="service.sudosync" version="1.2.0"></addon>')
        payload = mem.getvalue()
        with open(p, "wb") as f: f.write(payload + sign_payload(payload))
        with self.assertRaisesRegex(ValueError, "zduplikowan"): sudosync_core._validate_update_zip(p, "1.2.0")

        # file count
        p = os.path.join(self.tmpdir.name, "too_many.zip")
        files = {f"service.sudosync/f{i}": b"1" for i in range(sudosync_core.UPDATE_MAX_FILES + 1)}
        with open(p, "wb") as f: f.write(build_signed_zip(files))
        with self.assertRaisesRegex(ValueError, "nieprawid.ow.*liczb"): sudosync_core._validate_update_zip(p, "1.2.0")

        # member size
        orig_max = sudosync_core.UPDATE_MAX_MEMBER_BYTES
        sudosync_core.UPDATE_MAX_MEMBER_BYTES = 100
        try:
            p = os.path.join(self.tmpdir.name, "big_member.zip")
            with open(p, "wb") as f: f.write(build_signed_zip({"service.sudosync/big": b"X" * 150}))
            with self.assertRaisesRegex(ValueError, "przekracza limit rozmiaru: service.sudosync/big"): sudosync_core._validate_update_zip(p, "1.2.0")
        finally:
            sudosync_core.UPDATE_MAX_MEMBER_BYTES = orig_max

        # uncompressed size
        orig_max_u = sudosync_core.UPDATE_MAX_UNCOMPRESSED_BYTES
        sudosync_core.UPDATE_MAX_UNCOMPRESSED_BYTES = 100
        try:
            p = os.path.join(self.tmpdir.name, "big_unc.zip")
            with open(p, "wb") as f: f.write(build_signed_zip({"service.sudosync/f1": b"X"*60, "service.sudosync/f2": b"Y"*60}))
            with self.assertRaisesRegex(ValueError, "rozpakowanych danych przekracza"): sudosync_core._validate_update_zip(p, "1.2.0")
        finally:
            sudosync_core.UPDATE_MAX_UNCOMPRESSED_BYTES = orig_max_u

        # ZIP size
        p = os.path.join(self.tmpdir.name, "big_zip.zip")
        with patch('os.path.getsize', return_value=sudosync_core.UPDATE_MAX_BYTES + 10):
            with self.assertRaisesRegex(ValueError, "przekracza limit rozmiaru"): sudosync_core._validate_update_zip(p, "1.2.0")

        # corrupt ZIP
        p = os.path.join(self.tmpdir.name, "corrupt.zip")
        with open(p, "wb") as f: f.write(build_signed_zip({}, corrupt=True))
        with self.assertRaises(zipfile.BadZipFile): sudosync_core._validate_update_zip(p, "1.2.0")

        # brak addon.xml
        p = os.path.join(self.tmpdir.name, "no_addon.zip")
        with open(p, "wb") as f: f.write(build_signed_zip({"service.sudosync/test.txt": b"1"}, version=None))
        with self.assertRaisesRegex(ValueError, "Pakiet nie zawiera|nieprawid.ow. liczb"): sudosync_core._validate_update_zip(p, "1.2.0")

        # mismatch version
        p = os.path.join(self.tmpdir.name, "mismatch.zip")
        with open(p, "wb") as f: f.write(build_signed_zip({}, version="1.1.0"))
        with self.assertRaisesRegex(ValueError, "nie zgadza si."): sudosync_core._validate_update_zip(p, "1.2.0")


class TestEtap2InstallLatestUpdate(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_key = sudosync_core.PUBLIC_KEY_PEM
        sudosync_core.PUBLIC_KEY_PEM = pem_pub
        self.patcher = patch('sudosync_core._addon_profile_path', return_value=self.tmpdir.name)
        self.patcher.start()

    def tearDown(self):
        sudosync_core.PUBLIC_KEY_PEM = self.original_key
        self.patcher.stop()
        self.tmpdir.cleanup()

    @patch('sudosync_core.addon_settings', return_value={"client_name": "T", "base_path": "smb://test/"})
    @patch('sudosync_core.find_latest_update')
    @patch('sudosync_core.xbmcaddon.Addon')
    def test_install_update(self, mock_addon, mock_find, mock_settings):
        # Unverified zip -> brak instalacji i rzucenie bledu
        remote_zip = os.path.join(self.tmpdir.name, "remote_bad.zip")
        with open(remote_zip, "wb") as f: f.write(gen_zip({}) + b"X"*256)
        mock_find.return_value = {"available": True, "path": remote_zip, "filename": "remote_bad.zip", "version": "1.2.0"}
        
        target_dir = os.path.join(self.tmpdir.name, "service.sudosync")
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(target_dir, "addon.xml"), "w") as f: f.write("OLD")
        
        addon_info_mock = MagicMock()
        addon_info_mock.getAddonInfo.return_value = target_dir
        mock_addon.return_value = addon_info_mock

        with patch('sudosync_core._copy_vfs_to_local', side_effect=lambda a,b: shutil.copy(a,b)):
            with self.assertRaisesRegex(ValueError, "Odmowa.*podpis"):
                sudosync_core.install_latest_update(show_dialogs=False)
        # Zwykly zip nie zostal potraktowany jako zainstalowany! Katalog musi zostac nienaruszony
        with open(os.path.join(target_dir, "addon.xml"), "r") as f: self.assertEqual(f.read(), "OLD")

        # Poprawny pakiet -> prawidlowy przeplyw!
        remote_zip2 = os.path.join(self.tmpdir.name, "remote_good.zip")
        with open(remote_zip2, "wb") as f: f.write(build_signed_zip({}))
        mock_find.return_value = {"available": True, "path": remote_zip2, "filename": "remote_good.zip", "version": "1.2.0"}

        with patch('sudosync_core._copy_vfs_to_local', side_effect=lambda a,b: shutil.copy(a,b)):
            res = sudosync_core.install_latest_update(show_dialogs=False)
            self.assertTrue(res.get("installed"))
            # Kod powinnien byc zaktualizowany
            xml = os.path.join(target_dir, "addon.xml")
            self.assertTrue(os.path.exists(xml))
            with open(xml, "r") as f:
                self.assertIn('version="1.2.0"', f.read())

class TestEtap2FailClosedUpdate(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.patcher = patch('sudosync_core.addon_settings', return_value={"client_name": "T", "base_path": self.tmpdir.name})
        self.patcher.start()
        self.patcher2 = patch('sudosync_core.get_or_create_client_id', return_value="CLI")
        self.patcher2.start()

    def tearDown(self):
        self.patcher2.stop()
        self.patcher.stop()
        self.tmpdir.cleanup()
        
    def test_update_fail_closed(self):
        path = sudosync_core._shared_config_path(self.tmpdir.name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Baza ma wszystko wymagane by byc poprawna
        orig = '{"network_settings": {}, "initialization": {"base_client_id": "STARA"}}'
        def ok_mutator(cfg): return cfg
        
        # 1. Invalid JSON na pliku
        with open(path, "w", encoding="utf-8") as f: f.write("{invalid")
        with self.assertRaisesRegex(IOError, "invalid JSON"): sudosync_core.update_shared_config(ok_mutator)
        with open(path, "r", encoding="utf-8") as f: self.assertEqual(f.read(), "{invalid")

        # 2. unreadable file
        with open(path, "w", encoding="utf-8") as f: f.write(orig)
        with patch('sudosync_core.xbmcvfs.File', side_effect=OSError("Brak dostepu")):
            with self.assertRaises(IOError): sudosync_core.update_shared_config(ok_mutator)
        with open(path, "r", encoding="utf-8") as f: self.assertEqual(f.read(), orig)
        
        # 3. empty / uszkodzony plik (nie moze byc traktowany jak brak, bo to fail closed)
        with open(path, "w", encoding="utf-8") as f: f.write("")
        with self.assertRaisesRegex(IOError, "pusty"): sudosync_core.update_shared_config(ok_mutator)
        with open(path, "r", encoding="utf-8") as f: self.assertEqual(f.read(), "")

        # 4. missing network_settings na pliku (baza wczesniejsza to miala, ale jakims cudem zewnetrzny blad pozbawil klucza)
        with open(path, "w", encoding="utf-8") as f: f.write('{"initialization": {"base_client_id": "STARA"}}')
        with self.assertRaisesRegex(IOError, "missing network_settings"): sudosync_core.update_shared_config(ok_mutator)
        with open(path, "r", encoding="utf-8") as f: self.assertEqual(f.read(), '{"initialization": {"base_client_id": "STARA"}}')

        # 5. invalid data types na pliku (calosc to nie slownik)
        with open(path, "w", encoding="utf-8") as f: f.write('[]')
        with self.assertRaisesRegex(IOError, "invalid data types"): sudosync_core.update_shared_config(ok_mutator)
        with open(path, "r", encoding="utf-8") as f: self.assertEqual(f.read(), '[]')
        
        # 5a. invalid data types w kluczach wewnetrznych (network_settings to string)
        with open(path, "w", encoding="utf-8") as f: f.write('{"network_settings": "ZLE", "initialization": {}}')
        with self.assertRaisesRegex(IOError, "missing network_settings"): sudosync_core.update_shared_config(ok_mutator)
        with open(path, "r", encoding="utf-8") as f: self.assertEqual(f.read(), '{"network_settings": "ZLE", "initialization": {}}')
        
        # 5b. invalid data types w kluczach wewnetrznych (initialization to string przed mutacja)
        with open(path, "w", encoding="utf-8") as f: f.write('{"network_settings": {}, "initialization": "ZLE"}')
        with self.assertRaisesRegex(IOError, "missing initialization"): sudosync_core.update_shared_config(ok_mutator)
        with open(path, "r", encoding="utf-8") as f: self.assertEqual(f.read(), '{"network_settings": {}, "initialization": "ZLE"}')

        # 6. invalid legacy config
        with open(path, "w", encoding="utf-8") as f: f.write('{"sudosync_id_prefix": "OLD", "network_settings": {}, "initialization": {}}')
        with self.assertRaisesRegex(IOError, "legacy"): sudosync_core.update_shared_config(ok_mutator)
        with open(path, "r", encoding="utf-8") as f: self.assertEqual(f.read(), '{"sudosync_id_prefix": "OLD", "network_settings": {}, "initialization": {}}')

        # 7. mutator wprowadzajacy bledne dane (np. usuniecie initialization, zepsucie slownika)
        with open(path, "w", encoding="utf-8") as f: f.write(orig)
        def bad_mutator(cfg):
            del cfg["initialization"]
            return True
        with self.assertRaisesRegex(ValueError, "missing initialization"): sudosync_core.update_shared_config(bad_mutator)
        with open(path, "r", encoding="utf-8") as f: self.assertEqual(f.read(), orig)
        
        # 8. mutator psujacy typ initialization (np. zamiana na string)
        def bad_mutator2(cfg):
            cfg["initialization"] = "ZLE"
            return True
        with self.assertRaisesRegex(ValueError, "missing initialization"): sudosync_core.update_shared_config(bad_mutator2)
        with open(path, "r", encoding="utf-8") as f: self.assertEqual(f.read(), orig)
        
        # 9. mutator psujacy typ network_settings (np. zamiana na string po mutacji)
        def bad_mutator3(cfg):
            cfg["network_settings"] = "ZLE"
            return True
        with self.assertRaisesRegex(ValueError, "missing network_settings"): sudosync_core.update_shared_config(bad_mutator3)
        with open(path, "r", encoding="utf-8") as f: self.assertEqual(f.read(), orig)


class TestEtap2SudoSyncIDBaseOnly(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
    def tearDown(self):
        self.tmpdir.cleanup()

    def write_cfg(self, data):
        path = sudosync_core._shared_config_path(self.tmpdir.name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
            
    def read_cfg(self):
        path = sudosync_core._shared_config_path(self.tmpdir.name)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @patch('sudosync_core.addon_settings', return_value={"sudosync_id_prefix": "EVIL", "client_name": "N", "base_path": "smb://t/"})
    def test_base_only_id(self, mock_settings):
        sudosync_core.xbmcaddon.Addon().getSetting.side_effect = lambda k: "EVIL" if k == "sudosync_id_prefix" else ""
        
        # 1. non-base bez ID -> RuntimeError
        self.write_cfg({"network_settings": {}, "initialization": {"base_client_id": "INNA_BAZA"}})
        with patch('sudosync_core.get_or_create_client_id', return_value="JA_NIE_BAZA"):
            with self.assertRaisesRegex(RuntimeError, "Nie ustalono"):
                sudosync_core.get_or_sync_network_id_and_alias(self.tmpdir.name)
                
        # 2. base bez ID -> moze utworzyc, EVIL wejdzie
        self.write_cfg({"network_settings": {}, "initialization": {"base_client_id": "JA_BAZA"}})
        with patch('sudosync_core.get_or_create_client_id', return_value="JA_BAZA"):
            res = sudosync_core.get_or_sync_network_id_and_alias(self.tmpdir.name)
            self.assertTrue(res.startswith("NET-") or res.startswith("EVIL") or res.startswith("EV"))
            
        # 3. non-base -> korzysta ze wspolnego (wraca DOBRY), nie nadpisuje
        self.write_cfg({"sudosync_network_id": "NET", "sudosync_network_alias": "DOBRY", "network_settings": {}, "initialization": {"base_client_id": "INNA_BAZA"}})
        with patch('sudosync_core.get_or_create_client_id', return_value="JA_NIE_BAZA"):
            res = sudosync_core.get_or_sync_network_id_and_alias(self.tmpdir.name)
            cfg = self.read_cfg()
            self.assertEqual(cfg["sudosync_network_alias"], "DOBRY")

        # 4. base -> moze zmienic wspolny alias (jesli lokalny prefiks sie zmieni, on ma wladze)
        self.write_cfg({"sudosync_network_id": "NET", "sudosync_network_alias": "STARY", "network_settings": {}, "initialization": {"base_client_id": "JA_BAZA"}})
        with patch('sudosync_core.get_or_create_client_id', return_value="JA_BAZA"):
            res = sudosync_core.get_or_sync_network_id_and_alias(self.tmpdir.name)
            cfg = self.read_cfg()
            self.assertEqual(cfg["sudosync_network_alias"], "EVIL")

class TestEtap2InitialSyncBootstrappedAndResume(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.patcher = patch('sudosync_core._addon_profile_path', return_value=self.tmpdir.name)
        self.patcher.start()
        sudosync_core._clear_initial_sync_session()

    def tearDown(self):
        sudosync_core._clear_initial_sync_session()
        self.patcher.stop()
        self.tmpdir.cleanup()
        
    @patch('sudosync_core.is_initial_write_guard_armed', return_value=True)
    @patch('sudosync_core.sync_initial_base_selection', return_value={"initialization": {"base_client_id": "BASE"}})
    @patch('sudosync_core.get_or_create_client_id', return_value="PEER")
    @patch('sudosync_core.addon_settings', return_value={"client_name": "TestClient", "base_path": "smb://test/"})
    @patch('sudosync_core.collect_and_write', return_value={"remote_path": "smb://test/snapshot.json"})
    @patch('sudosync_core._read_vfs_json', return_value={})
    @patch('sudosync_core._write_vfs_json')
    @patch('sudosync_core._get_secure_local_identity_map', return_value={})
    @patch('sudosync_core._apply_one_planned_item')
    def test_bootstrapped_and_resume(self, mock_apply, mock_secure_map, mock_write_vfs, mock_read_vfs, mock_collect, mock_settings, mock_client_id, mock_sync_base, mock_guard):
        items = [{"type": "movie", "display": "A"}, {"type": "movie", "display": "B"}, {"type": "movie", "display": "C"}]
        
        reg_file = os.path.join(self.tmpdir.name, "live_registry.json")
        def get_bootstrapped():
            if not os.path.exists(reg_file): return False
            with open(reg_file) as f: return json.load(f).get("bootstrapped", False)
            
        def mock_apply_func(item, sm):
            if item["display"] == "B": raise KeyboardInterrupt()
            return True
        mock_apply.side_effect = mock_apply_func
        
        with patch('sudosync_core.run_dry_run', return_value={"planned_changes": {"PEER": copy.deepcopy(items)}, "generated_at": "now"}):
            with self.assertRaises(KeyboardInterrupt):
                sudosync_core.apply_initial_sync()
                
        self.assertFalse(get_bootstrapped())
        session = sudosync_core._load_initial_sync_session()
        self.assertEqual(session["applied_indexes"], [1])
        
        mock_apply.reset_mock()
        mock_apply.side_effect = lambda i, m: True
        with patch('sudosync_core.run_dry_run', return_value={"planned_changes": {"PEER": copy.deepcopy(items)}, "generated_at": "now"}):
            rep = sudosync_core.apply_initial_sync()
            
        self.assertTrue(rep["completed"])
        applied = [c[0][0]["display"] for c in mock_apply.call_args_list]
        self.assertEqual(applied, ["B", "C"])
        self.assertIsNone(sudosync_core._load_initial_sync_session())
        self.assertTrue(get_bootstrapped())

    @patch('sudosync_core.is_initial_write_guard_armed', return_value=True)
    @patch('sudosync_core.sync_initial_base_selection', return_value={"initialization": {"base_client_id": "BASE"}})
    @patch('sudosync_core.get_or_create_client_id', return_value="PEER")
    @patch('sudosync_core.addon_settings', return_value={"client_name": "TestClient", "base_path": "smb://test/"})
    @patch('sudosync_core.collect_and_write', return_value={"remote_path": "smb://test/snapshot.json"})
    @patch('sudosync_core._read_vfs_json', return_value={})
    @patch('sudosync_core._write_vfs_json')
    @patch('sudosync_core._get_secure_local_identity_map', return_value={})
    @patch('sudosync_core._apply_one_planned_item')
    def test_initial_sync_single_element_error(self, mock_apply, mock_secure_map, mock_write_vfs, mock_read_vfs, mock_collect, mock_settings, mock_client_id, mock_sync_base, mock_guard):
        items = [{"type": "movie", "display": "A"}, {"type": "movie", "display": "B"}, {"type": "movie", "display": "C"}]
        
        reg_file = os.path.join(self.tmpdir.name, "live_registry.json")
        def get_bootstrapped():
            if not os.path.exists(reg_file): return False
            with open(reg_file) as f: return json.load(f).get("bootstrapped", False)
            
        def mock_apply_func(item, sm):
            if item["display"] == "B": raise ValueError("Kontrolowany blad podczas symulacji bazy")
            return True
        mock_apply.side_effect = mock_apply_func
        
        with patch('sudosync_core.run_dry_run', return_value={"planned_changes": {"PEER": copy.deepcopy(items)}, "generated_at": "now"}):
            with patch('sudosync_core._mark_initialization_completed_if_converged') as mock_mark:
                with self.assertRaisesRegex(RuntimeError, "przerwana"):
                    sudosync_core.apply_initial_sync()
                self.assertFalse(mock_mark.called)
            
        self.assertFalse(get_bootstrapped())
        session = sudosync_core._load_initial_sync_session()
        self.assertEqual(session["applied_indexes"], [1]) # Zgodnie z formatowaniem, to indeksy zaczynają się od 1. item A ma index 1.
        
        # Wznowienie - B tym razem się uda
        mock_apply.reset_mock()
        mock_apply.side_effect = lambda i, m: True
        with patch('sudosync_core.run_dry_run', return_value={"planned_changes": {"PEER": copy.deepcopy(items)}, "generated_at": "now"}):
            rep = sudosync_core.apply_initial_sync()
            
        self.assertTrue(rep["completed"])
        applied = [c[0][0]["display"] for c in mock_apply.call_args_list]
        self.assertEqual(applied, ["B", "C"])
        self.assertIsNone(sudosync_core._load_initial_sync_session())
        self.assertTrue(get_bootstrapped())


class TestEtap2RollbackRealistic(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.patcher = patch('sudosync_core._addon_profile_path', return_value=self.tmpdir.name)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmpdir.cleanup()
        
    def test_rollback_realistic(self):
        old_nfo = os.path.join(self.tmpdir.name, "old.nfo")
        old_nfo_bak = os.path.join(self.tmpdir.name, "old.nfo.bak")
        new_nfo = os.path.join(self.tmpdir.name, "new.nfo")
        
        with open(old_nfo, "w") as f: f.write("MODIFIED")
        with open(old_nfo_bak, "w") as f: f.write("ORIGINAL")
        with open(new_nfo, "w") as f: f.write("NEW")
        
        manifest_path = os.path.join(self.tmpdir.name, "assign_ids_manifest.json")
        manifest_data = {
            "modified": [
                {"file": old_nfo, "backup": old_nfo_bak, "created": False},
                {"file": new_nfo, "created": True}
            ]
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)
            
        res = sudosync_core.rollback_sudosync_ids(manifest_path)
        self.assertEqual(res["rolled_back"], 2)
        
        self.assertFalse(os.path.exists(new_nfo))
        self.assertFalse(os.path.exists(old_nfo_bak))
        self.assertTrue(os.path.exists(old_nfo))
        with open(old_nfo, "r") as f:
            self.assertEqual(f.read(), "ORIGINAL")

if __name__ == '__main__':
    unittest.main()
