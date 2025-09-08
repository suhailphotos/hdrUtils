#!/usr/bin/env python3
import argparse, pyvips

def load_ultrahdr(path: str) -> pyvips.Image:
    return pyvips.Image.uhdrload(path)

def save_ultrahdr(img: pyvips.Image, out_path: str, quality: int = 90):
    # libvips exposes "uhdrsave" as an operation via pyvips
    pyvips.Operation.call("uhdrsave", img, out_path, Q=quality)

def main():
    ap = argparse.ArgumentParser(
        description="Resize/crop/compress Ultra HDR (JPEG gain map) with libvips."
    )
    ap.add_argument("input")
    ap.add_argument("output")
    # choose ONE of the sizing modes (scale or target width/height)
    ap.add_argument("--scale", type=float, help="Uniform scale (e.g. 0.5 for half-size)")
    ap.add_argument("--width", type=int, help="Resize to this width (keeps aspect)")
    ap.add_argument("--height", type=int, help="Resize to this height (keeps aspect)")
    # optional crop
    ap.add_argument("--crop", nargs=4, type=int, metavar=("LEFT","TOP","WIDTH","HEIGHT"),
                    help="Crop rectangle in pixels before resize")
    # JPEG quality
    ap.add_argument("-q", "--quality", type=int, default=90, help="JPEG quality (default 90)")
    args = ap.parse_args()

    img = load_ultrahdr(args.input)

    # Optional crop first (common workflow: crop → resize)
    if args.crop:
        l, t, w, h = args.crop
        img = img.crop(l, t, w, h)

    # Optional resize
    if args.scale:
        img = img.resize(args.scale)
    elif args.width and not args.height:
        img = img.resize(args.width / img.width)
    elif args.height and not args.width:
        img = img.resize(args.height / img.height)
    elif args.width and args.height:
        # two-step: scale to fit, then smartcrop to requested box
        scale = min(args.width / img.width, args.height / img.height)
        img = img.resize(scale).smartcrop(args.width, args.height)

    # Save as Ultra HDR JPEG (base + embedded gain map)
    save_ultrahdr(img, args.output, quality=args.quality)

    # Quick verification
    out = pyvips.Image.uhdrload(args.output)
    gm  = pyvips.Image.jpegload_buffer(out.get("gainmap"))
    print(f"wrote: {args.output}")
    print(f"base: {out.width}x{out.height}  gainmap: {gm.width}x{gm.height}  quality: {args.quality}")

if __name__ == "__main__":
    main()
