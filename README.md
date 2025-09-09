# hdrUtils — UltraHDR (JPEG Gain Map) Testbed (Containerized)

> **TL;DR**: This repo is a **Linux-first testbed** for experimenting with [Google’s `libultrahdr`](https://github.com/google/libultrahdr) via a custom **libvips + UltraHDR** build, wrapped in a clean, reproducible **Docker runner**. It includes small Python scripts to **inspect** and **resize/compress** UltraHDR JPEGs without leaving the container. Future direction: a lightweight Python CLI built on top of `libultrahdr`/libvips.

---

## What this repository is (and isn’t)

- **Is:** a reproducible **containerized environment** to build libvips **with UltraHDR support** (enabled by `libultrahdr`) and to **test** UltraHDR workflows from Python (`pyvips`).
- **Is not:** a fork or re-packaging of `libultrahdr`. The authoritative source is the upstream project. We simply build it from source inside the image and provide convenient test scripts.
- **Status:** actively iterated for testing and experimentation; API/commands may change.

### Upstream & Attribution

- Core library: **Google `libultrahdr`** → <https://github.com/google/libultrahdr>
- Image samples & learning resource: **Greg Benz Photography** → <https://gregbenzphotography.com/>  
  Samples here are for testing only; visit Greg’s site for background, tutorials, and guidance.

---

## Why containerize?

- **Reproducible builds:** libvips + UltraHDR can be finicky across distros/versions. The Dockerfile pins a sane toolchain and builds from upstream on each image build.
- **Isolation:** no need to pollute your host with build deps, and you can re-build as upstream changes.
- **Host-agnostic testing:** although designed for Linux (Ubuntu 24.04 base), the same image can run on any Linux box with Docker. (Author runs on a Linux server “**nimbus**”; macOS hosts are intentionally out-of-scope here.)

---

## Repo layout

```
hdrUtils/
├─ docker/
│  ├─ Dockerfile        # Builds libultrahdr + libvips(uhdr) + pyvips runtime
│  ├─ compose.yml       # Runner service (mounts repo into /work)
│  └─ update.sh         # Helper to rebuild/push tagged images from upstream HEADs
├─ scripts/
│  ├─ ultrahdr_inspect.py  # Inspect UltraHDR JPEGs (gainmap, ICC, metadata)
│  └─ ultrahdr_ops.py      # Resize / crop / re-encode UltraHDR JPEGs
├─ samples/
│  ├─ ISO_JPG_P3_transcoding_test_Greg_Benz.jpg
│  ├─ ISO_JPG_P3_transcoding_test_Greg_Benz_profile.icc  # example output from inspect
│  └─ ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg
└─ src/hdrutils/… (future convenience wrappers live here)
```

---

## Requirements

- Linux host with **Docker** (and **docker compose v2**).  
- `docker buildx` available (modern Docker includes it).
- You can optionally export your host UID/GID for correct file ownership (Compose does this automatically).

---

## How the image is built

The container is a **two-stage** build:

1. **Builder stage** (Ubuntu 24.04): installs build toolchain, builds **`libultrahdr`** from source, then builds **`libvips`** with `-Duhdr=enabled` linking to that `libultrahdr` install.
2. **Runtime stage** (Ubuntu 24.04): installs libvips runtime deps, creates a small **Python venv** with `pyvips`, and exposes vips/py as tools.

See [`docker/Dockerfile`](docker/Dockerfile) for the exact steps.

### Build locally (once)

From repo root:

```bash
docker compose -f docker/compose.yml build
```

Verify `pyvips` sees UltraHDR support:

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  -c "import pyvips as v; print('pyvips', v.__version__); print('has uhdrload?', hasattr(v.Image,'uhdrload'))"
# Expected:
# pyvips 3.x.x
# has uhdrload? True
```

> **Note:** Compose service mounts the repo root at **`/work`** inside the container and runs as your **host UID:GID**, so generated files are owned by you and sync cleanly (e.g., with Dropbox).

---

## Staying current with upstream (`update.sh`)

`docker/update.sh` resolves the current **HEAD commits** of upstream repos and tags an image accordingly:

- Image tag format: `<first12-of-libvips-commit>-<first12-of-libultrahdr-commit>`
- Also tags `:current` for convenience.

### Usage

From `docker/`:

```bash
# Build locally and load into the daemon
./update.sh

# Push to Docker Hub (set your repo first if desired)
IMAGE_REPO=suhailphotos/vips-uhdr ./update.sh --push

# Pin to specific commits (optional)
LIBVIPS_REF=<commit-or-branch> LIBUHDR_REF=<commit-or-branch> ./update.sh
```

After building/pushing with `update.sh`, you can point `docker/compose.yml` at your remote image by setting `IMAGE`:

```bash
# Example: use the freshly pushed image
IMAGE=suhailphotos/vips-uhdr:current docker compose -f docker/compose.yml run --rm pyvips -c "import pyvips"
```

> ✅ **Is the script still valid?** Yes — it uses `git ls-remote` to resolve commit hashes and passes those to the Docker build as `LIBVIPS_REF` / `LIBUHDR_REF`. It works whether you build **locally** (`--load`) or **push** (`--push`).

---

## Quick tests (P3 & sRGB)

Below commands assume you run them from repo root and have the sample images in `samples/`.

### 1) Inspect UltraHDR JPEG

The inspector prints the size of the embedded **gain map**, extracts the **ICC profile** (if present) next to your input (default `<name>_profile.icc`), and dumps key UltraHDR metadata fields.

**Display P3 sample:**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_inspect.py \
  /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg
```

**sRGB sample:**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_inspect.py \
  /work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg
```

**Custom ICC output path (optional):**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_inspect.py \
  /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg \
  /work/samples/P3_profile.icc
```

**Typical output** (varies by file):

```
675674 bytes of gainmap data
gainmap: 1080x1350 bands=3
620 bytes of ICC profile data
profile written to /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz_profile.icc
gainmap-max-content-boost = [16.0, 16.0, 16.0]
gainmap-min-content-boost = [1.0, 1.0, 1.0]
gainmap-gamma = [1.0, 1.0, 1.0]
…
```

### 2) Resize / crop / re-encode (preserves gain map)

`ultrahdr_ops.py` uses libvips’ `uhdrsave` to write an UltraHDR JPEG (gain map preserved).

**Compress only (no size change):**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_ops.py \
  /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg \
  /work/samples/P3_Q80.jpg \
  -q 80
```

**Resize to width 1024 (keep aspect):**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_ops.py \
  /work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg \
  /work/samples/sRGB_w1024.jpg \
  --width 1024 -q 85
```

**Crop then fit to a 1024×1024 square (smartcrop):**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_ops.py \
  /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg \
  /work/samples/P3_square_1024.jpg \
  --crop 100 100 2000 2000 --width 1024 --height 1024 -q 85
```

**Expected tail output:**

```
wrote: /work/samples/P3_square_1024.jpg
base: 1024x1024  gainmap: 1080x1350  quality: 85
```

---

## Tips on file ownership & paths

- Compose runs the container as `user: "${UID}:${GID}"`, so files created under `/work` are owned by you (helpful if this repo lives in **Dropbox**, etc.).
- All paths in the examples are under `/work/...` (the repo root mounted inside the container).
- To write outputs next to inputs, pass an explicit output path in `/work/samples/...` as shown above.

---

## Roadmap

- A **Python CLI** wrapper for common UltraHDR workflows (convert, inspect, batch resize).
- Optional **FastAPI** service for programmatic testing on the home-lab server.
- (Later) CI to build and push image tags automatically as upstream changes.

---

## License & acknowledgements

- This repo (scripts/docs/config) is **MIT-licensed** (see `LICENSE`).
- **`libultrahdr`** and **`libvips`** are licensed under their respective upstream terms — please consult their repositories.
- Sample images credited to **Greg Benz Photography**; used here for testing/demonstration only.

---

## Contact / issues

If you spot bugs or want a feature in the container/scripts, please open an issue or PR. For library behavior and UltraHDR implementation details, see the upstream projects:

- <https://github.com/google/libultrahdr>
- <https://github.com/libvips/libvips>
