from typing import Optional, Tuple
import argparse
import os
import shutil
import subprocess
import struct
import atexit


ultra_hdr_app_path: Optional[str] = None
ffmpeg_path: Optional[str] = None


def main():
    """main"""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("input_file", help="input file, jpeg")
    arg_parser.add_argument("output_file", help="output file, jpeg")
    args = arg_parser.parse_args()

    _setup_paths()

    w, h = _get_size_from_jpeg(args.input_file)
    print("Input size:", w, h)
    # Need to crop to even size, otherwise Ultra HDR encoding fails.
    w -= w % 2
    h -= h % 2
    print("Output (cropped) size:", w, h)

    yuv_file = args.output_file + ".yuv"
    _make_yuv_p010(args.input_file, yuv_file, (w, h))
    # atexit.register(os.remove, yuv_file)  # yuv file not needed anymore -- temporary comment

    jpeg_cropped_file = args.output_file + ".cropped.jpeg"
    _make_jpeg_cropped(args.input_file, jpeg_cropped_file, (w, h))
    
    # atexit.register(os.remove, jpeg_cropped_file)  # cropped jpeg file not needed anymore -- temporary comment




def _setup_paths():
    global ultra_hdr_app_path, ffmpeg_path

    ultra_hdr_build_path = "./external/libultrahdr/build"  # hardcoded currently...
    assert os.path.exists(ultra_hdr_build_path)
    ultra_hdr_app_path = ultra_hdr_build_path + "/ultrahdr_app"
    assert os.path.exists(ultra_hdr_app_path), "libultrahdr not built yet?"

    ffmpeg_path = shutil.which("ffmpeg")
    assert ffmpeg_path is not None, "ffmpeg not installed?"

def _get_size_from_jpeg(input_jpeg_file: str) -> Tuple[int, int]:
    # https://stackoverflow.com/questions/8032642/how-can-i-obtain-the-image-size-using-a-standard-python-class-without-using-an
    with open(input_jpeg_file, "rb") as fhandle:
        size = 2
        ftype = 0
        while not 0xC0 <= ftype <= 0xCF or ftype in (0xC4, 0xC8, 0xCC):
            fhandle.seek(size, 1)
            byte = fhandle.read(1)
            while ord(byte) == 0xFF:
                byte = fhandle.read(1)
            ftype = ord(byte)
            size = struct.unpack(">H", fhandle.read(2))[0] - 2
        # We are at a SOFn block
        fhandle.seek(1, 1)  # Skip `precision' byte.
        height, width = struct.unpack(">HH", fhandle.read(4))
        return width, height

def _make_yuv_p010(input_jpeg_file: str, output_yuv_p010_file: str, size: Tuple[int, int]):
    """Make YUV P010 from JPEG"""
    args = [
        ffmpeg_path,
        "-i",
        input_jpeg_file,
        "-filter:v",
        f"crop={size[0]}:{size[1]}:0:0,format=p010",
        output_yuv_p010_file,
    ]
    print("$", " ".join(args))
    subprocess.check_call(args)

def _make_jpeg_cropped(input_jpeg_file: str, output_jpeg_file: str, size: Tuple[int, int]):
    """Make JPEG cropped"""
    args = [ffmpeg_path, "-i", input_jpeg_file, "-filter:v", f"crop={size[0]}:{size[1]}:0:0", output_jpeg_file]
    print("$", " ".join(args))
    subprocess.check_call(args)


if __name__ == "__main__":
    main()
