# Discord fórumtopik-figyelő

A bot a megadott fórumcsatornák öt legutóbb aktív, még nyitott topikját jeleníti meg egyetlen Discord-üzenetben. Helyi futtatáskor percenként frissít. GitHub Actions használatakor ötpercenként indul egy rövid futás, frissíti az üzenetet, majd leáll.

## Helyi beállítás

1. Másold a `.env.example` fájlt `.env` néven, és töltsd ki a tokennel és csatornaazonosítókkal.
2. PowerShellben, ebben a mappában futtasd:

   ```powershell
   py -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe main.py
   ```

## Folyamatos, ingyenes futtatás GitHub Actions segítségével

A workflow ütemezetten, ötpercenként frissíti a Discord-üzenetet. A GitHub ütemezése néha késhet. Nyilvános repók esetén a standard GitHub-hosted Actions futtatás ingyenes; a bot titkos tokenje GitHub Actions secretként kerül beállításra, és nem része a repónak. A forráskód nyilvánosan látható lesz.

### 1. Hozz létre egy nyilvános repót

GitHubon válaszd a **New repository** lehetőséget. Adj neki nevet, például `forum-topic-watcher`, állítsd **Public**-ra, és hozz létre üres repót. Ne kérd README vagy `.gitignore` automatikus létrehozását.

### 2. Töltsd fel a projekt fájljait

Nyiss PowerShellt a projekt mappájában, majd futtasd az alábbiakat. Az URL-ben cseréld le a `SAJATNEV/REPO` részt a GitHub-felhasználónevedre és a repó nevére:

```powershell
git init
git add .
git commit -m "Prepare scheduled Discord topic bot"
git branch -M main
git remote add origin https://github.com/SAJATNEV/REPO.git
git push -u origin main
```

A `.gitignore` kizárja a `.env` és `.venv` fájlokat. Feltöltés előtt a `git status` paranccsal ellenőrizheted, hogy a `.env` nincs a feltöltendő fájlok között. **A bot tokent soha ne tedd a kódba vagy nyilvános fájlba.**

### 3. Add hozzá a titkos adatokat a GitHubhoz

A repóban menj a **Settings → Secrets and variables → Actions** oldalra, majd hozz létre három **Repository secret** értéket:

| Secret neve | Értéke |
| --- | --- |
| `DISCORD_TOKEN` | A bot tokenje |
| `FORUM_CHANNEL_IDS` | A fórumcsatorna-ID-k, vesszővel elválasztva |
| `POST_CHANNEL_ID` | A lista célcsatornájának ID-je |

Ezeket a GitHub titkosítva tárolja, a workflow futásakor pedig környezeti változóként adja át a botnak.

### 4. Indítsd el és ellenőrizd

Nyisd meg a repó **Actions** lapját, engedélyezd a workflow-kat, válaszd ki a **Discord forum topic list** workflow-t, majd kattints a **Run workflow** gombra. Ha a futás sikeres, a Discord-üzenet frissül. Ezután a workflow automatikusan fut ötpercenként. A saját gépeden futó botot leállíthatod.

## Discord jogosultságok

A botnak látnia kell a figyelt fórumcsatornákat és a cél szöveges csatornát. Szükséges jogosultságok: **View Channels**, **Read Message History**, **Send Messages** és **Embed Links**. Privileged intent nem kell.

Csak az aktív, nem archivált topikok szerepelnek a listában.
