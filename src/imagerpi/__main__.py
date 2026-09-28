from __future__ import annotations

import argparse

from .app import main


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="IMAGE.RPI — terminal image viewer for Raspberry Pi / Linux"
    )
    parser.add_argument("path", nargs="?", help="image file or directory to open")
    args = parser.parse_args()
    main(args.path)


if __name__ == "__main__":
    cli()
