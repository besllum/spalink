# SPALINK-SIEVERS LandschaftsArchitekten – Website

Statische Website (HTML/CSS, wenig JavaScript) ohne WordPress und ohne Plugins.

- `data/projekte.json` – alle Projekte (Titel, Kategorien, Texte, Fotos)
- `data/wp-export.json` – Texte der festen Seiten und von „Aktuell“ (Export aus WordPress)
- `src/assets/` – Stil (CSS), Skript (JS), Schriften (Open Sans, lokal eingebunden)
- `build.py` – erzeugt die fertige Website in `public/` (braucht Python 3 + Pillow und die Originalfotos im Ordner `../medien`)
- `public/` – **die fertige Website**. Diesen Ordnerinhalt per SFTP zu IONOS hochladen.

Vorschau: Vercel liefert `public/` aus (siehe `vercel.json`, Vorschau ist für Suchmaschinen gesperrt).
