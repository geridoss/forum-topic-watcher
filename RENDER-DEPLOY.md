# Render telepítési útmutató

Ez a változat a Discord-bot mellett egy apró `/health` HTTP-végpontot is futtat, amit egy külső ellenőrző szolgáltatás rendszeresen meghívhat. A beállítás a Render ingyenes webszolgáltatására készült.

## 1. Töltsd fel a módosításokat GitHubra

PowerShellben, a projekt mappájában:

```powershell
git add main.py requirements.txt render.yaml RENDER-DEPLOY.md
git commit -m "Prepare bot for Render"
git push
```

## 2. Hozd létre a Render szolgáltatást

1. Lépj be a [Render Dashboardra](https://dashboard.render.com/).
2. Válaszd a **New → Blueprint** lehetőséget, és csatlakoztasd a `geridoss/forum-topic-watcher` GitHub-repót.
3. A Render a repó `render.yaml` fájljából létrehozza az ingyenes webszolgáltatást. Ha a Blueprint a titkos változókat kéri, add meg őket:
   - `DISCORD_TOKEN`: a Discord bot tokenje.
   - `FORUM_CHANNEL_IDS`: a figyelt fórumcsatornák ID-i, vesszővel elválasztva.
   - `TEXT_CHANNEL_IDS`: a figyelt hagyományos szöveges csatornák ID-i, vesszővel elválasztva (opcionális).
   - `POST_CHANNEL_ID`: a lista csatornájának ID-je.
   - `TOPIC_LIMIT`: a megjelenő aktivitások száma (opcionális, alapértelmezés: `5`).
4. Indítsd el a telepítést, és várd meg, amíg a szolgáltatás állapota **Live** lesz.
5. A szolgáltatás `onrender.com` címe után illeszd a `/health` útvonalat, például `https://forum-topic-watcher.onrender.com/health`. A böngészőben az `ok` választ kell látnod.

## 3. Állíts be külső pinget

Egy külső uptime-monitorozó szolgáltatásban figyeld a fenti `/health` címet 10 percenként. A bot saját maga által küldött pingjére ne támaszkodj: ha a Render leállítja a szolgáltatást, a bot nem tudja magát felébreszteni.

## 4. Ellenőrzés és átállás

Ellenőrizd, hogy a bot a Discordban online, a naplóban pedig nincs `Missing Access` vagy más frissítési hiba. Teszteld a listát egy fórumba írt új hozzászólással, és várj legfeljebb egy percet. Ha a Renderes példány frissít, kapcsold ki a GitHub Actions workflow-t az **Actions → Discord forum topic list → ⋯ → Disable workflow** menüben. Így nem fut egyszerre két példány.

## Korlátok

- A Render ingyenes webszolgáltatása 15 perc bejövő forgalom nélkül alvó állapotba kerül. Az uptime monitor pingje ezt az időt újraindítja.
- A Render ingyenes csomagja havi 750 üzemórát ad a munkaterület szolgáltatásainak. Egy egész hónapig futó szolgáltatás egy 31 napos hónapban 744 órát használ fel, így kevés tartalék marad; a többi ingyenes szolgáltatás is ebből a keretből fogyaszt.
- A Render az ingyenes szolgáltatást bármikor újraindíthatja, az uptime monitor vagy az ütemezett ping is kimaradhat. Ez hobbi célú, költségmentes kerülőmegoldás, nem garantált, folyamatos rendelkezésre állás.
- A `BOT_RUN_ONCE` változót ne állítsd be a Render szolgáltatásánál. Ott a botnak tartósan futnia kell.
- A Discord tokent csak a Render titkos környezeti változói között add meg, ne a GitHub kódjában.
