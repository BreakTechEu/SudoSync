# SudoSync — trwały kontekst projektu

Ten plik jest krótką, trwałą pamięcią wymagań użytkownika. Przeczytaj go na
początku każdej sesji pracy. Szczegółowy przepływ użytkownika znajduje się w
[`V2_USER_FLOW.md`](V2_USER_FLOW.md), a projekt techniczny w
[`V2_DESIGN.md`](V2_DESIGN.md). Jeśli bieżąca prośba użytkownika coś zmienia,
nadrzędna jest bieżąca prośba; potem zaktualizuj te pliki.

## Cel i repozytorium

- Projekt: `BreakTechEu/SudoSync-Kodi-addon`.
- `master` jest docelową gałęzią główną dla v2.
- `v1-stable` to gałąź stabilnej wersji SudoSync 1.0.0 i jest tylko do odczytu.
- Rozwój v2 prowadzimy na `v2/rewrite-2026-10-10`, a do `master` integrujemy
  v2 uzgodnioną ścieżką przeglądu. Nie traktuj `master` jako gałęzi stabilnej wersji SudoSync 1.0.0 ani
  `v1-stable` jako celu zmian v2.
- Stan gałęzi, kodu i testów sprawdzaj na początku sesji — ten plik nie jest
  źródłem aktualnego statusu Git.
- Aktualizuj wydania i paczki ZIP na GitHubie tak, aby inne narzędzia AI miały dostęp do aktualnego stanu kodu i artefaktów.
- Audyt zewnętrzny wykonuj dopiero przed przekazaniem zmian do `master` albo
  przygotowaniem wtyczki do testu na rzeczywistym Kodi.

## Uzgodniony model użycia

- Stanowiska deweloperskie są oddalone od siebie o ponad 20 km i nigdy nie są
  używane jednocześnie. Pracę kontynuuje się na kolejnym stanowisku po
  przekazaniu zmian przez GitHub.
- Roman i docelowy użytkownik korzystają tylko z jednego Kodi naraz. Najpierw
  kończą pracę na jednym urządzeniu, potem uruchamiają następne.
- SudoSync działa jako usługa w tle Kodi, więc pozostałe urządzenia nie mają
  w tym czasie uruchomionej usługi SudoSync.
- Ochrona przed równoczesnym uruchomieniem jest dodatkiem. Nie projektuj jej
  jako warunku rozpoczęcia lub ukończenia zwykłego przepływu. Nie wracaj do
  wielokrotnego pytania, czy inne urządzenia pracują w tle — użytkownik już
  określił zasadę pracy jednym Kodi.
- Weryfikacja na rzeczywistych urządzeniach jest sekwencyjna: wykonać zmianę
  na jednym Kodi, zakończyć jego pracę, uruchomić kolejne Kodi i sprawdzić
  rezultat. Nie wymagać fizycznej równoczesnej pracy dwóch Kodi.

## Zachowanie wtyczki

- Szczegóły pierwszego uruchomienia, `SudoSync.cfg`, konfiguratora, migracji
  i aktualizacji są opisane w `docs/V2_USER_FLOW.md`. Traktuj ten dokument
  jako wymagania użytkownika, a nie sugestię.
- Ścieżkę udziału wybiera się selektorem katalogu Kodi; użytkownik nie ma
  ręcznie przepisywać adresu SMB/NFS. Plik wspólny to
  `<base_path>/SudoSync.cfg`.
- Konfiguracja sieciowa jest wspólna. ID klienta, nazwa i ustawienia
  konkretnego Kodi pozostają lokalne i nie mogą być kopiowane przez plik
  wspólny.
- Aktualizacje są sprawdzane na GitHub Releases (`BreakTechEu/SudoSync-Kodi-addon`) najwyżej raz na dobę (lub ręcznie w ustawieniach) i instalowane wyłącznie po jawnej zgodzie użytkownika, albo instalowane ręcznie ze wskazanego przez użytkownika pliku `.zip`. Wycofano dawny mechanizm aktualizacji ze wspólnego folderu `.SudoSync` na NAS.
- W `SudoSync.cfg` zapisywana jest minimalna wymagana wersja wtyczki w sieci (`min_addon_version`). Urządzenie ze starszą wersją wtyczki jest blokowane przy starcie (oraz podczas odświeżania dzierżawy sesji) do czasu zaktualizowania wtyczki.
- Synchronizowane pola: licznik odtworzeń, data ostatniego odtworzenia,
  pozycja wznowienia i ocena użytkownika dla istniejących filmów i odcinków.
