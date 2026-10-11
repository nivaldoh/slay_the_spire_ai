# Project state

Updated 2026-10-11. Milestone A is in progress; no original-engine combat verified yet.

## Active work

Locked environment and adapter bootstrap. No GPU job is running.
The session began at 02:12 America/Sao_Paulo; user return deadline is 10:00 tomorrow
(2026-10-12 13:00 UTC). All experiment processes must have explicit shorter limits.

## Initial inspection

WSL, game files, all three Workshop jars, Windows Python 3.13.1, uv 0.12.5,
and RTX 3060 availability confirmed again. WSL has 7.7 GiB RAM and 4.8 GiB available.

## Bootstrap reference (facts from the guide, pending runtime verification)

### Verified environment

| Item | Finding |
|---|---|
| Host | Windows 11 Education (10.0.26200), user `niv`. Agent work runs in WSL2 Ubuntu 24.04. |
| Game | `C:\Program Files (x86)\Steam\steamapps\common\SlayTheSpire`. Classes dated 2022-12-20 (final patch), Steam build 10180494, bundled `jre\bin\java.exe` 1.8.0_144, `-Xmx1G` in `config.json`. |
| Mods | Downloaded from the Steam Workshop on 11 October 2026 into `steamapps\workshop\content\646570\<id>\`: ModTheSpire 3.30.3 (`1605060445`), BaseMod 5.56.0 (`1605833019`), CommunicationMod 1.2.1 (`2131373661`). Not run yet. |
| GPU | RTX 3060 12 GB, visible from WSL (driver 591.86, CUDA 13.1). The desktop uses about 1.3 GB. |
| CPU and memory | 12 threads. The host has 15.9 GB RAM, but WSL is capped at 7.7 GiB, and 1.6 of its 2 GiB swap was already in use. There is no `.wslconfig`. |
| Disk | 398 GB free in WSL; 2.1 TB free on `C:`. |
| Tools | WSL: uv 0.12.5, Python 3.13.5 (miniconda), OpenJDK 8 runtime only (no `javap`), cmake, g++, `gh` signed in. Windows: Python 3.13.1 at `C:\Python313\python.exe`. |
| Repository | `github.com/nivaldoh/slay_the_spire_ai`, **public**, empty. |

SHA-256 of the downloaded jars:

```text
541b5e8a875d2a404a5a6d54f4a6f814284b0cf71acb9245239d9c5ef50ea604  ModTheSpire.jar
c3353c10e64c621b723e9fd7d0502dfa796f828b101b68513594a5f5ef83fbaf  BaseMod.jar
12b99249eccfd5245ddb0b6b7575e1a1dfba0ce0ed6fad5bd5bbd4a303897ef5  CommunicationMod.jar
```

### Owner decisions

- The AI plays in the **Steam install with the personal profile** "niv" (slot 0). The owner accepts that bot runs change stats, unlock progress, and run history, and may award Steam achievements. No separate game copy.
- Mods come from the **Steam Workshop**. ModTheSpire and BaseMod stopped publishing GitHub releases in 2018, and those builds do not support the 2022 game.
- The agent may **open game windows and run GPU jobs** during working sessions and authorized overnight runs. It pauses when the owner wants the PC.
- The agent may **commit and push to `main`** without asking. The repository is public, so never commit game files, mod jars, saves, or bulky run output.
- The defaults in section 1 stand: Ironclad, Ascension 0, combat benchmark first.

### Known caveats

- **Unlocks can drift.** The profile has Ironclad unlock level 3 of 5. Finished bot runs may unlock more cards and relics, which changes reward pools. A starter-deck combat benchmark is unaffected. Record the unlock state in every run manifest.
- **Stats upload is unconfirmed.** "Upload Data" is on in `STSGameplaySettings`. The game has a `Settings.isModded` flag that its metrics, Steam-integration, and unlock code reference, so modded runs probably skip the upload. Confirm this at runtime. If they do upload, ask the owner before changing the setting.
- **Workshop updates can replace the jars.** Copy them to a fixed location and check the hashes before each run.
- **CommunicationMod 1.2.1 declares game version 11-30-2020.** It is assumed to work with the 2022 build but has not been tested here.
- **The owner cannot play Slay the Spire while experiments run,** because both use the same install.
- **WSL memory** is enough for the neural-policy track. Revisit it before the language-model track.

### Planned architecture (not built)

The game, ModTheSpire, BaseMod, and CommunicationMod run on Windows. CommunicationMod starts a small relay that uses only the standard library and runs under `C:\Python313\python.exe`. The relay forwards protocol lines over TCP to a server in WSL, which owns the policy, logging, and GPU. The WSL side listens and the Windows side connects out, which should avoid a Windows Firewall prompt; verify the localhost forwarding. The agent launches and restarts the game from WSL through Windows interop.

### Next steps for Milestone A

1. Copy the three jars to a fixed folder and record their versions and hashes. Find a launch command that starts ModTheSpire from WSL with no dialogs, likely `jre\bin\java.exe -jar ModTheSpire.jar --skip-launcher --mods basemod,CommunicationMod`, run from the game folder.
2. Scaffold the repository as described in section 4:
   - `AGENTS.md`, plus a thin `CLAUDE.md` containing `@AGENTS.md`
   - `README.md`, and `docs/state.md` holding this section
   - `.gitignore` covering game files, bulky `runs/` output, and `*:Zone.Identifier`
   - one locked uv environment

   Then commit and push.
3. Build the relay and protocol layer. Point CommunicationMod's `command=` at the relay. Its config file is created on first run, probably at `%LOCALAPPDATA%\ModTheSpire\CommunicationMod\config.properties`; confirm the path.
4. Implement `python -m spire doctor` to report the facts above and any precise blockers.
5. Have a random legal-action policy play one combat from a seeded `START`. Save the observations, actions, execution outcomes, and terminal result.
6. Start the next episode automatically. Make bridge failures distinguishable from gameplay losses. Work through the checklist in section 3.3.
7. Measure episode and reset time and record them in `docs/state.md`. Then begin Milestone B.

### Overnight readiness

**Not ready for an overnight training or research run.** There is no bridge, policy, evaluator, or baseline yet, and the overnight prompt in section 11 expects `docs/state.md` and a baseline.

An unattended *bootstrap* session that works toward Milestone A is possible now, using the section 11 bootstrap prompt. The first game launch should happen with the owner present, because it may raise Steam or Windows dialogs that need a click. Before leaving the session unattended:

- Steam is running and signed in.
- Windows sleep is disabled.
- Nobody is playing Slay the Spire.

