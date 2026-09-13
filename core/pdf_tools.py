import os
import pymupdf
from PIL import Image
import io

def merge_pdfs(pdf_paths: list[str], output_path: str):
    '''Merge multiple PDF files in order into a single output PDF.'''
    doc = pymupdf.open()
    try:
        for path in pdf_paths:
            with pymupdf.open(path) as sub_doc:
                doc.insert_pdf(sub_doc)
        doc.save(output_path, garbage=4, deflate=True)
    finally:
        doc.close()
    return output_path

def split_pdf(pdf_path: str, output_dir: str, page_ranges: str = None) -> list[str]:
    '''Split PDF into separate files.'''
    os.makedirs(output_dir, exist_ok=True)
    created_files = []
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    with pymupdf.open(pdf_path) as doc:
        total_pages = len(doc)
        if not page_ranges:
            for page_num in range(total_pages):
                out_doc = pymupdf.open()
                try:
                    out_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                    out_file = os.path.join(output_dir, f'{base_name}_page_{page_num + 1}.pdf')
                    out_doc.save(out_file, garbage=4, deflate=True)
                    created_files.append(out_file)
                finally:
                    out_doc.close()
        else:
            pages_to_extract = []
            parts = [p.strip() for p in page_ranges.split(',') if p.strip()]
            for part in parts:
                if '-' in part:
                    start_str, end_str = part.split('-', 1)
                    start = max(1, int(start_str.strip()))
                    end = min(total_pages, int(end_str.strip()))
                    pages_to_extract.extend(range(start - 1, end))
                else:
                    p_num = int(part)
                    if 1 <= p_num <= total_pages:
                        pages_to_extract.append(p_num - 1)
            
            pages_to_extract = sorted(list(set(pages_to_extract)))
            if pages_to_extract:
                out_doc = pymupdf.open()
                try:
                    for p in pages_to_extract:
                        out_doc.insert_pdf(doc, from_page=p, to_page=p)
                    out_file = os.path.join(output_dir, f'{base_name}_extracted.pdf')
                    out_doc.save(out_file, garbage=4, deflate=True)
                    created_files.append(out_file)
                finally:
                    out_doc.close()

    return created_files

def rotate_pdf(pdf_path: str, output_path: str, angle: int = 90, pages: list[int] = None):
    '''Rotate pages (90, 180, 270 degrees). If pages is None, rotates all pages.'''
    with pymupdf.open(pdf_path) as doc:
        total_pages = len(doc)
        target_pages = set(pages) if pages else set(range(total_pages))

        for i in range(total_pages):
            if i in target_pages:
                page = doc[i]
                page.set_rotation((page.rotation + angle) % 360)

        doc.save(output_path, garbage=4, deflate=True)
    return output_path

def pdf_to_images(pdf_path: str, output_dir: str, fmt: str = 'png', dpi: int = 150) -> list[str]:
    '''Convert all pages of a PDF into individual image files.'''
    os.makedirs(output_dir, exist_ok=True)
    created_files = []
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    with pymupdf.open(pdf_path) as doc:
        for idx, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            out_file = os.path.join(output_dir, f'{base_name}_page_{idx + 1}.{fmt.lower()}')
            pix.save(out_file)
            created_files.append(out_file)
    return created_files

def images_to_pdf(image_paths: list[str], output_path: str):
    '''Stitch an album or list of images into a single PDF.'''
    doc = pymupdf.open()
    try:
        for img_path in image_paths:
            with Image.open(img_path) as img:
                img_bytes = io.BytesIO()
                img_format = 'PNG' if img.mode == 'RGBA' else 'JPEG'
                img.save(img_bytes, format=img_format)
                img_bytes.seek(0)
                img_doc = pymupdf.open(stream=img_bytes.read(), filetype=img_format.lower())
                try:
                    rect = img_doc[0].rect
                    pdf_bytes = img_doc.convert_to_pdf()
                    img_pdf = pymupdf.open('pdf', pdf_bytes)
                    try:
                        page = doc.new_page(width=rect.width, height=rect.height)
                        page.show_pdf_page(rect, img_pdf, 0)
                    finally:
                        img_pdf.close()
                finally:
                    img_doc.close()
                
        doc.save(output_path, garbage=4, deflate=True)
    finally:
        doc.close()
    return output_path

def compress_pdf(pdf_path: str, output_path: str, max_image_dimension: int = 1200, jpeg_quality: int = 70):
    '''Compress a PDF by downscaling high-resolution embedded images and deflating streams.'''
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image['image']
                    pil_image = Image.open(io.BytesIO(image_bytes))

                    width, height = pil_image.size
                    if width > max_image_dimension or height > max_image_dimension:
                        pil_image.thumbnail((max_image_dimension, max_image_dimension), Image.Resampling.LANCZOS)
                        if pil_image.mode in ('RGBA', 'P'):
                            pil_image = pil_image.convert('RGB')
                        
                        buf = io.BytesIO()
                        pil_image.save(buf, format='JPEG', quality=jpeg_quality, optimize=True)
                        doc.update_stream(xref, buf.getvalue())
                except Exception:
                    continue

        doc.save(output_path, garbage=4, deflate=True, clean=True)
    return output_path

