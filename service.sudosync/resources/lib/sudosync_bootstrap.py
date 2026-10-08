# -------------------------------------------------------------------------
# SudoSync for Kodi
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# -------------------------------------------------------------------------
import os
import time
import json
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon

ADDON_ID = "service.sudosync"

def log(msg, level=xbmc.LOGINFO):
    xbmc.log("[SudoSync Bootstrap] {}".format(msg), level)

def get_addon_setting(key):
    return xbmcaddon.Addon(ADDON_ID).getSetting(key)

def set_addon_setting(key, value):
    xbmcaddon.Addon(ADDON_ID).setSetting(key, str(value))

def get_base_path():
    path = get_addon_setting("base_path").strip()
    return path

def set_base_path(path):
    set_addon_setting("base_path", path)
    log("Ustalono nową ścieźkę bazową: {}".format(path))

def test_vfs_rw(test_dir):
    try:
        if not xbmcvfs.exists(test_dir):
            if not xbmcvfs.mkdirs(test_dir):
                return False, "Nie moźna utworzyć katalogu .SudoSync"
        
        test_file = test_dir + "rw_test.tmp"
        f = xbmcvfs.File(test_file, 'w')
        f.write("test")
        f.close()
        
        f = xbmcvfs.File(test_file, 'r')
        data = f.read()
        f.close()
        
        xbmcvfs.delete(test_file)
        
        if data != "test":
            return False, "Błąd weryfikacji zapisu/odczytu"
            
        return True, "OK"
    except Exception as exc:
        return False, str(exc)

def _read_json_file(filepath):
    if not xbmcvfs.exists(filepath):
        return "NOT_FOUND", None
    try:
        f = xbmcvfs.File(filepath, "r")
        data = f.read()
        f.close()
    except Exception as exc:
        log("Nie można odczytać JSON {}: {}".format(filepath, exc), xbmc.LOGERROR)
        return "IO_ERROR", None

    try:
        import json
        return "VALID", json.loads(data)
    except Exception as exc:
        log("Nie można sparsować JSON {}: {}".format(filepath, exc), xbmc.LOGERROR)
        return "INVALID", None

def _write_json_file(filepath, obj):
    try:
        import json
        data = json.dumps(obj, indent=2, sort_keys=True)
        # Bezpieczny zapis przez plik tymczasowy i kopię zapasową
        tmp_file = filepath + ".tmp"
        bak_file = filepath + ".bak"
        
        f = xbmcvfs.File(tmp_file, 'w')
        result = f.write(data)
        f.close()
        
        if not result:
            log("Nie udało się zapisać pełnych danych do .tmp dla {}".format(filepath), xbmc.LOGERROR)
            return False

        if xbmcvfs.exists(filepath):
            if xbmcvfs.exists(bak_file):
                xbmcvfs.delete(bak_file)
            xbmcvfs.copy(filepath, bak_file)
            xbmcvfs.delete(filepath)
            
        if xbmcvfs.rename(tmp_file, filepath):
            if xbmcvfs.exists(tmp_file):
                xbmcvfs.delete(tmp_file)
            return True
        else:
            if xbmcvfs.exists(bak_file):
                xbmcvfs.rename(bak_file, filepath)
            return False
            
    except Exception as exc:
        log("Cannot write JSON {}: {}".format(filepath, exc), xbmc.LOGERROR)
        return False

def read_sudosync_cfg(base_path):
    cfg_path = base_path + "SudoSync.cfg"
    return _read_json_file(cfg_path)

def write_sudosync_cfg(base_path, config_data):
    cfg_path = base_path + "SudoSync.cfg"
    return _write_json_file(cfg_path, config_data)

