import os
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFont, ImageFilter

PRESETS = {
    'Instagram Story / Reel (1080x1920)': (1080, 1920, 'fit_pad'),
    'Instagram Post Square (1080x1080)': (1080, 1080, 'fit_pad'),
    'YouTube Thumbnail (1280x720)': (1280, 720, 'fit_pad'),
    'Passport Photo (600x600)': (600, 600, 'fit_crop'),
    'Twitter / X Header (1500x500)': (1500, 500, 'fit_pad'),
    'LinkedIn Banner (1584x396)': (1584, 396, 'fit_pad'),
    'Pinterest Pin (1000x1500)': (1000, 1500, 'fit_pad'),
    'Facebook Cover (820x312)': (820, 312, 'fit_pad'),
    'Open Graph / Social Card (1200x630)': (1200, 630, 'fit_pad'),
    'Discord Banner (960x540)': (960, 540, 'fit_pad'),
    'TikTok Video Frame (1080x1920)': (1080, 1920, 'fit_pad'),
    'App Store Screenshot 6.5" (1284x2778)': (1284, 2778, 'fit_pad'),
    'Email Attachment (<10MB)': (1920, 1080, 'scale_down')
}

def remove_background(input_path: str, output_path: str):
    '''AI-powered background removal using rembg.'''
    try:
        from rembg import remove
        with Image.open(input_path) as img:
            result = remove(img)
            if not output_path.lower().endswith('.png'):
                output_path = os.path.splitext(output_path)[0] + '.png'
            result.save(output_path, format='PNG')
        return output_path
    except Exception as e:
        raise RuntimeError(f'Background removal error: {str(e)}')

def strip_exif(input_path: str, output_path: str):
    '''Strip all EXIF / metadata (GPS, camera serials, timestamps) for privacy.'''
    with Image.open(input_path) as img:
        clean_img = Image.new(img.mode, img.size)
        clean_img.paste(img)
        
        fmt = img.format if img.format else 'JPEG'
        if output_path.lower().endswith(('.jpg', '.jpeg')) and clean_img.mode in ('RGBA', 'P'):
            clean_img = clean_img.convert('RGB')
        clean_img.save(output_path, format=fmt, quality=95)
    return output_path

def generate_favicons(input_path: str, output_dir: str, base_name: str = 'favicon') -> list[str]:
    '''
    Generate standard multi-size .ico file (16x16, 32x32, 48x48, 64x64, 128x128, 256x256)
    and Apple touch icon (180x180 PNG).
    '''
    os.makedirs(output_dir, exist_ok=True)
    created = []
    with Image.open(input_path) as img:
        img = img.convert('RGBA')
        
        ico_path = os.path.join(output_dir, f'{base_name}.ico')
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(ico_path, format='ICO', sizes=sizes)
        created.append(ico_path)
        
        touch_path = os.path.join(output_dir, 'apple-touch-icon.png')
        touch_img = img.resize((180, 180), Image.Resampling.LANCZOS)
        touch_img.save(touch_path, format='PNG')
        created.append(touch_path)

        png_32 = os.path.join(output_dir, 'favicon-32x32.png')
        img.resize((32, 32), Image.Resampling.LANCZOS).save(png_32, format='PNG')
        created.append(png_32)

    return created

def add_canvas_padding(input_path, output_path: str = None,
                       pad_top: int = 0, pad_right: int = 0,
                       pad_bottom: int = 0, pad_left: int = 0,
                       fill_color: tuple = (255, 255, 255)):
    '''Expand image canvas with padding / uniform border.'''
    if isinstance(input_path, Image.Image):
        if isinstance(output_path, (int, float)):
            pad = int(output_path)
            pad_top = pad_right = pad_bottom = pad_left = pad
        return apply_canvas_padding(input_path, pad_top, pad_right, pad_bottom, pad_left, fill_color)
    with Image.open(input_path) as img:
        res = apply_canvas_padding(img, pad_top, pad_right, pad_bottom, pad_left, fill_color)
        out_ext = os.path.splitext(output_path)[1].lower()
        if out_ext in ('.jpg', '.jpeg') and res.mode == 'RGBA':
            res = res.convert('RGB')
        res.save(output_path)
    return output_path

