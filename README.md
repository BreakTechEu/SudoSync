# SudoSync for Kodi

Lekka wtyczka usługi (service) dla odtwarzacza Kodi, zapewniająca automatyczną, dwukierunkową synchronizację stanu obejrzenia, punktów wznowienia (resume point), daty ostatniego odtworzenia oraz przyznanej oceny pomiędzy wieloma instalcjami KODI w sieci lokalnej bez konieczności stawiania centralnej bazy MySQL/MariaDB.

Synchronizacja opiera się na wspólnym zasobie sieciowym (SMB / NFS) oraz odpytywaniu oficjalnego API Kodi (JSON-RPC).

---

## Główne cechy

- **Brak zewnętrznego serwera bazy:** Wystarczy współdzielony katalog sieciowy z serwera NAS, routera lub komputera w tej samej sieci LAN.
- **Bezpieczeństwo biblioteki:** Brak bezpośredniej ingerencji w pliki bazy SQLite (`MyVideos*.db`) – modyfikacje odbywają się wyłącznie przez procedury JSON-RPC Kodi.
- **Wersjonowanie i rozwiązywanie konfliktów:** Każde pole posiada niezależny znacznik czasu i identyfikator klienta, co zapobiega pętlom zwrotnym i niekontrolowanemu nadpisywaniu danych.
- **Działanie w tle na Android TV / Google TV:** Mechanizm okresowego badania różnic niweluje problem gubienia zdarzeń systemowych `OnUpdate`/`OnStop` na przystawkach telewizyjnych.
- **Ochrona przed nadpisywaniem podczas skanowania:** W trakcie skanowania biblioteki i odczytu plików `.nfo` zmiany nie są traktowane jako nadrzędne.

---

## Synchronizowane pola

- Status obejrzenia (licznik odtworzeń / stan watched-unwatched),
- Dokładny punkt wznowienia wideo (*resume position*),
- Data ostatniego odtworzenia (*last played*),
- Oceny użytkownika (*userratings*).

---

## Instalacja i konfiguracja

1. **Pobranie wtyczki:**
   - Przejdź do zakładki **Releases** po prawej stronie tego repozytorium.
   - Pobierz najnowszy plik `service.sudosync-1.0.0.zip`.

2. **Instalacja w Kodi:**
   - W menu Kodi wejdź w: *Dodatki -> Zainstaluj z pliku zip* i wskaż pobrane archiwum.

3. **Konfiguracja ścieżki wymiany:**
   - Otwórz ustawienia wtyczki SudoSync w Kodi.
   - Podaj (wybierz narzędziem KODI) ścieżkę do wspólnego katalogu w Twojej sieci lokalnej, do którego UPRAWNIENIA ZAPISU mają wszystkie instancje Kodi, np.: smb://192.168.1.100/Wspoldzielony/.SudoSync/