def update_sudosync_cfg_network_settings(base_path, enabled, prefix):
    """Update network settings under a shared inter-client lock.

    Invalid/unreadable configuration is never replaced or repaired implicitly.
    """
    cfg_path = base_path.rstrip("/") + "/SudoSync.cfg"
    lock_dir = cfg_path + ".lockdir"
    lock_info = lock_dir + "/lock_info.json"
    lock_id = "{}".format(time.time())
    start = time.time()

    while True:
        if xbmcvfs.mkdirs(lock_dir):
            try:
                _write_json_file(lock_info, {"owner": lock_id, "created_at": time.time()})
            except Exception:
                try:
                    xbmcvfs.rmdir(lock_dir)
                except Exception:
                    pass
                raise
            break

        if time.time() - start > 15:
            raise RuntimeError("Nie można uzyskać blokady SudoSync.cfg w ciągu 15 sekund.")

        try:
            status, info = _read_json_file(lock_info)
            created_at = float((info or {}).get("created_at") or 0)
            if status == "VALID" and created_at and time.time() - created_at > 60:
                xbmcvfs.delete(lock_info)
                xbmcvfs.rmdir(lock_dir)
                continue
        except Exception:
            pass
        xbmc.sleep(200)

    try:
        status, cfg = _read_json_file(cfg_path)
        if status != "VALID" or not isinstance(cfg, dict):
            raise RuntimeError("SudoSync.cfg jest nieczytelny lub nieprawidłowy; zapis został zablokowany.")

        net = cfg.get("network_settings")
        if not isinstance(net, dict):
            raise RuntimeError("Brak prawidłowej sekcji network_settings w SudoSync.cfg.")

        if not isinstance(enabled, bool) or not isinstance(prefix, str):
            raise ValueError("Nieprawidłowy typ ustawień sieciowych.")

        net["sudosync_id_enabled"] = enabled
        net["sudosync_id_prefix"] = prefix
        cfg["network_settings"] = net
        if not write_sudosync_cfg(base_path, cfg):
            raise IOError("Nie udało się zapisać SudoSync.cfg.")
        return cfg
    finally:
        try:
            if xbmcvfs.exists(lock_info):
                xbmcvfs.delete(lock_info)
            xbmcvfs.rmdir(lock_dir)
        except Exception:
            pass

def is_legacy_installation(base_path):
    # Sprawdzamy czy istnieje system/config.json oraz clients/
    sys_config = base_path + "system/config.json"
    clients_dir = base_path + "clients/"
    return xbmcvfs.exists(sys_config) and xbmcvfs.exists(clients_dir)

