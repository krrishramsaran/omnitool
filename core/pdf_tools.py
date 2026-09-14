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

def add_highlight(pdf_path: str, output_path: str, page_number: int = 1,
                  rect: tuple = (72, 72, 200, 100), color: tuple = (1.0, 1.0, 0.0)):
    '''Add a highlight annotation over a rectangle on a specific PDF page.'''
    with pymupdf.open(pdf_path) as doc:
        if 1 <= page_number <= len(doc):
            page = doc[page_number - 1]
            norm_color = tuple(c / 255.0 if c > 1.0 else c for c in color)
            annot = page.add_highlight_annot(pymupdf.Rect(rect))
            annot.set_colors(stroke=norm_color)
            annot.update()
        doc.save(output_path, garbage=4, deflate=True)
    return output_path

def add_underline(pdf_path: str, output_path: str, page_number: int = 1,
                  rect: tuple = (72, 72, 200, 100), color: tuple = (0.0, 0.0, 1.0)):
    '''Add an underline annotation over a rectangle on a specific PDF page.'''
    with pymupdf.open(pdf_path) as doc:
        if 1 <= page_number <= len(doc):
            page = doc[page_number - 1]
            norm_color = tuple(c / 255.0 if c > 1.0 else c for c in color)
            annot = page.add_underline_annot(pymupdf.Rect(rect))
            annot.set_colors(stroke=norm_color)
            annot.update()
        doc.save(output_path, garbage=4, deflate=True)
    return output_path

def add_strikeout(pdf_path: str, output_path: str, page_number: int = 1,
                  rect: tuple = (72, 72, 200, 100), color: tuple = (1.0, 0.0, 0.0)):
    '''Add a strikethrough annotation over a rectangle on a specific PDF page.'''
    with pymupdf.open(pdf_path) as doc:
        if 1 <= page_number <= len(doc):
            page = doc[page_number - 1]
            norm_color = tuple(c / 255.0 if c > 1.0 else c for c in color)
            annot = page.add_strikeout_annot(pymupdf.Rect(rect))
            annot.set_colors(stroke=norm_color)
            annot.update()
        doc.save(output_path, garbage=4, deflate=True)
    return output_path

def redact_regions(pdf_path: str, output_path: str, redactions: list[dict]):
    '''
    Permanently redact (black out and scrub) regions from a PDF.
    redactions: [{'page': 0, 'rect': [x0, y0, x1, y1], 'fill': (0, 0, 0)}, ...]
    '''
    with pymupdf.open(pdf_path) as doc:
        for r in redactions:
            p_idx = r.get('page', 0)
            if 0 <= p_idx < len(doc):
                page = doc[p_idx]
                raw_fill = r.get('fill', (0, 0, 0))
                fill_color = tuple(c / 255.0 if c > 1.0 else c for c in raw_fill)
                page.add_redact_annot(pymupdf.Rect(r['rect']), fill=fill_color)
        
        for page in doc:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)
        
        doc.save(output_path, garbage=4, deflate=True, clean=True)
    return output_path

def search_and_redact(pdf_path: str, output_path: str, search_terms: list[str], fill_color: tuple = (0, 0, 0)):
    '''Search for specific text terms across all pages and permanently redact them.'''
    norm_fill = tuple(c / 255.0 if c > 1.0 else c for c in fill_color)
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            for term in search_terms:
                if not term.strip():
                    continue
                rects = page.search_for(term.strip())
                for rect in rects:
                    page.add_redact_annot(rect, fill=norm_fill)
        for page in doc:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)
        doc.save(output_path, garbage=4, deflate=True, clean=True)
    return output_path

def extract_page_text(pdf_path: str, page_number: int = 1) -> str:
    '''Extract plain text from a specific page (1-indexed).'''
    with pymupdf.open(pdf_path) as doc:
        if 1 <= page_number <= len(doc):
            return doc[page_number - 1].get_text('text')
    return ''

def extract_document_text(pdf_path: str, output_txt_path: str = None) -> str:
    '''Extract plain text from all pages. If output_txt_path is provided, saves to .txt file; otherwise returns text.'''
    with pymupdf.open(pdf_path) as doc:
        lines = []
        for i, page in enumerate(doc):
            lines.append(f'--- [ Page {i + 1} ] ---')
            lines.append(page.get_text('text'))
            lines.append('\n')
        full_text = '\n'.join(lines)
    if output_txt_path:
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        return output_txt_path
    return full_text

def list_form_fields(pdf_path: str) -> list[dict]:
    '''Inspect and list all interactive form fields (AcroForms) in a PDF.'''
    fields = []
    with pymupdf.open(pdf_path) as doc:
        for p_idx, page in enumerate(doc):
            for widget in page.widgets():
                fields.append({
                    'page': p_idx,
                    'name': widget.field_name or f'field_p{p_idx+1}_{len(fields)}',
                    'type': widget.field_type_string,
                    'rect': [widget.rect.x0, widget.rect.y0, widget.rect.x1, widget.rect.y1],
                    'value': widget.field_value or ''
                })
    return fields

