# Architektura i mechanizmy SudoSync

## Zasada działania
- Komunikacja z Kodi odbywa się wyłącznie przez JSON-RPC. Brak bezpośrednich operacji I/O na plikach bazy danych SQLite (MyVideos*.db).
- Folder wymiany danych to wspólny zasób sieciowy (SMB/NFS) wskazany w konfiguracji dodatku.

## Model danych i synchronizacja
- Identyfikacja mediów opiera się na unikalnych ID zewnętrznych baz: IMDb, TMDb, TVDb, Trakt. Pozycje bez unikalnych ID są pomijane.
- Wersjonowanie rekordów: każdy atrybut (playcount, lastplayed, resume, userrating) zapisywany jest z własnym znacznikiem czasu i ID klienta.
- Zapobieganie pętlom zwrotnym: zdalny zapis zachowuje wersję źródłową, dzięki czemu nie wywołuje ponownego wykrycia jako lokalna zmiana.
- Kwarantanna skanowania: zmiany wykryte podczas indeksowania biblioteki (VideoLibrary scan) otrzymują celowo starsze znaczniki, by nie nadpisać stanu ze wspólnego folderu.
- Ochrona odtwarzania: w trakcie aktywnego odtwarzania wideo wtyczka nie wykonuje żadnych zdalnych zapisów.