def run_migration_wizard(base_path):
    xbmcgui.Dialog().ok(
        "SudoSync - Migracja",
        "Wykryto istniejącą instalację starszej wersji SudoSync w wybranym folderze.\n\n"
        "Dotychczasowe dane zostaną zachowane. Ustawienia zostaną wyodrębnione do nowego pliku SudoSync.cfg.",
    )

    status, sys_config = _read_json_file(base_path + "system/config.json")
    if status == "IO_ERROR":
        xbmcgui.Dialog().ok(
            "SudoSync - migracja zatrzymana",
            "Nie można odczytać starego system/config.json. Migracja została zatrzymana, aby nie nadpisać konfiguracji.",
        )
        return False
    if status == "INVALID":
        xbmcgui.Dialog().ok(
            "SudoSync - migracja zatrzymana",
            "Stary system/config.json jest nieprawidłowym JSON-em. Migracja została zatrzymana, aby nie utracić ustawień.",
        )
        return False
    if not isinstance(sys_config, dict):
        xbmcgui.Dialog().ok(
            "SudoSync - migracja zatrzymana",
            "Stary system/config.json ma nieprawidłową strukturę. Migracja została zatrzymana.",
        )
        return False

    old_net = sys_config.get("network_settings", {})
    if old_net is not None and not isinstance(old_net, dict):
        xbmcgui.Dialog().ok(
            "SudoSync - migracja zatrzymana",
            "Sekcja network_settings w starym config.json ma nieprawidłową strukturę.",
        )
        return False

    addon = xbmcaddon.Addon(ADDON_ID)
    old_net = old_net or {}
    sudosync_id_enabled = old_net.get(
        "sudosync_id_enabled",
        addon.getSetting("sudosync_id_enabled").strip().lower() == "true",
    )
    sudosync_id_prefix = old_net.get(
        "sudosync_id_prefix",
        addon.getSetting("sudosync_id_prefix").strip() or "NAS",
    )
    if not isinstance(sudosync_id_enabled, bool) or not isinstance(sudosync_id_prefix, str):
        xbmcgui.Dialog().ok(
            "SudoSync - migracja zatrzymana",
            "Stare ustawienia SudoSync ID mają nieprawidłowe typy.",
        )
        return False

    new_cfg = {
        "format": "SudoSync configuration",
        "schema_version": 1,
        "configuration": {
            "completed": True,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "network_settings": {
            "sudosync_id_enabled": sudosync_id_enabled,
            "sudosync_id_prefix": str(sudosync_id_prefix),
        },
    }
    if not write_sudosync_cfg(base_path, new_cfg):
        xbmcgui.Dialog().ok("SudoSync - błąd", "Nie udało się zapisać migrowanej konfiguracji.")
        return False

    xbmcgui.Dialog().notification(
        "SudoSync - migracja",
        "Migracja zakończona pomyślnie.",
        xbmcgui.NOTIFICATION_INFO,
        5000,
    )
    return True

def run_new_config_wizard(base_path):
    dialog = xbmcgui.Dialog()
    if not dialog.yesno("SudoSync - Konfigurator sieciowy", "Skonfigurujemy teraz nowe środowisko synchronizacji SudoSync dla Twojej domeny.\n\nCzy chcesz domyślnie uźywać niezawodnego identyfikatora 'SudoSync ID' dla wideo pozbawionych standardowych ID (IMDb/TMDb)?", yeslabel="Tak (Zalecane)", nolabel="Nie, uźyj IMDb"):
        sudosync_id_enabled = False
        sudosync_id_prefix = ""
    else:
        sudosync_id_enabled = True
        prefix = dialog.input("Podaj krĂłtki prefiks dla tej sieci (np. NAS lub DOM):", type=xbmcgui.INPUT_ALPHANUM)
        sudosync_id_prefix = prefix.strip() if prefix.strip() else "NAS"
        
    new_cfg = {
        "format": "SudoSync configuration",
        "schema_version": 1,
        "configuration": {
            "completed": True,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        },
        "network_settings": {
            "sudosync_id_enabled": sudosync_id_enabled,
            "sudosync_id_prefix": sudosync_id_prefix
        }
    }
    
    if not write_sudosync_cfg(base_path, new_cfg):
        xbmcgui.Dialog().ok("Błąd", "Nie udało się zapisać nowej konfiguracji do SudoSync.cfg")
        return False
        
    dialog.ok("Sukces", "Ĺšrodowisko .SudoSync skonfigurowane poprawnie!\nTeraz synchronizacja moźe się rozpocząć.")
    return True

def apply_network_settings(cfg):
    net = cfg.get("network_settings", {})
    if not net:
        return
        
    remote_enabled = bool(net.get("sudosync_id_enabled", False))
    remote_prefix = str(net.get("sudosync_id_prefix") or "").strip()

    addon = xbmcaddon.Addon(ADDON_ID)
    local_enabled = addon.getSetting("sudosync_id_enabled").strip().lower() == "true"
    local_prefix = addon.getSetting("sudosync_id_prefix").strip()

    changed = False
    if local_enabled != remote_enabled:
        addon.setSetting("sudosync_id_enabled", "true" if remote_enabled else "false")
        changed = True
    if local_prefix != remote_prefix:
        addon.setSetting("sudosync_id_prefix", remote_prefix)
        changed = True

    if changed:
        log("Konfiguracja sieciowa SudoSync ID została wymuszona na lokalnym kliencie.")

def run_bootstrap():
    """Zwraca True, jeśli bootstrap zakończony i moźna przejść do logiki operacyjnej, False w przypadku wstrzymania/błędu."""
    log("Rozpoczęcie fazy BOOTSTRAP")
    base_path = get_base_path()
    
    # 1. USTALENIE BASE PATH
    # Jeźeli brak base_path LUB ścieźka to stara śmieciowa defaultowa domyślna SMB
    if not base_path or base_path == "smb://192.168.69.100/Wideo/.SudoSync/" or not base_path.endswith("/"):
        dialog = xbmcgui.Dialog()
        dialog.ok("SudoSync", "Musisz wskazać folder sieciowy (np. SMB/NFS), w ktĂłrym SudoSync będzie przechowywać wspĂłlną konfigurację i bazę dla wszystkich urządzeń Kodi w tej sieci.")
        
        selected_path = dialog.browse(3, "Wybierz katalog wspĂłłdzielony (np. Wideo)", "network")
        if not selected_path:
            log("User cancelled path selection.")
            return False
            
        selected_path = selected_path.replace('\\', '/')
        if not selected_path.endswith('/'):
            selected_path += '/'
            
        # Zabezpieczenie przed zagnieźdźaniem .SudoSync/.SudoSync
        if selected_path.endswith(".SudoSync/"):
            base_path = selected_path
        else:
            base_path = selected_path + ".SudoSync/"
            
        set_base_path(base_path)
        
    # 2. TEST DOSTĘPU I READ/WRITE
    log("Testowanie dostępu R/W do {}".format(base_path))
    success, msg = test_vfs_rw(base_path)
    if not success:
        xbmcgui.Dialog().ok("SudoSync - Brak Dostępu", "Nie udało się zapisać plikĂłw w wybranym folderze:\n{}\n\nSprawdĹş uprawnienia do zapisu lub wskaź inny udział w ustawieniach.".format(msg))
        return False
        
    # 3. SPRAWDZENIE SUDOSYNC.CFG
    status, cfg = read_sudosync_cfg(base_path)
    if status == "VALID":
        # WALIDACJA ISTNIEJĄCEGO SudoSync.cfg
        if not isinstance(cfg, dict):
            xbmcgui.Dialog().ok("Błąd SudoSync.cfg", "Plik SudoSync.cfg nie jest prawidłowym słownikiem JSON.")
            return False
        if cfg.get("schema_version") not in (1, 2):
            xbmcgui.Dialog().ok("Błąd SudoSync.cfg", "Nieobsługiwana wersja schematu (schema_version) w SudoSync.cfg.")
            return False
        if not isinstance(cfg.get("network_settings"), dict):
            xbmcgui.Dialog().ok("Błąd SudoSync.cfg", "Brak sekcji network_settings w SudoSync.cfg.")
            return False
        if not isinstance(cfg.get("network_settings", {}).get("sudosync_id_enabled"), bool):
            xbmcgui.Dialog().ok("Błąd SudoSync.cfg", "Zły typ danych w sudosync_id_enabled.")
            return False
        if not isinstance(cfg.get("network_settings", {}).get("sudosync_id_prefix"), str):
            xbmcgui.Dialog().ok("Błąd SudoSync.cfg", "Zły typ danych w sudosync_id_prefix.")
            return False
        if not cfg.get("configuration", {}).get("completed"):
            xbmcgui.Dialog().ok("Błąd SudoSync.cfg", "Konfiguracja w SudoSync.cfg nie jest oznaczona jako ukończona.")
            return False
            
        log("SudoSync.cfg poprawnie zweryfikowany. Aplikowanie ustawień sieciowych.")
        apply_network_settings(cfg)
        return True
    elif status in ("INVALID", "IO_ERROR"):
        import time
        corrupted_path = base_path + "SudoSync.cfg"
        backup_path = base_path + "SudoSync.cfg.corrupted_" + str(int(time.time()))
        if xbmcvfs.exists(corrupted_path):
            xbmcvfs.copy(corrupted_path, backup_path)
        xbmcgui.Dialog().ok("Błąd Krytyczny", "Plik SudoSync.cfg jest uszkodzony lub nieczytelny. Została utworzona kopia zapasowa. Napraw plik ręcznie lub usuń go, aby wymusić nową konfigurację.")
        return False
    else:
        # BRAK SUDOSYNC.CFG
        # 4. Sprawdzenie, czy to starsza instalacja
        if is_legacy_installation(base_path):
            log("Wykryto starszą instalację bez SudoSync.cfg -> MIGRATION WIZARD")
            if not run_migration_wizard(base_path):
                return False
        else:
            log("Brak starej instalacji -> NEW CONFIG WIZARD")
            if not run_new_config_wizard(base_path):
                return False
                
        # 5. PONOWNY ODCZYT I WALIDACJA PO WIZARDZIE
        status, cfg = read_sudosync_cfg(base_path)
        if status == "VALID" and cfg.get("configuration", {}).get("completed"):
            apply_network_settings(cfg)
            return True
            
        xbmcgui.Dialog().ok("Błąd Krytyczny", "Nie udało się odczytać SudoSync.cfg pomimo jego zapisu.")
        return False

def check_and_enforce_updates_before_bootstrap():
    """Install an available signed update before starting operational code.

    A failed update check/install is fail-closed: the service does not continue
    with an older installation when a candidate update cannot be safely handled.
    """
    from resources.lib.sudosync_core import check_for_update, install_latest_update

    base_path = get_base_path()
    if not base_path or base_path == "smb://192.168.69.100/Wideo/.SudoSync/":
        return False

    result = check_for_update(show_notification=False, manual=False)
    if result.get("error"):
        raise RuntimeError("Nie można bezpiecznie sprawdzić aktualizacji: {}".format(result["error"]))
    if not result.get("available"):
        return False

    installed = install_latest_update(show_dialogs=False)
    if not installed.get("installed"):
        raise RuntimeError(
            "Wykryto nowszą wersję {}, ale nie udało się jej bezpiecznie zainstalować.".format(
                result.get("version") or "nieznaną"
            )
        )

    xbmcgui.Dialog().notification(
        "SudoSync zaktualizowano",
        "Zainstalowano {}. Nowa wersja zostanie aktywowana po restarcie Kodi.".format(
            installed.get("version")
        ),
        xbmcgui.NOTIFICATION_INFO,
        10000,
    )
    return True