- Zmiany biblioteki wykonuj wyłącznie przez Kodi JSON-RPC. Nigdy nie edytuj
  `MyVideos*.db` bezpośrednio.
- Dopasowuj po silnych identyfikatorach z uwzględnieniem rodzaju medium.
  Tytuł, rok, ścieżka i lokalny ID Kodi same nie wystarczają. Nie dodawaj
  zdalnych pozycji do lokalnej biblioteki. Konflikty/niejednoznaczności
  raportuj i pomijaj zamiast zgadywać.
- Nie zakładaj, że każdy ma IMDb ID. Łącz obsługiwane mocne ID z Kodi
  JSON-RPC i `.nfo` (m.in. `<uniqueid type="…">`, filmowe `<tmdbid>` oraz
  legacy IMDb `<id>tt…</id>`). Jeśli brak mocnego ID i nie można przypisać
  SudoSync ID, pomiń rekord zamiast dopasowywać go po tytule.
- Przed zmianami wymagany jest podgląd, jawne zatwierdzenie, kopia i
  sprawdzenie wyniku. Podczas odtwarzania odraczaj zdalne zmiany.
- Zachowaj model LIVE silnika v1: każde Kodi publikuje własny snapshot, zmiany każdego
  pola mają wersję logiczną, a uruchomione Kodi uzgadnia je z peer snapshotami
  niezależnie od współbieżności startu. Zachowuj zwycięską wersję przy
  replikacji, aby uniknąć pętli. Użytkownik wymaga catch-up mimo długich
  odstępów między uruchomieniami. W sprawdzonym silniku v1 snapshot peer starszy niż
  7 dni powoduje błąd odczytu, który zatrzymuje cykl LIVE; nie przenoś tego
  ograniczenia do v2 bez zachowania catch-up po długiej przerwie.
- Każda paczka aktualizacji ZIP (pobrana z GitHub Releases lub wskazana lokalnie) musi przejść walidację struktury i manifestu `addon.xml` (`_validate_addon_zip_package`) przed rozpakowaniem do katalogu tymczasowego i atomową podmianą z kopią zapasową.

## Zasady współpracy

- Kontynuuj pracę w spójnych etapach; nie pytaj ponownie o ustalenia zapisane
  w tym pliku ani w `V2_USER_FLOW.md`.
- Zachowuj niezapisane zmiany. Przed synchronizacją sprawdź status i historię;
  nie używaj ślepego resetu i nie rozwiązuj konfliktów przez zgadywanie.
- W trakcie implementacji wykonuj zwykłe testy i własny przegląd kodu, gdy
  są potrzebne do zmiany. Nie przedstawiaj planu ani dokumentacji jako
  ukończonej wtyczki.
- Raportuj zmienione pliki, potwierdzone testy, commit/push i najbliższy
  pozostały etap. Wyraźnie odróżniaj stan lokalny od tego, co jest na GitHubie.


## Stan przekazania — 2026-10-12 (Zapis historyczny z etapu przejściowego)

- *(Zapis historyczny)*: Wstępna implementacja adaptera `KodiJsonRpcAdapter` i odczytu NFO. Wówczas `service.py` uruchamiał v2 jedynie do odzyskiwania, a pełny cykl v2 nie był jeszcze zintegrowany.
- *(Aktualizacja z 2026-10-16/17)*: Pełny cykl `v2_runtime.sync_cycle()` został włączony do `_execute_integrated_live_cycle()` w `service.py` i jest objęty testami jednostkowymi. Weryfikacja funkcjonalna w środowisku rzeczywistego Kodi jest prowadzona odrębnie przez Agenta Antigravity.



## Stan przekazania — 2026-10-16 / 2026-10-17

