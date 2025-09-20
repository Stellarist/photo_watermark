import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ExifTags, ImageColor


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Add EXIF shooting date watermark to images.")
	parser.add_argument("input_path", help="Image file or directory path")
	parser.add_argument("--font-size", type=int, default=32, dest="font_size", help="Font size in pixels (default: 32)")
	parser.add_argument("--color", type=str, default="#FFFFFF", help="Text color (hex or name), default #FFFFFF")
	parser.add_argument("--position", type=str, default="bottom-right", choices=[
		"top-left", "top-right", "center", "bottom-left", "bottom-right"
	], help="Watermark position (default: bottom-right)")
	parser.add_argument("--opacity", type=int, default=220, help="Text opacity 0-255 (default: 220)")
	parser.add_argument("--font-path", type=str, default=None, help="Optional path to a .ttf font file")
	return parser.parse_args()


def find_output_dir(input_path: Path) -> Path:
	if input_path.is_file():
		base_dir = input_path.parent
	else:
		base_dir = input_path
	return base_dir / f"{base_dir.name}_watermark"


def format_date(date: datetime) -> str:
	return date.strftime("%Y-%m-%d")


def get_exif_datetime(image: Image.Image) -> Optional[datetime]:
	try:
		exif = image.getexif()
		if not exif:
			return None
		# Build tag name map
		tag_map = {ExifTags.TAGS.get(tag, tag): value for tag, value in exif.items()}
		# Common datetime tags in EXIF
		for key in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
			value = tag_map.get(key)
			if not value:
				continue
			# Expected format: "YYYY:MM:DD HH:MM:SS"
			if isinstance(value, bytes):
				try:
					value = value.decode("utf-8", errors="ignore")
				except Exception:
					continue
			value = str(value)
			for fmt in ["%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d", "%Y-%m-%d"]:
				try:
					return datetime.strptime(value, fmt)
				except ValueError:
					continue
		return None
	except Exception:
		return None


def get_file_mtime(path: Path) -> datetime:
	return datetime.fromtimestamp(path.stat().st_mtime)


def compute_text_position(img_size: Tuple[int, int], text_size: Tuple[int, int], position: str, margin: int = 16) -> Tuple[int, int]:
	img_w, img_h = img_size
	text_w, text_h = text_size
	if position == "top-left":
		return margin, margin
	if position == "top-right":
		return img_w - text_w - margin, margin
	if position == "center":
		return (img_w - text_w) // 2, (img_h - text_h) // 2
	if position == "bottom-left":
		return margin, img_h - text_h - margin
	# bottom-right
	return img_w - text_w - margin, img_h - text_h - margin


def load_font(font_path: Optional[str], font_size: int) -> ImageFont.ImageFont:
	if font_path:
		try:
			return ImageFont.truetype(font_path, font_size)
		except Exception:
			pass
	return ImageFont.load_default()


def draw_watermark(image: Image.Image, text: str, color: str, opacity: int, position: str, font: ImageFont.ImageFont) -> Image.Image:
	if image.mode != "RGBA":
		image = image.convert("RGBA")
	text_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
	draw = ImageDraw.Draw(text_layer)
	# Measure text
	bbox = draw.textbbox((0, 0), text, font=font)
	text_w = bbox[2] - bbox[0]
	text_h = bbox[3] - bbox[1]
	x, y = compute_text_position(image.size, (text_w, text_h), position)
	# Parse color
	try:
		fill_color = ImageColor.getrgb(color)
	except Exception:
		fill_color = (255, 255, 255)
	fill = (*fill_color, max(0, min(255, opacity)))
	# Optional soft shadow for readability
	shadow_offset = 2
	draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, min(255, opacity)))
	draw.text((x, y), text, font=font, fill=fill)
	return Image.alpha_composite(image, text_layer)


def process_image_file(input_file: Path, output_dir: Path, args: argparse.Namespace) -> Optional[Path]:
	try:
		with Image.open(input_file) as im:
			date_dt = get_exif_datetime(im)
			if date_dt is None:
				date_dt = get_file_mtime(input_file)
			text = format_date(date_dt)
			font = load_font(args.font_path, args.font_size)
			out_rgba = draw_watermark(im, text, args.color, args.opacity, args.position, font)
			# Save preserving original format when possible
			output_dir.mkdir(parents=True, exist_ok=True)
			ext = input_file.suffix.lower()
			out_name = input_file.stem + "_wm" + (".png" if ext == ".png" else ".jpg")
			# Convert to RGB if not supporting alpha in chosen format
			if out_name.lower().endswith(".jpg") or out_name.lower().endswith(".jpeg"):
				out_img = out_rgba.convert("RGB")
				out_img.save(output_dir / out_name, quality=92)
			else:
				out_rgba.save(output_dir / out_name)
			return output_dir / out_name
	except Exception as e:
		print(f"Failed to process {input_file}: {e}", file=sys.stderr)
		return None


def is_image_file(path: Path) -> bool:
	return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


def main() -> None:
	args = parse_args()
	input_path = Path(args.input_path)
	if not input_path.exists():
		print(f"Input path not found: {input_path}", file=sys.stderr)
		sys.exit(1)

	output_dir = find_output_dir(input_path)
	processed = 0
	if input_path.is_file():
		if is_image_file(input_path):
			if process_image_file(input_path, output_dir, args):
				processed += 1
		else:
			print(f"Not an image file: {input_path}", file=sys.stderr)
	else:
		for root, _, files in os.walk(input_path):
			root_path = Path(root)
			# Preserve relative structure below input_path
			rel = root_path.relative_to(input_path)
			for name in files:
				p = root_path / name
				if is_image_file(p):
					out_dir = output_dir / rel
					if process_image_file(p, out_dir, args):
						processed += 1

	print(f"Done. Processed {processed} image(s). Output: {output_dir}")


if __name__ == "__main__":
	main()
