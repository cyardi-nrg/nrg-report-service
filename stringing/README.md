# Stringing & electrical design — index by project

Version: **v1 (2026-11-18)** · NRG Technologists

One folder per project, the same way the 3D work is filed under `3d-design/<project>/`. Each folder has its own
`README.md` listing every deliverable (latest version first), the inputs and decisions it rests on, what still
needs checking, and how to rebuild it.

**To find a project:** search for the client's name in this file, or on GitHub search the repository for the
name (for example `Sangani` or `Jain`). Every file name starts with the project name and ends with its version.

| Project | Size | Folder | Latest deliverables | 3D / walk-around | Status |
|---|---|---|---|---|---|
| **Jain Granite & Marble** (shed roof, E–W slopes) | 100 kWp · 160 × Adani 625 Wp · GoodWe GW80K-MT | [`jain-granite/`](jain-granite/) | Layout set with Y-connectors L-01 v2, L-02 v1, L-03 v1 · CEIG set 01–06 v7 · BOM v2 (no-Y) | [`3d-design/jain-granite/`](../3d-design/jain-granite/) | Layout set done; BOM still for the no-Y design |
| **Sangani Skyz** (G+12, 48 flats, flat terrace) | 104.64 kWp · 192 × 545 Wp · 48 × Solaryaan 2 kW | [`sangani-skyz/`](sangani-skyz/) | Stringing plan v3 · cable schedule v3 · DC route samples v3 | 3D v1.4, proposal v1.1 and walk-around made in the "3D design and walkthrough videos" session (not filed in `3d-design/` yet) | Stringing and cable lengths done |
| **Express Cranes** (south shed, gable, ridge E–W) | 75 kWp · 120 × Adani 625 Wp · inverter to be confirmed | [`express-cranes/`](express-cranes/) | String layout (landscape) v1 | [`3d-design/express-cranes/`](../3d-design/express-cranes/) | String layout done; inverter / home runs pending |
| **Two-roof site, 120 kWp** (client name to be given) | 120 kWp · 625 Wp · GoodWe | [`two-roof-120kwp/`](two-roof-120kwp/) | Stringing options v2 · portrait vs landscape v6 · roof B cost v2 | — | Waiting on owner's choices |

## Conventions (all projects)

- File names: `<Project>_<what>_v<N>.<ext>`; older versions stay next to the new one.
- Every script and generated sheet carries its version in its first line / title block.
- Portrait / landscape are relative to the roof **slope** (landscape = long side along the ridge).
- Stringing rules (owner): string ends on the outside edge, never across a walkway, panels joined side by side,
  mirrored partner strings so + meets + and − meets − (Y-connectors only where the same poles meet).
- DC routing (owner): along a rafter → edge purlin → across onto the nearest wall (cabin / building) → along the
  wall → into the inverter room.