def add_text_to_pdf(pdf_path: str, output_path: str, text: str, page_number: int = 1,
                    x: float = 72, y: float = 72, font_size: int = 14, color: tuple = (0, 0, 0)):
    '''Add text annotation / stamp to a specific page of a PDF.'''
    with pymupdf.open(pdf_path) as doc:
        if 1 <= page_number <= len(doc):
            page = doc[page_number - 1]
            norm_color = tuple(c / 255.0 if c > 1.0 else c for c in color)
            page.insert_text(pymupdf.Point(x, y), text, fontsize=font_size, color=norm_color)
        doc.save(output_path, garbage=4, deflate=True)
    return output_path

def add_image_or_signature_to_pdf(pdf_path: str, output_path: str, image_path: str, page_number: int = 1,
                                 x: float = 72, y: float = 72, width: float = 150, height: float = 60):
    '''Insert an image, logo, or signature stamp onto a specific page of a PDF.'''
    with pymupdf.open(pdf_path) as doc:
        if 1 <= page_number <= len(doc):
            page = doc[page_number - 1]
            rect = pymupdf.Rect(x, y, x + width, y + height)
            page.insert_image(rect, filename=image_path)
        doc.save(output_path, garbage=4, deflate=True)
    return output_path

def apply_annotations_to_pdf(pdf_path: str, output_path: str, annotations_by_page: dict):
    '''
    Apply freehand drawings, texts, and signature images across pages.
    annotations_by_page format:
    {
      page_index (0-indexed): {
         'drawings': [ {'points': [(x1,y1), (x2,y2), ...], 'color': (r,g,b), 'width': 2}, ... ],
         'texts': [ {'text': '...', 'x': x, 'y': y, 'font_size': 14, 'color': (r,g,b)}, ... ],
         'signatures': [ {'image_path': '...', 'x': x, 'y': y, 'width': w, 'height': h}, ... ]
      }
    }
    '''
    with pymupdf.open(pdf_path) as doc:
        for page_idx, page_data in annotations_by_page.items():
            if 0 <= page_idx < len(doc):
                page = doc[page_idx]

                # 1. Apply freehand strokes
                for stroke in page_data.get('drawings', []):
                    pts = stroke.get('points', [])
                    if len(pts) > 1:
                        shape = page.new_shape()
                        raw_color = stroke.get('color', (0, 0, 0))
                        color = tuple(c / 255.0 if c > 1.0 else c for c in raw_color)
                        width = stroke.get('width', 2)
                        
                        shape.draw_polyline([pymupdf.Point(p[0], p[1]) for p in pts])
                        shape.finish(color=color, width=width)
                        shape.commit()

                # 2. Apply text annotations
                for t in page_data.get('texts', []):
                    raw_color = t.get('color', (0, 0, 0))
                    color = tuple(c / 255.0 if c > 1.0 else c for c in raw_color)
                    font_size = t.get('font_size', 14)
                    page.insert_text(
                        pymupdf.Point(t['x'], t['y']),
                        t['text'],
                        fontsize=font_size,
                        color=color
                    )

                # 3. Apply signatures/images
                for sig in page_data.get('signatures', []):
                    img_file = sig.get('image_path')
                    if img_file and os.path.exists(img_file):
                        rect = pymupdf.Rect(sig['x'], sig['y'], sig['x'] + sig['width'], sig['y'] + sig['height'])
                        page.insert_image(rect, filename=img_file)

        doc.save(output_path, garbage=4, deflate=True)
    return output_path

def add_watermark_text(pdf_path: str, output_path: str, watermark_text: str,
                       opacity: float = 0.3, font_size: int = 36, color: tuple = (0.5, 0.5, 0.5)):
    '''Add a centered watermark across all pages of a PDF.'''
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            rect = page.rect
            center_x = rect.width / 2.0
            center_y = rect.height / 2.0
            point = pymupdf.Point(max(20, center_x - (len(watermark_text) * font_size * 0.28)), center_y)
            page.insert_text(point, watermark_text, fontsize=font_size, color=color, rotate=0)
        doc.save(output_path, garbage=4, deflate=True)
    return output_path

def protect_pdf(pdf_path: str, output_path: str, password: str):
    '''Encrypt a PDF with AES-256 password protection.'''
    with pymupdf.open(pdf_path) as doc:
        doc.save(output_path, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password, garbage=4, deflate=True)
    return output_path

def unlock_pdf(pdf_path: str, output_path: str, password: str):
    '''Decrypt a password-protected PDF.'''
    with pymupdf.open(pdf_path) as doc:
        if doc.is_encrypted:
            if not doc.authenticate(password):
                raise ValueError('Incorrect password for PDF.')
        doc.save(output_path, encryption=pymupdf.PDF_ENCRYPT_KEEP, garbage=4, deflate=True)
    return output_path
