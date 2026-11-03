"""Convert PDF, image, and Word files to Base64 text files."""

import argparse
import base64
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
    ".doc",
    ".docx",
}


def convert_file(source: Path) -> Path:
    """Encode one supported file and save its Base64 text beside it."""
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {source.suffix}")
    if not source.is_file():
        raise FileNotFoundError(f"File not found: {source}")

    output = source.with_name(f"{source.name}.base64.txt")
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    output.write_text(encoded + "\n", encoding="ascii")
    return output


def main() -> None:
    """Convert files passed on the command line or in this folder."""
    parser = argparse.ArgumentParser(
        description="Convert PDFs, images, and Word documents to Base64 text."
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Files to convert; defaults to supported files in this folder.",
    )
    args = parser.parse_args()

    files = args.files or [
        path
        for path in Path(__file__).resolve().parent.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not files:
        print("No supported files found.")
        return

    for source in files:
        try:
            output = convert_file(source)
        except (FileNotFoundError, ValueError) as error:
            print(f"Skipped {source}: {error}")
            continue
        print(f"Saved Base64: {output}")


if __name__ == "__main__":
    main()
