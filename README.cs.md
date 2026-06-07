# voicetype-win

**Lokální offline diktování řeči pro Windows — jako Whisper Flow, ale běží celé u tebe na vlastním GPU.** Stiskneš zkratku, mluvíš, stiskneš znovu a přepsaný text se vloží do aktivního okna. Nic se neposílá do cloudu.

Postaveno na [onnx-asr](https://github.com/istupakov/onnx-asr) s **přepínatelnými modely** (NVIDIA Parakeet, Canary, …). Výchozí model je multijazyčný — 25 evropských jazyků včetně češtiny, angličtiny, němčiny, … s automatickou detekcí jazyka.

> 🇬🇧 English version: [README.md](README.md)

> 🤖 **Generováno AI:** Veškerý kód v tomto repozitáři byl vygenerován pomocí AI (Anthropic Claude přes Claude Code). Před použitím doporučujeme kontrolu.

## Co to umí

- 🎙️ **Diktování na přepínač** globální zkratkou (výchozí `Alt + .`)
- ⚡ Běží **lokálně na GPU** (CUDA), automatický fallback na CPU
- 🔀 **Přepínatelný model** v configu (výchozí Parakeet TDT 0.6B v3; podporován i Canary, GigaAM, Whisper)
- ✍️ Automatická **interpunkce a velká písmena**
- 📋 Vkládání přes schránku — spolehlivé i pro diakritiku
- 🟢 **Ikona v liště**: pauza, **uvolnění modelu z VRAM** (vrátí ~3,4 GB pro hry), ukončení
- ⏯️ **Automatická pauza médií** (YouTube / Spotify / …) po dobu nahrávání a jejich obnovení
- 🚀 Volitelný **autostart** po přihlášení

## Požadavky

- Windows 10 / 11
- **NVIDIA GPU** doporučeno (~4 GB volné VRAM pro výchozí model). RTX 50xx (Blackwell / sm_120) podporováno. Funguje i bez GPU (CPU, pomalejší).
- **Python 3.11**
- Mikrofon

CUDA Toolkit instalovat **netřeba** — potřebný CUDA 12 / cuDNN 9 runtime se nainstaluje přes pip (viz `requirements.txt`).

## Instalace

1. **Stáhni kód** — naklonuj, nebo z GitHubu stáhni ZIP (zelené tlačítko **Code** → *Download ZIP*) a rozbal:
   ```
   git clone https://github.com/mlutonsky/voicetype-win.git
   ```
2. Měj nainstalovaný **Python 3.11** (`winget install Python.Python.3.11`).
3. **Dvojklik na `install.cmd`** ve složce. Hotovo.

To je vše — `install.cmd` vytvoří virtuální prostředí a nainstaluje **všechny** závislosti z `requirements.txt` automaticky (včetně CUDA 12 / cuDNN 9 runtime). GPU se autodetekuje; na stroji bez NVIDIA GPU se nainstaluje CPU verze. Model (~1 GB) se stáhne automaticky z Hugging Face při prvním spuštění.

<details>
<summary>Radši terminál? / Proč to spouští PowerShell?</summary>

`install.cmd` je jen pohodlná obálka kolem `install.ps1`. Z terminálu jde spustit totéž přímo:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1   # -Cpu vynutí CPU verzi
```

`-ExecutionPolicy Bypass` vypadá hrozivě, ale není: Windows ve výchozím stavu blokuje spouštění nepodepsaných lokálních `.ps1` skriptů a tento přepínač to obejde **jen pro toto jedno spuštění** — **nemění** žádné systémové nastavení. `install.cmd` to za tebe udělá, abys to nemusel psát. Skripty `install.ps1` i `install-autostart.ps1` jsou krátké a čitelné, klidně si je předem projdi.
</details>

Ověření GPU + modelu:

```powershell
.\.venv\Scripts\python.exe smoke_test.py
```

## Použití

- **Na pozadí (bez okna):** dvojklik na `start-dictation.vbs`
- **S konzolí (vidíš log):** `.\.venv\Scripts\python.exe dictate.py`

1. Klikni do libovolného textového pole.
2. Stiskni **`Alt + .`** → vyšší pípnutí → **mluv** (hrající média se sama pozastaví).
3. Stiskni **`Alt + .`** znovu → nižší pípnutí → text se vloží na kurzor; přehrávání se obnoví.

### Ikona v liště

Ikona se objeví v oznamovací oblasti (možná pod šipkou **^** — dá se přetáhnout na lištu). Barva = stav:

| Barva | Stav |
|---|---|
| 🟢 zelená | připraveno, model v paměti |
| 🔴 červená | nahrává |
| 🟠 oranžová | diktování pozastaveno |
| ⚪ šedá | model uvolněn (VRAM volná) |

**Pravým klikem** se rozbalí menu:

- **Pozastavit / Obnovit diktování**
- **Uvolnit model z paměti (GPU)** — vrátí **~3,4 GB VRAM** (ideální před hraním her). Aplikace běží dál a model se sám načte (~3 s) při příštím diktování.
- **Načíst model do paměti** — ruční načtení zpět.
- **Ukončit** — ukončí úplně (uvolní i zbylých ~80 MB CUDA kontextu).

### Autostart po přihlášení

**Dvojklik na `install-autostart.cmd`** (nebo `powershell -ExecutionPolicy Bypass -File install-autostart.ps1`).

Vypnutí: smaž zástupce ve `shell:startup` (Win+R → `shell:startup`).

## Konfigurace (`config.toml`)

Po úpravě aplikaci restartuj.

| Klíč | Význam |
|---|---|
| `hotkey` | Zkratka pro toggle, např. `"alt+."`, `"ctrl+alt+space"`, `"win+alt+d"` |
| `model` | ASR model — viz *Přepnutí modelu* níže |
| `device` | `"auto"` (GPU, fallback CPU) / `"gpu"` / `"cpu"` |
| `language` | jazyk přepisu — `"auto"` nebo kód (`"cs"`, `"en"`, `"de"`, …) |
| `ui_language` | jazyk aplikace/tray/logu — `"auto"` (dle Windows), `"en"` nebo `"cs"` |
| `punctuation` | `true` = interpunkce a velká písmena |
| `append_space` | `true` = přidá mezeru za vložený text |
| `beep` | zvuková signalizace start/stop |
| `paste_method` | `"clipboard"` (Ctrl+V, spolehlivé pro diakritiku) / `"type"` |
| `pause_media` | `true` = pozastaví hrající média po dobu nahrávání a pak je obnoví |

### Přepnutí modelu

V `config.toml` nastav `model` na cokoli, co onnx-asr podporuje, např.:

| `model` | Poznámka |
|---|---|
| `nemo-parakeet-tdt-0.6b-v3` | **výchozí** — multijazyčný (25 EU jazyků), auto-detekce |
| `nemo-canary-1b-v2` | multijazyčný + překlad, větší/přesnější |
| `nemo-parakeet-tdt-0.6b-v2` | jen angličtina, nejrychlejší |
| `whisper-base` | OpenAI Whisper (ONNX) |

Nastav `language` odpovídajícím způsobem (nebo nech `"auto"`). Kompletní seznam viz [onnx-asr](https://github.com/istupakov/onnx-asr#models).

## Řešení potíží

- **Zkratka nereaguje:** globální odchyt kláves může vyžadovat běh **jako správce** (když má fokus aplikace běžící jako správce) — spusť `start-dictation.vbs` / konzoli jako správce.
- **Běží na CPU místo GPU:** zkontroluj výstup `smoke_test.py` / řádek `Běží na` v `dictate.log`. GPU vyžaduje balíčky `nvidia-*-cu12` z `requirements.txt`.
- **Špatný mikrofon:** používá se výchozí vstup Windows — změň v *Nastavení → Systém → Zvuk → Vstup*.
- **Vkládání nefunguje v konkrétní aplikaci:** nastav `paste_method = "type"`.
- **Dlouhé nahrávky:** model je laděný na kratší úseky (do ~30 s); pro souvislé diktování přepínej po větách/odstavcích.

## Jak to funguje

- `dictate.py` — hlavní aplikace: globální hotkey (toggle), nahrávání mikrofonu (`sounddevice`, 16 kHz mono), přepis (`onnx-asr`), vložení přes schránku, ikona v liště (`pystray` + `Pillow`), pauza/obnovení médií.
- `cuda_init.py` — zpřístupní CUDA/cuDNN DLL z balíčků `nvidia-*-cu12` (jinak je `onnxruntime` za běhu nenajde).
- `media_control.py` — pozastaví/obnoví média přes Windows System Media Transport Controls (`winsdk`).
- Model se stáhne z Hugging Face při prvním spuštění do `~/.cache/huggingface`.

## Poděkování

- [onnx-asr](https://github.com/istupakov/onnx-asr) od istupakova (runtime + ONNX konverze modelů)
- [NVIDIA NeMo](https://github.com/NVIDIA/NeMo) modely Parakeet / Canary

## Licence

[MIT](LICENSE)