def apply_canvas_padding(img: Image.Image, pad_top: int = 0, pad_right: int = 0,
                         pad_bottom: int = 0, pad_left: int = 0,
                         fill_color: tuple = (255, 255, 255)) -> Image.Image:
    '''Apply padding around PIL Image.'''
    if pad_top <= 0 and pad_right <= 0 and pad_bottom <= 0 and pad_left <= 0:
        return img
    new_w = img.width + pad_left + pad_right
    new_h = img.height + pad_top + pad_bottom
    mode = 'RGBA' if img.mode == 'RGBA' else 'RGB'
    bg_fill = (*fill_color[:3], 255) if mode == 'RGBA' and len(fill_color) == 3 else fill_color
    canvas = Image.new(mode, (new_w, new_h), bg_fill)
    canvas.paste(img, (pad_left, pad_top))
    return canvas

def round_corners(img: Image.Image, radius: int = 20) -> Image.Image:
    '''Apply rounded corners with alpha transparency.'''
    if radius <= 0:
        return img
    img = img.convert('RGBA')
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=radius, fill=255)
    img.putalpha(mask)
    return img

def add_drop_shadow(img: Image.Image, offset=(5, 5),
                    shadow_color=(0, 0, 0, 120), blur: int = 8, padding: int = 20) -> Image.Image:
    '''Add soft drop shadow around image.'''
    img = img.convert('RGBA')
    total_w = img.width + abs(offset[0]) + padding * 2
    total_h = img.height + abs(offset[1]) + padding * 2

    shadow = Image.new('RGBA', (total_w, total_h), (0, 0, 0, 0))
    shadow_mask = Image.new('RGBA', img.size, shadow_color)
    sx = padding + max(offset[0], 0)
    sy = padding + max(offset[1], 0)
    shadow.paste(shadow_mask, (sx, sy), img.getchannel('A'))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))

    result = Image.new('RGBA', (total_w, total_h), (0, 0, 0, 0))
    result.paste(shadow, (0, 0), shadow)
    result.paste(img, (padding + max(-offset[0], 0), padding + max(-offset[1], 0)), img)
    return result

def crop_image(input_path, output_path=None, box: tuple = None):
    '''Crop image using bounding box (x0, y0, x1, y1). Supports PIL Image or file paths.'''
    if isinstance(input_path, Image.Image):
        crop_box = output_path if box is None else box
        return input_path.crop(crop_box)
    with Image.open(input_path) as img:
        cropped = img.crop(box)
        cropped.save(output_path)
    return output_path

def estimate_output_size(img: Image.Image, fmt: str = 'JPEG', quality: int = 85) -> int:
    '''Estimate output file size in bytes for live readout.'''
    import io
    buf = io.BytesIO()
    save_img = img.copy()
    fmt_upper = fmt.upper()
    if fmt_upper in ('JPEG', 'JPG'):
        if save_img.mode in ('RGBA', 'P', 'LA'):
            save_img = save_img.convert('RGB')
        save_img.save(buf, format='JPEG', quality=quality, optimize=True)
    elif fmt_upper == 'WEBP':
        save_img.save(buf, format='WEBP', quality=quality)
    elif fmt_upper == 'PNG':
        save_img.save(buf, format='PNG', optimize=True)
    else:
        save_img.save(buf, format='PNG')
    return buf.tell()

