# hdrUtils — UltraHDR (JPEG gain map) test harness (Docker + pyvips)

> **Status:** Work-in-progress test harness. This repo is *not* a fork of the UltraHDR codec. It contains a reproducible build of **libvips** with **libultrahdr** support enabled, plus a few Python scripts to exercise common workflows (inspect, compress, resize, crop).

## What this repository is (and isn’t)

- **Goal (now):** Provide a clean, repeatable environment to **test** UltraHDR (JPEG gain map) read/write through **libvips** and **pyvips**, and to validate practical workflows (thumbnailing, compression, cropping).
- **Future direction:** Likely a small Python CLI/SDK to make common UltraHDR operations convenient (e.g., “resize + keep HDR”).
- **Not included:** The codec itself. The authoritative sources remain upstream:
  - **UltraHDR reference & tooling:** https://github.com/google/libultrahdr
  - **Image processing library:** https://github.com/libvips/libvips
  - **Python bindings:** https://github.com/libvips/pyvips

**Sample images** used for testing are courtesy of **Greg Benz Photography**: https://gregbenzphotography.com/
Please see the `samples/` folder and attribution below.

---

## TL;DR — Results

- **Full findings & console output:** see **[TEST_REPORT.md](TEST_REPORT.md)**.
- **Quick artifact links (plain links; click to view):**
  - **Sources:**
    - P3: [`samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg`](samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg)
    - sRGB: [`samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg`](samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg)
  - **Outputs (generated in this repo):**
    - Recompress (Q=75): [`samples/P3_q75.jpg`](samples/P3_q75.jpg) · ICC dump: [`samples/P3_q75_profile.icc`](samples/P3_q75_profile.icc)
    - Uniform resize to 512px: [`samples/P3_w512.jpg`](samples/P3_w512.jpg) · ICC: [`samples/P3_w512_profile.icc`](samples/P3_w512_profile.icc)
    - **Crop (no sync)** — intentional mismatch: [`samples/P3_crop_640_nosync.jpg`](samples/P3_crop_640_nosync.jpg) · ICC: [`samples/P3_crop_640_nosync_profile.icc`](samples/P3_crop_640_nosync_profile.icc)
    - **Crop (synced)** — map aligned: [`samples/P3_crop_640_sync.jpg`](samples/P3_crop_640_sync.jpg) · ICC: [`samples/P3_crop_640_sync_profile.icc`](samples/P3_crop_640_sync_profile.icc)

---

## Why containerize?

- **Reproducible**: Pins to known commits of `libvips` and `libultrahdr` on every build.
- **Isolated**: No OS package drift. Everything under `/opt/vips` inside the image.
- **Fast updates**: `docker/update.sh` resolves and tags images against upstream HEADs or your chosen refs.
- **Single host**: Intended to run on a Linux host (e.g., my `nimbus`). I don’t run Docker for Mac for this project.

---

## What gets built

A multi-stage `Dockerfile` that:

1. Clones and builds **libultrahdr** (CMake + Ninja), installs to `/opt/vips`.
2. Clones and builds **libvips** with `-Duhdr=enabled` (Meson/Ninja), installs to `/opt/vips`.
3. Produces a small runtime layer with system libs + **pyvips** in a venv.
4. `docker/compose.yml` defines a `pyvips` service with `entrypoint: ["python3"]` and mounts your project root at `/work`.

**Result:** You can run one-shot Python commands, or invoke the helper scripts in `scripts/`, all against a libvips build that understands UltraHDR’s `uhdrload` / `uhdrsave` operations.

---

## Prerequisites

- Docker with Buildx (e.g., Docker 28+)
- Linux host (tested on Ubuntu 24.04)
- Git (to clone this repo)

---

## Build the image

```bash
cd docker
docker compose build
```

By default, this builds from:
- `LIBVIPS_REF=master`
- `LIBUHDR_REF=main`

You can pin specific commits/branches via environment overrides when building, e.g.:

```bash
LIBVIPS_REF=v8.15.0 LIBUHDR_REF=main docker compose build
```

The `Dockerfile` is here: [`docker/Dockerfile`](docker/Dockerfile).

---

## Updating to latest upstream (optional)

Use the helper script to resolve HEAD commits and tag an image:

```bash
cd docker
./update.sh           # builds and loads into your local Docker
./update.sh --push    # builds and pushes to Docker Hub (set IMAGE_REPO first)
```

