# ReactBOM

KiCad plugin fork derived from [InteractiveHtmlBom](https://github.com/openscopeproject/InteractiveHtmlBom). ReactBOM reuses the upstream PCB parsers and `pcbdata` extraction pipeline, but its purpose in this monorepo is **data export**, not shipping a self-contained HTML viewer.

The output is the same `pcbdata` object the original plugin embeds in generated BOM pages—optionally **LZ-compressed and base64-encoded**—for consumption by [IBOMReact](../../IBOMReact/).

## Relationship to upstream

| | Upstream InteractiveHtmlBom | ReactBOM |
|---|---|---|
| **Goal** | Single-file HTML BOM you can open offline | `pcbdata` files for React apps |
| **Viewer** | Bundled JS/CSS in `ibom.html` | [IBOMReact](../../IBOMReact/) |
| **Source** | Full plugin | Fork; core parsing/compression borrowed from upstream |

Plugin Python code lives under `InteractiveHtmlBom/` and remains largely compatible with upstream. Credit and MIT license terms from the original project apply—see `LICENSE`.

Additional borrowed code (also MIT): KiBom `units.py`, svgpathtools-derived `svgpath.py`.

## Data pipeline

```
KiCad PCB (.kicad_pcb)
        │
        ▼
   ReactBOM plugin          ← parsers, BOM fields, layer extraction
        │
        ▼
   pcbdata (JSON)           ← see DATAFORMAT.md
        │
        ├── uncompressed JSON  →  {project}.ibom.json
        │
        └── LZ-String base64   →  {project}.ibom.txt (or inline in HTML)
                │
                ▼
           IBOMReact loadPcbData()
```

## Output formats

ReactBOM builds the same structure documented in [DATAFORMAT.md](./DATAFORMAT.md): board geometry, footprints, pads, optional tracks/zones, BOM rows, and metadata.

**Compression is enabled by default.** The plugin uses the same LZ-String base64 encoding as upstream (`InteractiveHtmlBom/core/lzstring.py`).

IBOMReact accepts either format via `loadPcbData()`:

- **JSON file** — starts with `{`; full decompressed `pcbdata` object
- **Base64 text file** — single LZ-compressed string (no JSON wrapper)

### Getting a data file for IBOMReact

1. Install the plugin in KiCad (see [Installation](#installation)).
2. Open your board and run **Generate interactive BOM** (toolbar button or **Tools → External Plugins**).
3. Choose output directory and options. Disable **Enable compression** in the dialog if you want raw JSON.
4. After generation, use one of these artifacts:
   - **Compressed:** extract the base64 string from the `///PCBDATA///` section of the generated HTML (`LZString.decompressFromBase64("…")`), or save that string as a `.ibom.txt` file.
   - **Uncompressed:** with compression off, the embedded assignment is plain JSON; save it as `{project}.ibom.json`.

Example destination used elsewhere in this repo: `IBOMReact/public/audio-toy.ibom.json`.

## Installation

ReactBOM can be installed like the upstream KiCad plugin.

### KiCad PCM

Add this repository URL in **Plugin and Content Manager → Manage repositories → +**:

```
https://raw.githubusercontent.com/peon374/ReactBOM/refs/heads/master/repository.json
```

Then install **ReactBOM** from the catalog. The repo serves `packages-v1.json` from the same GitHub path (ReactBOM plugin only).

To rebuild the PCM zip and refresh `repository.json` / `packages-v1.json` after a version bump:

```bash
python3 update_pcm_repo.py
```

### Manual / development install

1. Clone this repository (or use it as a git submodule under `projects/ReactBOM`).
2. Point KiCad’s plugin search path at the directory containing `InteractiveHtmlBom/`, or symlink:

   ```bash
   ln -s /path/to/workweb/projects/ReactBOM/InteractiveHtmlBom \
     ~/.local/share/kicad/8.0/scripting/plugins/InteractiveHtmlBom
   ```

   Adjust the KiCad version segment (`8.0`, `9.0`, etc.) for your install.

3. Restart KiCad. The **Generate interactive BOM** action should appear.

### CLI (headless)

```bash
cd projects/ReactBOM
pip install -e .

INTERACTIVE_HTML_BOM_NO_DISPLAY=1 generate_interactive_bom /path/to/board.kicad_pcb
```

Run `generate_interactive_bom --help` for BOM fields, variant, netlist, and compression flags. Pass `--no-compression` for uncompressed embedded data.

### Python package

```bash
pip install -e .
```

Package metadata is in `pyproject.toml`. The console entry point is `generate_interactive_bom`.

## Configuration

Plugin options match upstream: BOM column fields (including schematic extras like MPN/LCSC), grouping, DNP handling, tracks/zones, net highlighting data, and compression. Settings are stored per project in `ibom.config.ini` next to the PCB file.

Refer to the [upstream wiki](https://github.com/openscopeproject/InteractiveHtmlBom/wiki) for field configuration and schematic integration details—the behavior is the same; only the intended consumer differs.

## Supported ECAD inputs

Inherited from upstream parsers:

- KiCad (`.kicad_pcb`)
- EasyEDA (`.json`)
- Eagle / Fusion 360 (`.brd`)
- Generic JSON
- Allegro (via export script)

## IBOMReact integration

Copy or serve the generated data file, then in your React app:

```tsx
import { InteractiveBOM, loadPcbData } from "ibomreact";
import "ibomreact/style.css";

const pcbData = await loadPcbData("/my-board.ibom.json");

<InteractiveBOM pcbData={pcbData} />
```

See [IBOMReact/README.md](../../IBOMReact/README.md) for component API, demo app, and build instructions.

## License

MIT — see [LICENSE](./LICENSE). Original InteractiveHtmlBom © openscopeproject contributors.