def extract_color_palette(img: Image.Image, n_colors: int = 6) -> list[str]:
    '''Extract dominant color palette as list of hex strings [#RRGGBB, ...].'''
    try:
        small = img.copy().convert('RGB')
        small.thumbnail((150, 150))
        quantized = small.quantize(colors=n_colors)
        p = quantized.getpalette()
        colors = []
        for i in range(min(n_colors, len(p) // 3)):
            r, g, b = p[i*3], p[i*3+1], p[i*3+2]
            colors.append(f'#{r:02x}{g:02x}{b:02x}')
        return colors
    except Exception:
        return ['#202020', '#ffffff', '#e74c3c', '#3498db', '#2ecc71', '#f1c40f']

def apply_rename_pattern(original_path: str, pattern: str, index: int = 1, img_size: tuple = (0, 0)) -> str:
    '''Generate formatted filename using tokens: {name}, {index}, {width}, {height}, {date}.'''
    from datetime import datetime
    bname = os.path.splitext(os.path.basename(original_path))[0]
    ext = os.path.splitext(original_path)[1]
    w, h = img_size
    date_str = datetime.now().strftime('%Y%m%d')
    try:
        new_bname = pattern.format(name=bname, index=index, width=w, height=h, date=date_str)
    except Exception:
        new_bname = f'{bname}_{index:03d}'
    return f'{new_bname}{ext}'

def adjust_color_temperature(img: Image.Image, temperature: int) -> Image.Image:
    '''Adjust color temperature (-100 cool/blue to +100 warm/amber).'''
    if temperature == 0:
        return img
    import numpy as np
    orig_mode = img.mode
    has_alpha = orig_mode == 'RGBA'
    alpha = img.getchannel('A') if has_alpha else None

    rgb_img = img.convert('RGB')
    arr = np.array(rgb_img, dtype=np.float32)
    factor = temperature / 100.0

    arr[:, :, 0] = np.clip(arr[:, :, 0] * (1.0 + factor * 0.25), 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] * (1.0 - factor * 0.25), 0, 255)

    result = Image.fromarray(arr.astype(np.uint8))
    if has_alpha and alpha:
        result.putalpha(alpha)
    return result


def process_image(
    input_path: str,
    output_path: str,
    scale_percent: float = None,
    width: int = None,
    height: int = None,
    keep_aspect: bool = True,
    preset_name: str = None,
    crop_box: tuple = None,
    brightness: float = 1.0,
    contrast: float = 1.0,
    sharpness: float = 1.0,
    saturation: float = 1.0,
    color_temperature: int = 0,
    grayscale: bool = False,
    rotate_angle: int = 0,
    flip_h: bool = False,
    flip_v: bool = False,
    canvas_padding: tuple = None,
    round_corners_radius: int = None,
    drop_shadow: dict = None,
    strip_metadata: bool = False,
    quality: int = 95,
    watermark_text: str = None
) -> str:
    '''Comprehensive image editor and resizer pipeline.'''
    with Image.open(input_path) as orig_img:
        img = ImageOps.exif_transpose(orig_img) if not strip_metadata else orig_img.copy()

        # Handle Interactive Crop First
        if crop_box and len(crop_box) == 4:
            x0, y0, x1, y1 = crop_box
            if x1 > x0 and y1 > y0:
                img = img.crop((int(x0), int(y0), int(x1), int(y1)))

        # Handle Presets
        if preset_name and preset_name in PRESETS:
            target_w, target_h, mode = PRESETS[preset_name]
            if mode == 'scale_down':
                img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            elif mode == 'fit_pad':
                img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
                bg_mode = 'RGBA' if img.mode == 'RGBA' else 'RGB'
                bg_color = (0, 0, 0, 0) if bg_mode == 'RGBA' else (255, 255, 255)
                new_canvas = Image.new(bg_mode, (target_w, target_h), bg_color)
                paste_x = (target_w - img.width) // 2
                paste_y = (target_h - img.height) // 2
                new_canvas.paste(img, (paste_x, paste_y))
                img = new_canvas
            elif mode == 'fit_crop':
                img = ImageOps.fit(img, (target_w, target_h), Image.Resampling.LANCZOS)
        elif scale_percent and scale_percent != 100:
            factor = scale_percent / 100.0
            new_w = max(1, int(img.width * factor))
            new_h = max(1, int(img.height * factor))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        elif width or height:
            if width and height:
                if keep_aspect:
                    img.thumbnail((width, height), Image.Resampling.LANCZOS)
                else:
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
            elif width:
                factor = width / float(img.width)
                new_h = max(1, int(img.height * factor))
                img = img.resize((width, new_h), Image.Resampling.LANCZOS)
            elif height:
                factor = height / float(img.height)
                new_w = max(1, int(img.width * factor))
                img = img.resize((new_w, height), Image.Resampling.LANCZOS)

        # Filters & Tuning
        if grayscale or saturation == 0.0:
            img = ImageOps.grayscale(img)
        elif saturation != 1.0:
            if img.mode != 'RGB' and img.mode != 'RGBA':
                img = img.convert('RGB')
            img = ImageEnhance.Color(img).enhance(saturation)

        if brightness != 1.0:
            img = ImageEnhance.Brightness(img.convert('RGB') if img.mode not in ('RGB', 'RGBA') else img).enhance(brightness)
        if contrast != 1.0:
            img = ImageEnhance.Contrast(img.convert('RGB') if img.mode not in ('RGB', 'RGBA') else img).enhance(contrast)
        if sharpness != 1.0:
            img = ImageEnhance.Sharpness(img.convert('RGB') if img.mode not in ('RGB', 'RGBA') else img).enhance(sharpness)

        if color_temperature != 0:
            img = adjust_color_temperature(img, color_temperature)

        # Transformations
        if rotate_angle != 0:
            img = img.rotate(-rotate_angle, expand=True)
        if flip_h:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if flip_v:
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        # Canvas Padding / Border Expansion
        if canvas_padding:
            if isinstance(canvas_padding, (int, float)):
                pt = pr = pb = pl = int(canvas_padding)
                fc = (255, 255, 255)
            elif isinstance(canvas_padding, (tuple, list)):
                if len(canvas_padding) == 2:
                    pt = pr = pb = pl = int(canvas_padding[0])
                    fc = canvas_padding[1]
                elif len(canvas_padding) >= 4:
                    pt, pr, pb, pl = canvas_padding[:4]
                    fc = canvas_padding[4] if len(canvas_padding) > 4 else (255, 255, 255)
                else:
                    pt = pr = pb = pl = int(canvas_padding[0])
                    fc = (255, 255, 255)
            else:
                pt = pr = pb = pl = 20
                fc = (255, 255, 255)
            img = apply_canvas_padding(img, pt, pr, pb, pl, fc)

        # Rounded Corners
        if round_corners_radius and round_corners_radius > 0:
            img = round_corners(img, round_corners_radius)

        # Drop Shadow
        if drop_shadow:
            ds_dict = drop_shadow if isinstance(drop_shadow, dict) else {}
            offset = ds_dict.get('offset', (5, 5))
            scol = ds_dict.get('shadow_color', (0, 0, 0, 120))
            blur = ds_dict.get('blur', 8)
            pad = ds_dict.get('padding', 20)
            img = add_drop_shadow(img, offset=offset, shadow_color=scol, blur=blur, padding=pad)

        # Watermarking Text
        if watermark_text:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            font_size = max(16, int(img.width * 0.03))
            try:
                font = ImageFont.truetype('arial.ttf', font_size)
            except Exception:
                font = ImageFont.load_default()
            
            draw.text((20, img.height - font_size - 20), watermark_text, fill=(255, 255, 255, 160), font=font)
            img = Image.alpha_composite(img, txt_layer)

        # Save Output
        out_ext = os.path.splitext(output_path)[1].lower()
        if out_ext in ('.jpg', '.jpeg'):
            if img.mode in ('RGBA', 'P', 'LA'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    bg.paste(img, mask=img.getchannel('A'))
                else:
                    bg.paste(img.convert('RGB'))
                img = bg
            img.save(output_path, format='JPEG', quality=quality, optimize=True)
        elif out_ext == '.png':
            img.save(output_path, format='PNG', optimize=True)
        elif out_ext == '.webp':
            img.save(output_path, format='WEBP', quality=quality)
        elif out_ext == '.ico':
            img.save(output_path, format='ICO')
        elif out_ext in ('.bmp', '.tiff', '.tif'):
            if out_ext == '.bmp' and img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(output_path)
        else:
            img.save(output_path)

    return output_path

def smart_upscale_image(input_path: str, output_path: str, scale_factor: int = 2, sharpness: float = 1.4) -> str:
    '''
    Smart crisp upscaler combining progressive Lanczos resampling, edge-preserving
    unsharp masking, and adaptive local contrast enhancement for 2x/4x magnification.
    '''
    if scale_factor not in (2, 4):
        scale_factor = 2

    with Image.open(input_path) as orig:
        img = orig.copy()
        target_w = img.width * scale_factor
        target_h = img.height * scale_factor

        if scale_factor == 4:
            mid_w = img.width * 2
            mid_h = img.height * 2
            img = img.resize((mid_w, mid_h), Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2))

        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=2.0, percent=int(120 * sharpness), threshold=3))

        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.08)

        out_ext = os.path.splitext(output_path)[1].lower()
        if out_ext in ('.jpg', '.jpeg') and img.mode == 'RGBA':
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.getchannel('A'))
            img = bg

        img.save(output_path, quality=95, optimize=True)
    return output_path