def fill_form_fields(pdf_path: str, output_path: str, field_values: dict) -> str:
    '''Fill interactive form fields and save output.'''
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            for widget in page.widgets():
                name = widget.field_name
                if name and name in field_values:
                    val = field_values[name]
                    if widget.field_type_string == 'CheckBox':
                        widget.field_value = 'Yes' if (val is True or str(val).lower() in ('1', 'true', 'yes', 'on')) else 'Off'
                    else:
                        widget.field_value = str(val)
                    widget.update()
        doc.save(output_path, garbage=4, deflate=True)
    return output_path

def apply_annotations_to_pdf(pdf_path: str, output_path: str, annotations_by_page: dict):
    '''
    Apply freehand drawings, texts, signature images, highlights, underlines, strikeouts, and redactions.
    '''
    has_redactions = False
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

                # 4. Apply highlights
                for hl in page_data.get('highlights', []):
                    raw_color = hl.get('color', (255, 255, 0))
                    color = tuple(c / 255.0 if c > 1.0 else c for c in raw_color)
                    annot = page.add_highlight_annot(pymupdf.Rect(hl['rect']))
                    annot.set_colors(stroke=color)
                    annot.update()

                # 5. Apply underlines
                for ul in page_data.get('underlines', []):
                    raw_color = ul.get('color', (0, 0, 255))
                    color = tuple(c / 255.0 if c > 1.0 else c for c in raw_color)
                    annot = page.add_underline_annot(pymupdf.Rect(ul['rect']))
                    annot.set_colors(stroke=color)
                    annot.update()

                # 6. Apply strikeouts
                for so in page_data.get('strikeouts', []):
                    raw_color = so.get('color', (255, 0, 0))
                    color = tuple(c / 255.0 if c > 1.0 else c for c in raw_color)
                    annot = page.add_strikeout_annot(pymupdf.Rect(so['rect']))
                    annot.set_colors(stroke=color)
                    annot.update()

                # 7. Apply redactions
                for rd in page_data.get('redactions', []):
                    raw_fill = rd.get('fill', (0, 0, 0))
                    fill_color = tuple(c / 255.0 if c > 1.0 else c for c in raw_fill)
                    page.add_redact_annot(pymupdf.Rect(rd['rect']), fill=fill_color)
                    has_redactions = True

        if has_redactions:
            for page in doc:
                page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)
            doc.save(output_path, garbage=4, deflate=True, clean=True)
        else:
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

def reorder_pdf_pages(pdf_path: str, output_path: str, new_order: list[int]) -> str:
    '''Reorder PDF pages according to new_order list of 0-indexed page numbers.'''
    with pymupdf.open(pdf_path) as doc:
        valid_order = [i for i in new_order if 0 <= i < len(doc)]
        if not valid_order:
            raise ValueError('Invalid page order specification.')
        doc.select(valid_order)
        doc.save(output_path, garbage=4, deflate=True)
    return output_path

def delete_pdf_pages(pdf_path: str, output_path: str, pages_to_delete: list[int]) -> str:
    '''Delete specified 0-indexed pages from PDF.'''
    with pymupdf.open(pdf_path) as doc:
        keep_pages = [i for i in range(len(doc)) if i not in pages_to_delete]
        if not keep_pages:
            raise ValueError('Cannot delete all pages from a document.')
        doc.select(keep_pages)
        doc.save(output_path, garbage=4, deflate=True)
    return output_path

def get_pdf_thumbnails(pdf_path: str, max_pages: int = 100, dpi: int = 30) -> list:
    '''Generate small low-DPI thumbnail PIL images for each page.'''
    thumbs = []
    with pymupdf.open(pdf_path) as doc:
        limit = min(len(doc), max_pages)
        for i in range(limit):
            pix = doc[i].get_pixmap(dpi=dpi)
            img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            thumbs.append(img)
    return thumbs

def is_ocr_available() -> bool:
    '''Check if Tesseract OCR engine is available on the system.'''
    import shutil
    if shutil.which('tesseract'):
        return True
    common_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        os.path.expanduser(r'~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'),
    ]
    for p in common_paths:
        if os.path.exists(p):
            return True
    if os.environ.get('TESSDATA_PREFIX'):
        return True
    return False

def ocr_pdf(pdf_path: str, output_path: str, language: str = 'eng') -> str:
    '''
    Perform OCR on scanned PDF pages and produce a searchable PDF.
    If Tesseract is not installed, raises RuntimeError with installation instructions.
    '''
    if not is_ocr_available():
        raise RuntimeError(
            'Tesseract OCR engine is not installed or not found in system PATH.\n'
            'Install via PowerShell: winget install UB-Mannheim.TesseractOCR\n'
            'or download from https://github.com/UB-Mannheim/tesseract/wiki'
        )
    with pymupdf.open(pdf_path) as doc:
        ocr_doc = pymupdf.open()
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            pdf_bytes = pix.pdfocr_tobytes(language=language)
            page_doc = pymupdf.open('pdf', pdf_bytes)
            ocr_doc.insert_pdf(page_doc)
        ocr_doc.save(output_path, garbage=4, deflate=True)
    return output_path

