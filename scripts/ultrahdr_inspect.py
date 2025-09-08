#!/usr/bin/env python3
import sys, argparse
import pyvips

def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", help="UltraHDR JPEG path")
    args = p.parse_args()

    image = pyvips.Image.uhdrload(args.input)

    # Gain map buffer
    gainmap_buf = image.get("gainmap")
    print(f"{len(gainmap_buf)} bytes of gainmap data")
    gainmap = pyvips.Image.jpegload_buffer(gainmap_buf)
    print(f"gainmap: {gainmap.width}x{gainmap.height} bands={gainmap.bands}")

    # ICC profile
    profile = image.get("icc-profile-data")
    print(f"{len(profile)} bytes of ICC profile data")
    with open("profile.icc", "wb") as f:
        f.write(profile)
    print("profile written to profile.icc")

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
        except Exception as e:
            print(f"{name} = <missing>")

if __name__ == "__main__":
    sys.exit(main())
