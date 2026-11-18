# Express Cranes — 75 kWp rooftop: 3D views — v1 (2026-11-02) · NRG Technologists

Built on the Jain Granite viewer (`../jain-granite`): PEB shed look, GI cladding, shutters, louvres, gutters, ridge caps.

- **Layout:** owner's SolarEdge screenshot (north up) and 2D landscape v1.2.
  - 120 × Adani 625 Wp in landscape on the south shed.
  - South shed: gable roof, ridge east–west, 10° slope (from the owner).
  - North face: L1, L2. South face: L3, L4. Each group is 5 rows × 6.
- **Heights (from the owner):** both big sheds about 12 m; the two small sheds about 7 m. Roof slopes of the north shed and the small sheds are assumed.
- **Walkways:** 300 mm GI grating in the gaps between groups, along the ridge and down the west side. A caged roof ladder on the west wall, south end.
- Turbo ventilators sit where the SolarEdge model shows them. The yard, road, compound wall and trees are representative.

```bash
node build.mjs     # -> output/Express-Cranes_3D-Viewer_v1.html (single file, opens offline)
node render.mjs    # -> output/stills/*.png (no video unless asked)
```