- The script tags images as `${IMAGE_REPO}:${first12(vips)}-${first12(uhdr)}` and `${IMAGE_REPO}:current`.
- Environment variables:
  - `IMAGE_REPO` (default: `suhailphotos/vips-uhdr`)
  - `PLATFORMS` (default: `linux/amd64`)
  - Optional pins: `LIBVIPS_REF`, `LIBUHDR_REF`

Script: [`docker/update.sh`](docker/update.sh).

---

## Sanity check

```bash
docker compose -f docker/compose.yml run --rm pyvips   -c "import pyvips as v; print('pyvips', v.__version__); print('has uhdrload?', hasattr(v.Image,'uhdrload'))"
```

Expected: `pyvips 3.x` and `has uhdrload? True`.

---

## Using the container

> All examples assume you run from the repo root and mount it into the container at `/work` via `docker/compose.yml`.

### 1) Inspect an UltraHDR JPEG

```bash
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_inspect.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz_profile.icc
```

What it prints:

- Size of embedded **gain map** (JPEG) and its decoded dimensions
- Presence/size of **ICC profile** (written to the optional output path)
- Key UltraHDR fields (content boost, gamma, offsets, HDR capacity, etc.)

Script: [`scripts/ultrahdr_inspect.py`](scripts/ultrahdr_inspect.py).

### 2) Compress (change JPEG quality only)

```bash
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_ops.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_q75.jpg   -q 75
```

- Re-saves as UltraHDR JPEG using libvips’ `uhdrsave`.
- **Gain map** and **ICC** are preserved.

### 3) Uniform resize (keep aspect)

```bash
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_ops.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_w512.jpg   --width 512 -q 85
```

- Base image is resized to 512×512.
- Current script preserves the original gain map as-is (see *Cropping & sync* below).

### 4) Crop (two approaches)

**A. Intentional “no-sync” crop** — demonstrates the failure mode:

```bash
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_ops.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_crop_640_nosync.jpg   --crop 220 220 640 640 -q 85
```

The base is cropped to 640×640, but the gain map is **not**—HDR alignment may be wrong.

**B. Synchronized crop** — keeps base and gain map aligned:

```bash
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_crop_sync.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_crop_640_sync.jpg   --crop 220 220 640 640 -q 85
```

Script: [`scripts/ultrahdr_crop_sync.py`](scripts/ultrahdr_crop_sync.py).

> This script decodes the embedded gain map, crops it proportionally to the base crop, then re-embeds it before `uhdrsave`. For combined **resize+crop**, you must apply the **same scale** to the gain map region too (the script shows where to add that).

---

## Sample assets

Located in [`samples/`](samples/):

- `ISO_JPG_P3_transcoding_test_Greg_Benz.jpg` (Display P3)
- `ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg` (sRGB)

Both are courtesy of **Greg Benz Photography** (https://gregbenzphotography.com). Extracted ICCs are checked into this repo for reference after inspection runs.

---

## Repository layout

```
hdrUtils/
├─ docker/
│  ├─ Dockerfile        # builds libultrahdr + libvips (uhdr enabled) + pyvips
│  ├─ compose.yml       # one-shot runner service (entrypoint: python3)
│  └─ update.sh         # resolve refs, build/tag/push
├─ scripts/
│  ├─ ultrahdr_inspect.py    # dump gainmap, ICC, UltraHDR fields
│  ├─ ultrahdr_ops.py        # compress/resize/crop (no map sync)
│  └─ ultrahdr_crop_sync.py  # crop with synchronized gain map
├─ samples/                  # test images (from Greg Benz) + extracted ICCs
└─ src/hdrutils/             # (future) Python package scaffolding
```

---

## Notes & limitations

- **Resizing & cropping**: UltraHDR carries an embedded JPEG gain map. If you crop or non-uniformly resize, you must keep the map aligned with the base. The `ultrahdr_crop_sync.py` script demonstrates the approach.
- **Smart crops / arbitrary transforms**: Avoid for now unless you can compute and apply the same transform to the gain map image.
- **Color management**: ICC is preserved by our scripts; verify with `ultrahdr_inspect.py` for your assets (P3 vs sRGB both tested).
- **Performance**: libvips is streaming and fast; Python bindings are thin. For production pipelines, a native binary or long-lived worker is ideal.

---

## License & attribution

- This repo: **MIT** (see `LICENSE`).
- UltraHDR reference & tools: **google/libultrahdr** (see its repo for license/terms).
- libvips / pyvips: (see their repos for license/terms).
- Sample images © **Greg Benz Photography**; used here for testing with attribution.

If you have questions or find issues, please open an issue or PR. PRs adding automated tests for more edge cases (resize+crop sync, rotation, etc.) are very welcome.

