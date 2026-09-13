import os
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFont

PRESETS = {
    'Instagram Story / Reel (1080x1920)': (1080, 1920, 'fit_pad'),
    'Instagram Post Square (1080x1080)': (1080, 1080, 'fit_pad'),
    'YouTube Thumbnail (1280x720)': (1280, 720, 'fit_pad'),
    'Passport Photo (600x600)': (600, 600, 'fit_crop'),
    'Twitter / X Header (1500x500)': (1500, 500, 'fit_pad'),
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

def process_image(
    input_path: str,
    output_path: str,
    scale_percent: float = None,
    width: int = None,
    height: int = None,
    keep_aspect: bool = True,
    preset_name: str = None,
    brightness: float = 1.0,
    contrast: float = 1.0,
    sharpness: float = 1.0,
    saturation: float = 1.0,
    grayscale: bool = False,
    rotate_angle: int = 0,
    flip_h: bool = False,
    flip_v: bool = False,
    strip_metadata: bool = False,
    quality: int = 95,
    watermark_text: str = None
) -> str:
    '''Comprehensive image editor and resizer pipeline.'''
    with Image.open(input_path) as orig_img:
        img = ImageOps.exif_transpose(orig_img) if not strip_metadata else orig_img.copy()

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
            img = ImageEnhance.Brightness(img).enhance(brightness)
        if contrast != 1.0:
            img = ImageEnhance.Contrast(img).enhance(contrast)
        if sharpness != 1.0:
            img = ImageEnhance.Sharpness(img).enhance(sharpness)

        # Transformations
        if rotate_angle != 0:
            img = img.rotate(-rotate_angle, expand=True)
        if flip_h:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if flip_v:
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

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
                img = img.convert('RGB')
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
