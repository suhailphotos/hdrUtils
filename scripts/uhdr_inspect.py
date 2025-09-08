#!/usr/bin/env python3
import sys
import pyvips

if not hasattr(pyvips.Image, "uhdrload"):
    raise RuntimeError("This libvips build has no uhdrload()")

if len(sys.argv) < 2:
    print("usage: uhdr_inspect.py <ultrahdr.jpg> [icc_out=profile.icc]")
    sys.exit(2)

in_path = sys.argv[1]
icc_out = sys.argv[2] if len(sys.argv) > 2 else "profile.icc"

# Load UltraHDR JPEG (base + gain map in metadata)
image = pyvips.Image.uhdrload(in_path)

# Gain map buffer -> size + decode to an image
gainmap_buffer = image.get("gainmap")
print(f"{len(gainmap_buffer)} bytes of gainmap data")
gainmap = pyvips.Image.jpegload_buffer(gainmap_buffer)
print(f"gainmap = {gainmap}")

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

# Dump gain-map metadata fields
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
