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
- Aktualizacja jest dystrybuowana przez paczkę umieszczoną przez
  administratora w `.SudoSync` i sprawdzaną przez uruchomioną wtyczkę.
  Użytkownik nie może jej pominąć. Nie dodawaj funkcji wgrywania paczki przez
  wtyczkę bez osobnego polecenia.
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
- Przy wykryciu nowego ZIP-a aktualizacji, który nie przejdzie weryfikacji,
  pokaż jasny komunikat użytkownikowi, odmów instalacji i zatrzymaj start
  wtyczki do czasu zastąpienia lub usunięcia paczki.

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


## Stan przekazania — 2026-10-12

- Aktualny kod rozwoju znajduje się na GitHubie w `v2/rewrite-2026-10-10`.
  Zmiana adaptera JSON-RPC łączy dostępne identyfikatory z Kodi z
  identyfikatorami odczytanymi z plików `.nfo` (obsługiwane
  `<uniqueid type="…">`, filmowe `<tmdbid>` i legacy IMDb
  `<id>tt…</id>`). Sprzeczne identyfikatory zatrzymują odczyt zamiast
  automatycznego dopasowania.
- Potwierdzone: 13 testów `tests/test_sudosync_v2_kodi_rpc.py` przeszło
  lokalnie. To testy adaptera, nie test end-to-end na Kodi.
- Ograniczenie: `KodiJsonRpcAdapter` nie obsługuje jeszcze zwykłej
  synchronizacji v2 end-to-end. Nie budować ZIP-a ani nie deklarować gotowości
  do testu na Kodi.
- Bieżący etap lokalny: dodano `KodiVFSMetadataReader` i kompozytor
  `build_kodi_v2_runtime`, który łączy adapter JSON-RPC z czytaniem NFO przez
  Kodi VFS. Testy VFS, runtime i JSON-RPC przeszły (33 testy, 1 pominięty z
  powodu braku uprawnień Windows do tworzenia symlinków). Etap zapisano w
  commicie `47fb544` na gałęzi rozwoju. `service.py` nadal używa dotychczasowego silnika v1 (linia 1.x).
- Uzgodniony model pracy Kodi jest sekwencyjny: w danej chwili działa tylko
  jedna usługa SudoSync na urządzeniu Kodi. Fizyczny test blokady między
  urządzeniami nie jest warunkiem implementacji ani zwykłego testu
  funkcjonalnego. Jest potrzebny wyłącznie po ewentualnym rozszerzeniu projektu
  o równoczesną pracę usług Kodi. Nie pytaj ponownie o tę decyzję.
- Integracja startowa: `service.py` wywołuje runtime v2 do odzyskiwania
  przerwanej transakcji i podglądu diagnostycznego. Zwykła synchronizacja nadal
  działa ścieżką dotychczasowego silnika v1 (linia 1.x); nie jest to jeszcze synchronizacja v2 end-to-end.
- Następny etap: dokończyć bezpieczny przepływ podglądu, jawnego zatwierdzenia,
  transakcji i cyklu synchronizacji v2 zgodnie z `V2_DESIGN.md`. Potem sprawdzić
  synchronizację kolejno na urządzeniach Kodi.
- Gałąź GitHub została zaktualizowana przez integrację GitHub, ponieważ
  lokalny Git nie rozwiązywał `github.com`. Lokalny checkout domowy nie
  został pobrany ponownie; jego historia Git nie jest zsynchronizowana ze
  zdalną. Na początku kolejnej sesji sprawdź stan GitHuba i bezpiecznie
  zsynchronizuj checkout przed dalszymi commitami. Nie resetuj go w ciemno.
- `master` i `v1-stable` pozostają nietknięte.


## Stan przekazania — 2026-10-16

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
- Potwierdzone testy jednostkowe: 181 testów uruchomionych (`python -m unittest discover -s tests -p "test_*.py" -v`), 178 zaliczonych, 3 pominięte (testy symlinków na Windows).
- Zbudowano lokalną paczkę instalacyjną ZIP gotową do bezpośrednich testów beta na urządzeniach Kodi użytkownika (pliki `*.zip` są wykluczone w `.gitignore`).
- Wdrożono poprawki po audycie commitu `d1096c3`: dodano posortowane aliasy rekordu klienta do elementów planu (`build_live_plan` i `build_dry_run` w `sudosync_merge.py`), uszczelniono kontrolę tożsamości w `_apply_one_planned_item` (fail-closed przy pustych lub rozłącznych aliasach), dodano logowanie `LOGWARNING` w `_get_secure_local_identity_map` oraz obsługę milisekund w parserze czasu `_validate_remote_snapshot` wraz z 14 nowymi testami w `tests/test_live_apply_identity.py` (łącznie 195 testów, 192 zaliczone, 3 pominięte) i przebudowano lokalną paczkę `service.sudosync-2.0.0.zip`.
- Wdrożono poprawki wersjonowania pierwszego snapshotu i odporności pętli usługi:
  - `_record_versions` przy braku poprzedniego snapshotu (`previous_snapshot is None`) zawsze nadaje wersje zerowe (`lc=0, seq=0`), chroniąc historię odtworzeń peerów przed nadpisaniem przez świeżo dołączone urządzenie.
  - `_initial_snapshot_and_analyse` publikuje snapshot do v2 wyłącznie po zakończeniu inicjalizacji (`init_completed=True`), a `_sync_v2_after_initial_apply` publikuje stan po inicjalizacji z jawnym `suppress_local_changes=True`.
  - Dodano backoff `_live_retry_delay_seconds` (minimum 30 s lub czas cyklu pollingu) po błędzie lub blokadzie w `_execute_integrated_live_cycle` bez kasowania flag `dirty`.
  - Potwierdzone testy: 219 testów (w tym nowy zestaw `tests/test_v2_first_publish_and_backoff.py`), 216 zaliczonych, 3 pominięte (symlinki Windows).
- Domknięto backoff pętli usługi przy wyniku `busy` bez błędu i blokady (`LIVE_BUSY_RETRY_SECONDS = 10` w `service.sudosync/service.py`) z zachowaniem wszystkich flag `dirty`. Dodano instrukcję bezpiecznego ręcznego testu na urządzeniu Kodi w pliku [`TEST_NA_KODI.md`](TEST_NA_KODI.md). Bieżący zestaw testów jednostkowych liczy 223 testy (`tests/test_v2_busy_backoff.py`), w tym 220 zaliczonych i 3 pominięte (symlinki Windows). Z aktualnego commitu na gałęzi `master` zbudowano i opublikowano na GitHubie (w GitHub Releases `v2.0.0`) niepodpisaną paczkę testową `service.sudosync-2.0.0.zip`. Test na Kodi odbywa się w scenariuszu czystej instalacji po zmianie nazwy starego folderu `.SudoSync` na NAS i usunięciu poprzedniej wersji ze wszystkich urządzeń Kodi.

