# photo_watermark

A small Python CLI tool to add a shooting-date text watermark (from EXIF) to photos. Supports custom font size, color, and position. Saves results into a new sibling subdirectory named `<dirname>_watermark`.

## Install

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

```powershell
# Basic: process a file or directory
python watermark.py "C:\path\to\image.jpg"
python watermark.py "C:\path\to\folder"

# Options
python watermark.py "C:\path\to\folder" \
  --font-size 36 \
  --color "#FFFFFF" \
  --position bottom-right \
  --opacity 200
```

- `--font-size`: integer pixels. Default 32
- `--color`: HEX or named color, e.g., `#FFFFFF`, `white`
- `--position`: one of `top-left`, `top-right`, `center`, `bottom-left`, `bottom-right` (default `bottom-right`)
- `--opacity`: 0-255 alpha for the text layer (default 220)

By default, the tool extracts `DateTimeOriginal` (or similar EXIF date) and formats it as `YYYY-MM-DD`. If no EXIF date is found, falls back to file modification time.

Outputs go to `<dirname>_watermark` inside the input directory.

## Notes
- Fonts: Uses PIL's default font if no TTF provided. You may add `--font-path` to specify a TTF file.
- Supported images: common formats supported by Pillow (JPEG, PNG, etc.).
