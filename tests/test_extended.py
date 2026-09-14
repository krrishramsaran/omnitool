import os
import sys
import unittest
import tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pymupdf
from PIL import Image

from core.pdf_tools import (
    images_to_pdf, split_pdf, compress_pdf, add_text_to_pdf,
    add_highlight, add_underline, add_strikeout, redact_regions,
    search_and_redact, extract_page_text, extract_document_text,
    list_form_fields, fill_form_fields, apply_annotations_to_pdf,
    reorder_pdf_pages, delete_pdf_pages, get_pdf_thumbnails, is_ocr_available
)
from core.image_tools import (
    remove_background, process_image, add_canvas_padding, round_corners,
    add_drop_shadow, crop_image, estimate_output_size, extract_color_palette,
    apply_rename_pattern, adjust_color_temperature, smart_upscale_image
)
from core.video_tools import (
    compress_video_target_size, add_fade, crossfade_videos,
    burn_subtitles, extract_audio_waveform, apply_color_grade,
    render_clip_sequence, COLOR_GRADE_PRESETS
)
from core.ffmpeg_utils import run_ffmpeg, detect_hw_encoder, get_ffmpeg_path

class TestExtendedCapabilities(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pdf_split_and_text(self):
        # Create 3 page PDF
        p1 = os.path.join(self.work_dir, 'p1.png')
        p2 = os.path.join(self.work_dir, 'p2.png')
        p3 = os.path.join(self.work_dir, 'p3.png')
        Image.new('RGB', (100, 100), (255, 0, 0)).save(p1)
        Image.new('RGB', (100, 100), (0, 255, 0)).save(p2)
        Image.new('RGB', (100, 100), (0, 0, 255)).save(p3)

        pdf_path = os.path.join(self.work_dir, 'doc3.pdf')
        images_to_pdf([p1, p2, p3], pdf_path)

        # Split with range
        split_out = os.path.join(self.work_dir, 'splits')
        extracted = split_pdf(pdf_path, split_out, page_ranges='1-2')
        self.assertEqual(len(extracted), 1)

        # Add text
        txt_pdf = os.path.join(self.work_dir, 'txt.pdf')
        add_text_to_pdf(pdf_path, txt_pdf, 'Hello PDF', page_number=1)
        self.assertTrue(os.path.exists(txt_pdf))

        # Compress PDF
        cmp_pdf = os.path.join(self.work_dir, 'cmp.pdf')
        compress_pdf(pdf_path, cmp_pdf)
        self.assertTrue(os.path.exists(cmp_pdf))

    def test_rembg(self):
        # Test background removal on a simple image
        img_path = os.path.join(self.work_dir, 'person.png')
        im = Image.new('RGB', (64, 64), color=(255, 255, 255))
        for x in range(20, 44):
            for y in range(20, 44):
                im.putpixel((x, y), (255, 0, 0))
        im.save(img_path)

        out_bg = os.path.join(self.work_dir, 'nobg.png')
        remove_background(img_path, out_bg)
        self.assertTrue(os.path.exists(out_bg))

    def test_pdf_phase1_2_annotations_and_forms(self):
        # 1. Create a PDF with searchable text
        doc = pymupdf.open()
        p1 = doc.new_page(width=400, height=500)
        p1.insert_text(pymupdf.Point(50, 100), "Confidential Secret Document", fontsize=14)
        p2 = doc.new_page(width=400, height=500)
        p2.insert_text(pymupdf.Point(50, 100), "Second Page Content Here", fontsize=14)
        
        pdf_path = os.path.join(self.work_dir, 'annot_source.pdf')
        doc.save(pdf_path)
        doc.close()

        # Test Text Extraction
        t1 = extract_page_text(pdf_path, page_number=1)
        self.assertIn("Confidential", t1)
        full_text = extract_document_text(pdf_path)
        self.assertIn("Second Page Content", full_text)

        # Test Highlights, Underlines, Strikeouts
        hl_out = os.path.join(self.work_dir, 'hl.pdf')
        add_highlight(pdf_path, hl_out, page_number=1, rect=(40, 80, 250, 120))
        self.assertTrue(os.path.exists(hl_out))

        ul_out = os.path.join(self.work_dir, 'ul.pdf')
        add_underline(pdf_path, ul_out, page_number=1, rect=(40, 80, 250, 120))
        self.assertTrue(os.path.exists(ul_out))

        so_out = os.path.join(self.work_dir, 'so.pdf')
        add_strikeout(pdf_path, so_out, page_number=1, rect=(40, 80, 250, 120))
        self.assertTrue(os.path.exists(so_out))

        # Test Search and Redact
        red_out = os.path.join(self.work_dir, 'redacted.pdf')
        search_and_redact(pdf_path, red_out, search_terms=['Confidential'])
        self.assertTrue(os.path.exists(red_out))
        t_redacted = extract_page_text(red_out, page_number=1)
        self.assertNotIn("Confidential", t_redacted)

        # Test Redact Regions
        reg_out = os.path.join(self.work_dir, 'redact_reg.pdf')
        redact_regions(pdf_path, reg_out, [{'page': 0, 'rect': [0, 0, 200, 200]}])
        self.assertTrue(os.path.exists(reg_out))

        # Test Interactive Form Fields
        form_doc = pymupdf.open()
        fp = form_doc.new_page(width=400, height=300)
        widget = pymupdf.Widget()
        widget.rect = pymupdf.Rect(50, 50, 200, 80)
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        widget.field_name = 'company_name'
        widget.field_value = 'Acme Inc'
        fp.add_widget(widget)
        form_pdf = os.path.join(self.work_dir, 'form.pdf')
        form_doc.save(form_pdf)
        form_doc.close()

        fields = list_form_fields(form_pdf)
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0]['name'], 'company_name')
        self.assertEqual(fields[0]['value'], 'Acme Inc')

        filled_pdf = os.path.join(self.work_dir, 'filled_form.pdf')
        fill_form_fields(form_pdf, filled_pdf, {'company_name': 'OmniTool Global'})
        self.assertTrue(os.path.exists(filled_pdf))
        updated_fields = list_form_fields(filled_pdf)
        self.assertEqual(updated_fields[0]['value'], 'OmniTool Global')

        # Test apply_annotations_to_pdf comprehensive
        multi_annot_out = os.path.join(self.work_dir, 'multi_annot.pdf')
        apply_annotations_to_pdf(pdf_path, multi_annot_out, {
            0: {
                'drawings': [{'points': [(50, 50), (100, 100), (150, 80)], 'color': (0, 0, 255), 'width': 3}],
                'texts': [{'x': 60, 'y': 200, 'text': 'Approved by QA', 'color': (0, 128, 0), 'font_size': 16}],
                'highlights': [{'rect': (50, 90, 200, 110), 'color': (255, 255, 0)}],
                'underlines': [{'rect': (50, 115, 200, 125), 'color': (0, 0, 255)}],
                'strikeouts': [{'rect': (50, 130, 200, 140), 'color': (255, 0, 0)}],
                'redactions': [{'rect': (50, 150, 200, 180), 'fill': (0, 0, 0)}]
            }
        })
        self.assertTrue(os.path.exists(multi_annot_out))

    def test_image_phase1_2_features(self):
        im = Image.new('RGB', (200, 150), color=(100, 150, 200))
        img_path = os.path.join(self.work_dir, 'test_img.png')
        im.save(img_path)

        # 1. Canvas Padding
        padded = add_canvas_padding(im, 20, fill_color=(255, 0, 0))
        self.assertEqual(padded.size, (240, 190))

        # 2. Rounded corners
        rounded = round_corners(im, 15)
        self.assertEqual(rounded.mode, 'RGBA')

        # 3. Soft drop shadow
        shadowed = add_drop_shadow(im)
        self.assertTrue(shadowed.width > im.width and shadowed.height > im.height)

        # 4. Crop image
        cropped = crop_image(im, (20, 20, 120, 100))
        self.assertEqual(cropped.size, (100, 80))

        # 5. Squoosh size estimation
        est_size = estimate_output_size(im, 'JPEG', quality=80)
        self.assertGreater(est_size, 0)

        # 6. Color palette extraction
        palette = extract_color_palette(im, n_colors=4)
        self.assertTrue(len(palette) <= 4)
        self.assertTrue(palette[0].startswith('#'))

        # 7. Rename pattern
        renamed = apply_rename_pattern('photo.jpg', '{name}_v{index}_{width}x{height}', index=5, img_size=(1920, 1080))
        self.assertEqual(renamed, 'photo_v5_1920x1080.jpg')

        # 8. Color temperature adjustment
        warmer = adjust_color_temperature(im, 50)
        cooler = adjust_color_temperature(im, -50)
        self.assertEqual(warmer.size, im.size)
        self.assertEqual(cooler.size, im.size)

        # 9. Full process_image pipeline with all Phase 1 & 2 features combined
        out_proc = os.path.join(self.work_dir, 'processed_combo.png')
        process_image(
            input_path=img_path,
            output_path=out_proc,
            crop_box=(10, 10, 150, 120),
            color_temperature=25,
            canvas_padding=(15, (50, 50, 50)),
            round_corners_radius=8,
            drop_shadow=True,
            quality=85
        )
        self.assertTrue(os.path.exists(out_proc))
        with Image.open(out_proc) as res:
            self.assertEqual(res.mode, 'RGBA')

    def test_video_phase1_2_features(self):
        # 1. Hardware encoder probe
        hw = detect_hw_encoder()
        self.assertIsInstance(hw, dict)
        self.assertIn(hw['best'], ['h264_nvenc', 'h264_qsv', 'h264_amf', 'libx264', None])
        self.assertIsInstance(hw['available'], list)
        self.assertIsInstance(hw['has_hw'], bool)

        # 2. Synthetic 2-second test video
        v_in = os.path.join(self.work_dir, 'synth_short.mp4')
        run_ffmpeg([
            '-y',
            '-f', 'lavfi', '-i', 'testsrc=duration=2:size=160x120:rate=10',
            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2',
            '-c:v', 'libx264', '-c:a', 'aac',
            v_in
        ])
        self.assertTrue(os.path.exists(v_in))

        # 3. Audio Waveform Extraction
        wf = extract_audio_waveform(v_in, num_points=40)
        self.assertEqual(len(wf), 40)
        for point in wf:
            self.assertTrue(0.0 <= point <= 1.0)

        # 4. Fade In / Out
        fade_out = os.path.join(self.work_dir, 'faded.mp4')
        add_fade(v_in, fade_out, fade_in_sec=0.5, fade_out_sec=0.5)
        self.assertTrue(os.path.exists(fade_out) and os.path.getsize(fade_out) > 0)

        # 5. Crossfade Merging
        cf_out = os.path.join(self.work_dir, 'crossfaded.mp4')
        crossfade_videos([v_in, v_in], cf_out, transition_duration=0.5)
        self.assertTrue(os.path.exists(cf_out) and os.path.getsize(cf_out) > 0)

        # 6. Subtitle Burning
        srt_path = os.path.join(self.work_dir, 'test.srt')
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write("1\n00:00:00,000 --> 00:00:01,500\nHello OmniTool Test Subtitle\n\n")

        sub_out = os.path.join(self.work_dir, 'subbed.mp4')
        burn_subtitles(v_in, srt_path, sub_out)
        self.assertTrue(os.path.exists(sub_out) and os.path.getsize(sub_out) > 0)

    def test_phase3_features(self):
        # 1. PDF Page Reordering & Page Deletion
        doc = pymupdf.open()
        for i in range(1, 4):
            page = doc.new_page(width=300, height=400)
            page.insert_text(pymupdf.Point(50, 100), f"Page {i} Content", fontsize=16)
        source_pdf = os.path.join(self.work_dir, 'source_p3.pdf')
        doc.save(source_pdf)
        doc.close()

        # Reorder pages: [2, 0, 1] -> Page 3, Page 1, Page 2
        reordered_pdf = os.path.join(self.work_dir, 'reordered.pdf')
        reorder_pdf_pages(source_pdf, reordered_pdf, [2, 0, 1])
        self.assertTrue(os.path.exists(reordered_pdf))
        r_doc = pymupdf.open(reordered_pdf)
        self.assertEqual(len(r_doc), 3)
        self.assertIn("Page 3", r_doc[0].get_text())
        self.assertIn("Page 1", r_doc[1].get_text())
        self.assertIn("Page 2", r_doc[2].get_text())
        r_doc.close()

        # Delete page index 1 (the middle page)
        deleted_pdf = os.path.join(self.work_dir, 'deleted.pdf')
        delete_pdf_pages(source_pdf, deleted_pdf, [1])
        self.assertTrue(os.path.exists(deleted_pdf))
        d_doc = pymupdf.open(deleted_pdf)
        self.assertEqual(len(d_doc), 2)
        self.assertIn("Page 1", d_doc[0].get_text())
        self.assertIn("Page 3", d_doc[1].get_text())
        d_doc.close()

        # Thumbnails extraction
        thumbs = get_pdf_thumbnails(source_pdf, dpi=20)
        self.assertEqual(len(thumbs), 3)
        for t in thumbs:
            self.assertIsInstance(t, Image.Image)

        # OCR check returns bool
        ocr_avail = is_ocr_available()
        self.assertIsInstance(ocr_avail, bool)

        # 2. Video Color Grading & Timeline Sequence Builder
        v_in = os.path.join(self.work_dir, 'synth_p3.mp4')
        run_ffmpeg([
            '-y',
            '-f', 'lavfi', '-i', 'testsrc=duration=2:size=160x120:rate=10',
            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2',
            '-c:v', 'libx264', '-c:a', 'aac',
            v_in
        ])
        self.assertTrue(os.path.exists(v_in))

        # Test Color Grading with Cinematic Teal & Orange
        graded_out = os.path.join(self.work_dir, 'graded.mp4')
        apply_color_grade(v_in, graded_out, 'Cinematic Teal & Orange')
        self.assertTrue(os.path.exists(graded_out) and os.path.getsize(graded_out) > 0)

        # Test Sequence Builder (stitching multiple trimmed clips)
        seq_clips = [
            {'path': v_in, 'start': 0.0, 'end': 0.8},
            {'path': v_in, 'start': 0.5, 'end': 1.5}
        ]
        seq_out = os.path.join(self.work_dir, 'sequence_stitched.mp4')
        render_clip_sequence(seq_clips, seq_out)
        self.assertTrue(os.path.exists(seq_out) and os.path.getsize(seq_out) > 0)

        # 3. Image Smart Super-Resolution Upscaling (2x)
        small_img_path = os.path.join(self.work_dir, 'small_orig.png')
        small_img = Image.new('RGB', (60, 40), color=(120, 200, 80))
        small_img.save(small_img_path)

        upscaled_path = os.path.join(self.work_dir, 'upscaled_2x.png')
        smart_upscale_image(small_img_path, upscaled_path, scale_factor=2)
        self.assertTrue(os.path.exists(upscaled_path))
        with Image.open(upscaled_path) as up_img:
            self.assertEqual(up_img.size, (120, 80))

if __name__ == '__main__':
    unittest.main()