- Gałąź `v2/rewrite-2026-10-10` została wcześniej scalona do `master`; aktywny rozwój toczy się na `master` (`v1-stable` pozostaje tylko do odczytu).
- Domknięto pełny cykl synchronizacji i inicjalizacji w runtime v2 (`sudosync_v2/runtime.py`, `engine.py`, `planning.py`, `initialization.py`, `snapshot.py`):
  - `build_sync_plan` i `build_initialization_plan` dołączają `target_versions` do każdej zmiany, a `apply_plan_to_snapshot` aktualizuje lokalny snapshot wraz ze zwycięskimi wersjami pól (ochrona przed pętlą zwrotną / feedback-loop guard).
  - `build_snapshot` przypisuje wersję zerową (`lc=0, seq=0`) nowo odkrytym pozycjom przy istniejącym snapshocie oraz obsługuje `suppress_local_changes` podczas skanowania biblioteki (z zachowaniem jawnej zmiany istniejącej oceny `userrating`).
  - `V2RuntimeComponents` udostępnia metody `sync_cycle()`, `publish_local_snapshot()`, `initialization_preview()` oraz `apply_initialization()`.
- W `sudosync_core.py` (ścieżka aktywna w UI/tle Kodi) naprawiono błędy blokujące realne użycie na urządzeniach Kodi:
  - Zainicjalizowano brakującą mapę `secure_map = _get_secure_local_identity_map()` w `run_live_sync_cycle()` (eliminacja `NameError` przy zapisie zmian do Kodi).
  - Usunięto odrzucanie snapshotów starszych niż 7 dni w `_validate_snapshot` i `_validate_remote_snapshot` (urządzenie włączone po dłuższej przerwie normalnie dogania stan sieci) oraz poprawiono porównywanie dat UTC (`tzinfo=timezone.utc`).
  - `read_remote_snapshots()` ignoruje pliki w formacie `SudoSync v2 snapshot`, dzięki czemu koegzystencja katalogu v2 nie powoduje fałszywych błędów odczytu snapshotów.
  - `_record()` oraz `_get_secure_local_identity_map()` łączą identyfikatory z JSON-RPC Kodi z identyfikatorami z plików `.nfo` (w tym `sudosync`), zamiast pomijać `.nfo`, gdy Kodi zwróci częściowy zestaw ID.
- Wdrożono poprawki wersjonowania pierwszego snapshotu i odporności pętli usługi (`LIVE_BUSY_RETRY_SECONDS = 10` w `service.sudosync/service.py`) z zachowaniem wszystkich flag `dirty`.
- W wydaniach `2.0.1` i `2.0.2`:
  - Wprowadzono mechanizm dzierżawy pojedynczego aktywnego Kodi w sieci (`active_kodi_lock.json`, `acquire_network_active_kodi_lease`, `refresh_network_active_kodi_lease`, `release_network_active_kodi_lease`) oraz strażnika minimalnej wersji wtyczki (`min_addon_version` w `SudoSync.cfg`).
  - Pętla usługi w `service.py` reaguje na wynik `False` z `refresh_network_active_kodi_lease()` (spowodowany przejęciem dzierżawy przez inne Kodi lub podbiciem `min_addon_version` w `SudoSync.cfg` powyżej wersji lokalnej): loguje ostrzeżenie, wyświetla powiadomienie i przerywa pętlę usługi.
  - Całkowicie usunięto wycofany mechanizm automatycznej aktualizacji ze wspólnego folderu `.SudoSync` na NAS (`check_and_enforce_updates_before_bootstrap`, `find_latest_update`, `check_for_update`, `install_latest_update`, `_validate_update_zip`, `sign_release.py`). Aktualizacje odbywają się przez GitHub Releases (raz na 24 h za zgodą użytkownika lub ręcznie) oraz przez ręczny wybór pliku ZIP.
- Polityka wydań i wersjonowania (od 2026-10-17):
  - Kolejne paczki na GitHub Releases są publikowane jako pełne wydania (**Release**, bez flagi `Pre-release`, jako `Latest`), aby endpoint `/releases/latest` zawsze zwracał najnowszą wersję.
  - Większe zmiany otrzymują kolejny numer na trzeciej pozycji (`patch`), np. `2.0.1`, `2.0.2`, ..., `2.0.12`.


