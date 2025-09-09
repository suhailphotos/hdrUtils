#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import pyvips

def main():
    if not hasattr(pyvips.Image, "uhdrload"):
        raise RuntimeError("This libvips build has no uhdrload()")

    p = argparse.ArgumentParser(description="Inspect an UltraHDR (JPEG gain map) image.")
    p.add_argument("input", help="Path to UltraHDR JPEG")
    p.add_argument("icc_out", nargs="?", help="Optional path to write ICC profile")
    args = p.parse_args()

    in_path = Path(args.input).resolve()
    icc_out = Path(args.icc_out).resolve() if args.icc_out else in_path.with_name(in_path.stem + "_profile.icc")

    # Load UltraHDR JPEG (base + embedded gain map)
    image = pyvips.Image.uhdrload(str(in_path))

    # Gain map buffer
    gainmap_buf = image.get("gainmap")
    print(f"{len(gainmap_buf)} bytes of gainmap data")
    gainmap = pyvips.Image.jpegload_buffer(gainmap_buf)
    print(f"gainmap: {gainmap.width}x{gainmap.height} bands={gainmap.bands}")

    # ICC profile (if present)
    try:
        profile = image.get("icc-profile-data")
        print(f"{len(profile)} bytes of ICC profile data")
        with open(icc_out, "wb") as f:
            f.write(profile)
        print(f"profile written to {icc_out}")
    except pyvips.Error:
        print("0 bytes of ICC profile data")
        print("(no ICC profile present)")

    # Known UltraHDR fields
    for name in [
        "gainmap-max-content-boost",
        "gainmap-min-content-boost",
        "gainmap-gamma",
        "gainmap-offset-sdr",
        "gainmap-offset-hdr",
        "gainmap-hdr-capacity-min",
        "gainmap-hdr-capacity-max",
        "gainmap-use-base-cg",
    ]:
        try:
            field = image.get(name)
            print(f"{name} = {field}")
        except pyvips.Error:
            print(f"{name} = <missing>")

if __name__ == "__main__":
    sys.exit(main())
