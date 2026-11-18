# NRG Technologists — standing rules for solar design work (CLAUDE.md v1.1, 2026-11-18)

The owner is not a coder. These rules come from the owner's corrections on real projects. Follow them on
**every** project, without being told again.

## Raised GI structure on flat terraces (2D, 3D views, videos)
- **One column under each panel row**, never one under each panel. A 2-row table has 2 columns per frame;
  a 3-row table has 3 columns per frame.
- **One frame (a rafter down the slope plus its columns) for every ~2.5 panels** along a table, about 2.8 m
  for 620–625 Wp portrait panels. Never one rafter or one leg per panel column.
- Purlins run along the rows under the top and bottom edge of the panels; base plate under every column.
- Each table gets its own frames. Never join two separate tables into one frame.
- Panels show only a thin edge line. A wide light border round each panel looks like a rafter under every panel.
- All of this is built into the Design Lab 3D viewer (design-lab/worker/viewer/viewer.template.html v2.2,
  worker v1.15.2). Keep it that way when the viewer changes; check the "Structure" view (under the panels).
- Usual tilt 10° facing south (10–12° when asked). Heights are given per block by the owner: use them.

## Drawing the roof
- Always ask/confirm which way north is; use the owner's AutoCAD/SolarEdge lines, not a guess.
- Staircase cabins, lift rooms and other boxes must be **square to the building** (same rotation as the
  building and the panel tables) and measured from the drawing's dashed/solid lines.
- Number blocks from the south (B1 = southmost) unless the owner says otherwise.
- Use only the area the owner marks; keep the rest of the terrace free.

## Look of the buildings
- Apartment towers: keep them clean — cream walls, a darker base and corner strips, only one or two stacks of
  windows per wall with split-AC units; never a window everywhere. Use a street-view photo when the owner gives
  one (viewer v2.3 does this for residential buildings of 6+ floors).

## Order of work and deliverables
1. 2D layout first, for approval. 2. Then 3D views (Design Lab viewer look, NRG branding).
3. Then proposal PDF + Gmail draft (owner attaches the PDF). 4. Walk-around video only when asked:
   one 1080p MP4 only, no extra WhatsApp copy unless asked.
- Every file name and file carries a version number (e.g. "Project - 3D v1.2 - 05 top.png"); keep old versions.
- Energy estimate: kWp × 1450 units a year.
- When giving the owner code or files to paste: give full files, never patches; ask for their latest copy
  first; check the new version against the old so nothing is lost.
