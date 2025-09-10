#!/usr/bin/env python3
import argparse, pyvips, math

def main():
    ap = argparse.ArgumentParser(description="Crop UltraHDR with a synchronized gain map.")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--crop", nargs=4, type=int, metavar=("X","Y","W","H"), required=True)
    ap.add_argument("-q", "--quality", type=int, default=85)
    args = ap.parse_args()

    img = pyvips.Image.uhdrload(args.input)
    gm  = pyvips.Image.jpegload_buffer(img.get("gainmap"))

    X, Y, W, H = args.crop
    # Crop base
    img2 = img.crop(X, Y, W, H)

    # Map base->gainmap coordinates (proportional)
    Wb, Hb = img.width, img.height
    Wg, Hg = gm.width, gm.height
    xg = round(X * Wg / Wb);  yg = round(Y * Hg / Hb)
    wg = max(1, round(W * Wg / Wb));  hg = max(1, round(H * Hg / Hb))
    gm2 = gm.crop(xg, yg, wg, hg)

    # (Optional) if you also resize the base later, apply the **same** scaling to gm2.

    # Re-embed the updated gain map bytes
    gm_bytes = gm2.jpegsave_buffer(Q=args.quality)
    img2.set("gainmap", gm_bytes)

    pyvips.Operation.call("uhdrsave", img2, args.output, Q=args.quality)

    out = pyvips.Image.uhdrload(args.output)
    gm_out = pyvips.Image.jpegload_buffer(out.get("gainmap"))
    print(f"wrote: {args.output}")
    print(f"base: {out.width}x{out.height}  gainmap: {gm_out.width}x{gm_out.height}")

if __name__ == "__main__":
    main()
