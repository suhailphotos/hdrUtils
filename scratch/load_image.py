#!/usr/bin/env python3
import sys
from pathlib import Path
import pyvips

def load_image(path: str) -> pyvips.Image:
    """Try UltraHDR first; if not supported or not UltraHDR, load normally."""
    if hasattr(pyvips.Image, "uhdrload"):
        try:
            return pyvips.Image.uhdrload(path)
        except pyvips.Error:
            pass  # not UltraHDR or op failed; fall back below
    return pyvips.Image.new_from_file(path, access="sequential")

def has_meta(img: pyvips.Image, key: str) -> bool:
    return img.get_typeof(key) != 0  # 0 => missing

def main():
    if len(sys.argv) < 2:
        print("usage: load_image.py <image> [out_preview.png]")
        sys.exit(2)

    in_path = sys.argv[1]
    out_preview = sys.argv[2] if len(sys.argv) > 2 else None

    img = load_image(in_path)

    print("== BASIC INFO ==")
    print(f"path: {Path(in_path).resolve()}")
    print(f"size: {img.width}x{img.height}")
    print(f"bands: {img.bands}  format: {img.format}  interpretation: {img.interpretation}")

    print("\n== METADATA ==")
    print(f"icc-profile-data: {'present' if has_meta(img, 'icc-profile-data') else 'missing'}")
    print(f"exif-data:        {'present' if has_meta(img, 'exif-data') else 'missing'}")

    # UltraHDR bits (only present when loaded via uhdrload on a true UltraHDR JPEG)
    print("\n== ULTRA HDR ==")
    if has_meta(img, "gainmap"):
        gm_buf = img.get("gainmap")
        gainmap = pyvips.Image.jpegload_buffer(gm_buf)
        print(f"gainmap bytes: {len(gm_buf)}")
        print(f"gainmap image: {gainmap.width}x{gainmap.height} bands={gainmap.bands} fmt={gainmap.format}")
    else:
        print("gainmap: <missing> (likely not an UltraHDR JPEG)")

    # Optional: write a quick preview to trigger evaluation and verify pipeline
    if out_preview:
        img.write_to_file(out_preview)
        print(f"\npreview written: {out_preview}")

if __name__ == "__main__":
    sys.exit(main())
