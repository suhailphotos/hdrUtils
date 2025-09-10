# UltraHDR test report

**Repo:** `hdrUtils`  
**Host:** Ubuntu (nimbus) with Docker Buildx  
**Container:** libvips (uhdr enabled) + pyvips  
**Upstreams used for this build:** `LIBVIPS_REF=master`, `LIBUHDR_REF=main`  
**pyvips:** 3.0.0 (from container)

> The goal is to validate read/write behavior for UltraHDR (JPEG gain map) when compressing, resizing, and cropping. We test both P3 and sRGB source images (square 1080×1080).

---

## 0) Capability check

```bash
docker compose -f docker/compose.yml run --rm pyvips   -c "import pyvips as v; print('pyvips', v.__version__); print('has uhdrload?', hasattr(v.Image,'uhdrload'))"
```
**Observed**
```
pyvips 3.0.0
has uhdrload? True
```

---

## 1) Inspect originals

### 1A) P3 source

```bash
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_inspect.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz_profile.icc
```
**Observed**
```
643836 bytes of gainmap data
gainmap: 1080x1080 bands=3
620 bytes of ICC profile data
profile written to /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz_profile.icc
gainmap-max-content-boost = [16.0, 16.0, 16.0]
gainmap-min-content-boost = [1.0, 1.0, 1.0]
gainmap-gamma = [1.0, 1.0, 1.0]
gainmap-offset-sdr = [1.0000000116860974e-07, 1.0000000116860974e-07, 1.0000000116860974e-07]
gainmap-offset-hdr = [1.0000000116860974e-07, 1.0000000116860974e-07, 1.0000000116860974e-07]
gainmap-hdr-capacity-min = 1.0
gainmap-hdr-capacity-max = 16.0
gainmap-use-base-cg = 1
```

### 1B) sRGB source

```bash
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_inspect.py   /work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg   /work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz_profile.icc
```
**Observed**
```
681610 bytes of gainmap data
gainmap: 1080x1080 bands=3
3144 bytes of ICC profile data
profile written to /work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz_profile.icc
gainmap-max-content-boost = [16.0, 16.0, 16.0]
gainmap-min-content-boost = [1.0, 1.0, 1.0]
gainmap-gamma = [1.0, 1.0, 1.0]
gainmap-offset-sdr = [1.0000000116860974e-07, 1.0000000116860974e-07, 1.0000000116860974e-07]
gainmap-offset-hdr = [1.0000000116860974e-07, 1.0000000116860974e-07, 1.0000000116860974e-07]
gainmap-hdr-capacity-min = 1.0
gainmap-hdr-capacity-max = 16.56650161743164
gainmap-use-base-cg = 1
```

**Takeaway:** Both sources load with `uhdrload()`. ICC is present (P3 ICC ~620 B, sRGB ICC ~3.1 KB).

---

## 2) Compress (quality only)

```bash
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_ops.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_q75.jpg   -q 75
```
**Observed**
```
wrote: /work/samples/P3_q75.jpg
base: 1080x1080  gainmap: 1080x1080  quality: 75
```

Inspect re-saved file:
```
643929 bytes of gainmap data
gainmap: 1080x1080 bands=3
620 bytes of ICC profile data
profile written to /work/samples/P3_q75_profile.icc
gainmap-max-content-boost = [16.0, 16.0, 16.0]
… (HDR fields unchanged)
```

**Takeaway:** Recompression preserves UltraHDR structure & ICC. Gain map size changes slightly (expected).

---

## 3) Uniform resize (keep aspect)

```bash
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_ops.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_w512.jpg   --width 512 -q 85
```
**Observed**
```
wrote: /work/samples/P3_w512.jpg
base: 512x512  gainmap: 1080x1080  quality: 85
```

Inspect:
```
643929 bytes of gainmap data
gainmap: 1080x1080 bands=3
… (ICC present, HDR fields unchanged)
```

**Takeaway:** Base was resized, but the embedded gain map remained at 1080×1080 (current behavior of our simple script). Visual HDR looked correct in initial checks, but for production you may want to sync the map if your renderer expects matched geometry.

---

## 4) Crop

### 4A) Crop **without** syncing the map (intentional failure)

```bash
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_ops.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_crop_640_nosync.jpg   --crop 220 220 640 640 -q 85
```
**Observed**
```
wrote: /work/samples/P3_crop_640_nosync.jpg
base: 640x640  gainmap: 1080x1080  quality: 85
```
Inspect:
```
gainmap: 1080x1080 … (unchanged)
```

**Takeaway:** This intentionally demonstrates the mismatch—base is cropped but gain map isn’t.

### 4B) Crop **with** synchronized map

```bash
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_crop_sync.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_crop_640_sync.jpg   --crop 220 220 640 640 -q 85
```
**Observed**
```
wrote: /work/samples/P3_crop_640_sync.jpg
base: 640x640  gainmap: 640x640
```
Inspect:
```
83254 bytes of gainmap data
gainmap: 640x640 bands=3
… (ICC present, HDR fields unchanged)
```

**Takeaway:** Proportional crop of the gain map restores alignment. Visual inspection confirms expected HDR behavior.

---

## Conclusions

- **Read/write via libvips+pyvips works** for UltraHDR: ICC preserved; UltraHDR metadata intact.
- **Recompress-only** pipelines are safe.
- **Uniform resize** without syncing the gain map produced visually-correct results in quick checks, but geometry differs; consider syncing map in strict pipelines.
- **Cropping** without syncing the gain map causes obvious mismatch; **synchronized crop** fixes it (see `scripts/ultrahdr_crop_sync.py`).

---

## Next steps / suggestions

- Add tests for **resize+crop** with map sync (scale the cropped map before re-embedding).
- Add tests for **non-square** sources, large up/downscales, different qualities, and rotation/mirror.
- Compare output against **Android** or Chrome UltraHDR renderers to quantify deltas.
- Automate via CI (GitHub Actions) with a matrix of sizes/qualities and P3 vs sRGB.

---

## Reproduce locally

From repo root:

```bash
# build
cd docker && docker compose build && cd ..

# sanity
docker compose -f docker/compose.yml run --rm pyvips   -c "import pyvips as v; print('pyvips', v.__version__); print('has uhdrload?', hasattr(v.Image,'uhdrload'))"

# inspect P3 and sRGB
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_inspect.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz_profile.icc

docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_inspect.py   /work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz.jpg   /work/samples/ISO_JPG_sRGB_transcoding_test_Greg_Benz_profile.icc

# recompress, resize, crop (no-sync), crop (sync)
docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_ops.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_q75.jpg -q 75

docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_ops.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_w512.jpg --width 512 -q 85

docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_ops.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_crop_640_nosync.jpg --crop 220 220 640 640 -q 85

docker compose -f docker/compose.yml run --rm pyvips   /work/scripts/ultrahdr_crop_sync.py   /work/samples/ISO_JPG_P3_transcoding_test_Greg_Benz.jpg   /work/samples/P3_crop_640_sync.jpg --crop 220 220 640 640 -q 85
```

If you discover an inconsistency (e.g., renderer-specific behavior), please open an issue with the CLI used, outputs, and a small repro sample.
