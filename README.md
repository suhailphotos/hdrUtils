# hdrUtils — UltraHDR (JPEG Gain Map) with libvips in Docker

This repo gives you a **repeatable, isolated** way to test and process **UltraHDR** (JPEG gain‑map) images using **libvips** + **libultrahdr**—built from source—wrapped by Python **pyvips** inside a Docker runner. No host-level libvips installs; just run the container against your working tree.

> Target machine: **nimbus** (Ubuntu Server with Docker). macOS hosts are intentionally not used for Docker here.

---

## Contents

- [What you get](#what-you-get)
- [Repo layout](#repo-layout)
- [Prereqs](#prereqs)
- [Build the image (local-dev mode)](#build-the-image-local-dev-mode)
- [Update/pin libvips/libultrahdr (update.sh)](#updatepin-libvipslibultrahdr-updatesh)
- [Sanity check](#sanity-check)
- [Test samples: sRGB + Display‑P3](#test-samples-srgb--displayp3)
- [Inspect an UltraHDR JPEG (extract ICC + gain‑map fields)](#inspect-an-ultrahdr-jpeg-extract-icc--gainmap-fields)
- [Resize / crop / recompress UltraHDR](#resize--crop--recompress-ultrahdr)
- [Ownership & Dropbox sync notes](#ownership--dropbox-sync-notes)
- [Switching to a prebuilt image](#switching-to-a-prebuilt-image)
- [Troubleshooting quick hits](#troubleshooting-quick-hits)

---

## What you get

- **Reproducible build** of:
  - `google/libultrahdr` (CMake) → installed into `/opt/vips`
  - `libvips` with **UltraHDR support** (`-Duhdr=enabled`) via **Meson** → also under `/opt/vips`
- **Python runner** with a dedicated venv and **pyvips**.
- A **docker-compose** service `pyvips` which mounts your repo into `/work` and runs Python inside the container.
- Convenience scripts:
  - `scripts/ultrahdr_inspect.py` — dump gain‑map metadata and ICC; writes ICC next to the input by default.
  - `scripts/ultrahdr_ops.py` — resize/crop/recompress while preserving UltraHDR (base + gain map) via `uhdrsave`.

Why Meson for libvips? The official libvips build uses **Meson**; enabling UltraHDR in-tree is a Meson option (`-Duhdr=enabled`), so we follow upstream’s supported path.

---

## Repo layout

```
hdrUtils/
├── docker/
│   ├── Dockerfile        # multi-stage build: libultrahdr + libvips(+uhdr) → runtime with pyvips
│   ├── compose.yml       # runner service (mounts project at /work; entrypoint=python3)
│   └── update.sh         # buildx updater that pins HEAD SHAs and tags :current + content tag
├── samples/
│   ├── ISO_JPG_P3_transcoding_test_Greg_Benz.jpg
│   ├── ISO_JPG_P3_transcoding_test_Greg_Benz_profile.icc   # provided reference ICC for P3 sample
│   └── ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg
└── scripts/
    ├── ultrahdr_inspect.py
    └── ultrahdr_ops.py
```

---

## Prereqs

- **Docker** and **buildx** on `nimbus` (already present).
- You are in the repo root when running commands shown below (unless explicitly `cd docker/`).

---

## Build the image (local-dev mode)

This uses the compose file under `docker/` which **builds** from `Dockerfile` and tags the image as `suhailphotos/vips-uhdr:local` by default.

```bash
# from repo root
docker compose -f docker/compose.yml build
```

You can pin specific revisions at build time:

```bash
# Examples (tag/branch/SHA all work)
LIBVIPS_REF=master LIBUHDR_REF=main \
docker compose -f docker/compose.yml build
```

The Dockerfile installs both libraries under `/opt/vips` and sets up a Python venv with `pyvips`.

---

## Update/pin libvips/libultrahdr (update.sh)

`docker/update.sh` is a convenience script that resolves **HEAD SHAs** for both repos (unless you provide a `LIBVIPS_REF` / `LIBUHDR_REF`) and builds a content-addressed tag. It also tags `:current`.

```bash
# from repo root
cd docker

# Build locally and load to the Docker daemon (no push)
./update.sh

# Build and push to Docker Hub (requires you to be logged in; will tag :current)
./update.sh --push

# Pin to specific commits or tags
LIBVIPS_REF=v8.15.0 \
LIBUHDR_REF=main \
./update.sh --push
```

**Using the freshly built tag with compose:** either set `IMAGE` when you run compose or edit `compose.yml` to point at the tag you want.

```bash
# Use the image produced by update.sh (e.g., :current) without rebuilding
IMAGE=suhailphotos/vips-uhdr:current \
docker compose -f docker/compose.yml run --rm pyvips -c "import pyvips; print('ok')"
```

> If both `build:` and `image:` exist in compose, Compose may still build locally. To **force** using a prebuilt image, temporarily comment out `build:` lines in `docker/compose.yml` or pass `IMAGE=...` and ensure the tag exists locally (or pull it).

---

## Sanity check

Confirm the Python runner sees UltraHDR operations:

```bash
docker compose -f docker/compose.yml run --rm pyvips -c \
"import pyvips as v; print('pyvips', v.__version__); print('has uhdrload?', hasattr(v.Image,'uhdrload'))"
# Expect:
# pyvips 3.x
# has uhdrload? True
```

---

## Test samples: sRGB + Display‑P3

We include two sample UltraHDR JPEGs (from Greg Benz): one **sRGB**, one **Display‑P3**.

Paths (inside the container these are available under `/work/samples/...`):

- `/work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg`
- `/work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg`

---

## Inspect an UltraHDR JPEG (extract ICC + gain‑map fields)

The inspector **writes the ICC profile next to the input** by default, named `<stem>_profile.icc`. You can also pass an explicit output path as the second argument.

**sRGB test**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_inspect.py \
  /work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg

# Output excerpt:
#  <N> bytes of gainmap data
#  gainmap: <w>x<h> bands=<b>
#  <M> bytes of ICC profile data
#  profile written to /work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz_profile.icc
#  gainmap-max-content-boost = [...]
#  ...
```

**Display‑P3 test**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_inspect.py \
  /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg

# You should see a similar dump; ICC gets written as
# /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz_profile.icc
```

**Explicit ICC output path**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_inspect.py \
  /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg \
  /work/samples/P3.icc
```

---

## Resize / crop / recompress UltraHDR

`ultrahdr_ops.py` preserves UltraHDR (base + gain map) using `uhdrsave`.

**Compress only (no resize), Q=80**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_ops.py \
  /work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg \
  /work/samples/sRGB_Q80.jpg \
  -q 80
```

**Resize to width=1024 (keep aspect)**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_ops.py \
  /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg \
  /work/samples/P3_w1024.jpg \
  --width 1024 -q 85
```

**Center-crop to 1024×1024 via “fit then smartcrop”**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_ops.py \
  /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg \
  /work/samples/P3_square_1024.jpg \
  --width 1024 --height 1024 -q 85
```

**Manual crop box first, then fit + smartcrop**

```bash
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_ops.py \
  /work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg \
  /work/samples/sRGB_cropped_1024.jpg \
  --crop 100 100 2000 2500 --width 1024 --height 1024 -q 85
```

On success you’ll see a confirmation like:
```
wrote: /work/samples/P3_w1024.jpg
base: 1024x...  gainmap: ...  quality: 85
```

---

## Ownership & Dropbox sync notes

Compose maps your user with:
```yaml
user: "${UID:-1000}:${GID:-1000}"
```
To ensure files are owned by you (so Dropbox syncs immediately), always pass your host IDs when running:

```bash
UID=$(id -u) GID=$(id -g) \
docker compose -f docker/compose.yml run --rm pyvips \
  /work/scripts/ultrahdr_inspect.py /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg
```

If you accidentally created root-owned files, fix them from the host:
```bash
sudo chown -R "$(id -u)":"$(id -g)" samples/
```

---

## Switching to a prebuilt image

If you used `docker/update.sh --push` to publish `suhailphotos/vips-uhdr:current`, you can run without building locally:

```bash
IMAGE=suhailphotos/vips-uhdr:current \
docker compose -f docker/compose.yml run --rm pyvips -c "import pyvips; print('ok')"
```

To avoid local rebuilds, temporarily comment out the `build:` section in `docker/compose.yml` or ensure the prebuilt image exists locally (`docker pull suhailphotos/vips-uhdr:current`).

---

## Troubleshooting quick hits

- **`has uhdrload? False`** — your libvips wasn’t built with UltraHDR. Rebuild ensuring `-Duhdr=enabled` (the Dockerfile already does this).
- **Runtime can’t find `libwebpmux` / `libwebpdemux`** — the runtime stage needs WebP libs; they are included in `Dockerfile` (`libwebpmux3`, `libwebpdemux2`).
- **ICC written to unexpected place** — `ultrahdr_inspect.py` writes the ICC **beside the input** (derived name). Pass an explicit second path to override.
- **Files show up late in Dropbox** — usually an ownership issue; ensure `UID/GID` are passed so outputs are owned by your user.

---

## References

- `docker/Dockerfile` — full build details & options.
- `docker/update.sh` — content-addressed tagging of libvips/libultrahdr builds.
- `scripts/ultrahdr_inspect.py` — simple metadata/ICC extraction.
- `scripts/ultrahdr_ops.py` — resize/crop/compress preserving UltraHDR gain map.
