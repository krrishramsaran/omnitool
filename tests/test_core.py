import os
import sys
import unittest
import tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pymupdf
from PIL import Image

from core.ffmpeg_utils import get_ffmpeg_path, run_ffmpeg
from core.pdf_tools import (
    images_to_pdf, pdf_to_images, merge_pdfs, split_pdf,
    rotate_pdf, compress_pdf, add_text_to_pdf, add_watermark_text, protect_pdf, unlock_pdf
)
from core.image_tools import (
    process_image, strip_exif, generate_favicons, PRESETS
)
from core.video_tools import (
    trim_video, video_to_gif, extract_audio, mute_video, change_video_speed, convert_video_format
)

class TestCoreModules(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_image_tools(self):
        # Create a test image
        img_path = os.path.join(self.work_dir, 'sample.jpg')
        img = Image.new('RGB', (800, 600), color=(200, 100, 50))
        img.save(img_path)

        # Test resize percentage
        out_scaled = os.path.join(self.work_dir, 'scaled.jpg')
        process_image(img_path, out_scaled, scale_percent=50)
        with Image.open(out_scaled) as s_img:
            self.assertEqual(s_img.size, (400, 300))

        # Test preset
        out_preset = os.path.join(self.work_dir, 'preset.png')
        process_image(img_path, out_preset, preset_name='Instagram Post Square (1080x1080)')
        with Image.open(out_preset) as p_img:
            self.assertEqual(p_img.size, (1080, 1080))

        # Test strip EXIF
        out_noexif = os.path.join(self.work_dir, 'noexif.jpg')
        strip_exif(img_path, out_noexif)
        self.assertTrue(os.path.exists(out_noexif))

        # Test Favicon generation
        fav_dir = os.path.join(self.work_dir, 'favicons')
        favs = generate_favicons(img_path, fav_dir)
        self.assertTrue(len(favs) >= 3)
        self.assertTrue(os.path.exists(os.path.join(fav_dir, 'favicon.ico')))

    def test_pdf_tools(self):
        # Create two sample images
        img1 = os.path.join(self.work_dir, 'p1.png')
        img2 = os.path.join(self.work_dir, 'p2.png')
        Image.new('RGB', (300, 400), color=(255, 0, 0)).save(img1)
        Image.new('RGB', (300, 400), color=(0, 255, 0)).save(img2)

        # Images to PDF
        pdf1 = os.path.join(self.work_dir, 'doc1.pdf')
        images_to_pdf([img1, img2], pdf1)
        self.assertTrue(os.path.exists(pdf1))

        # PDF to images
        extracted_imgs = pdf_to_images(pdf1, os.path.join(self.work_dir, 'pdf_imgs'))
        self.assertEqual(len(extracted_imgs), 2)

        # Rotate PDF
        rot_pdf = os.path.join(self.work_dir, 'doc1_rot.pdf')
        rotate_pdf(pdf1, rot_pdf, angle=90)
        with pymupdf.open(rot_pdf) as rdoc:
            self.assertEqual(rdoc[0].rotation, 90)

        # Merge PDFs
        pdf2 = os.path.join(self.work_dir, 'doc2.pdf')
        images_to_pdf([img1], pdf2)
        merged_pdf = os.path.join(self.work_dir, 'merged.pdf')
        merge_pdfs([pdf1, pdf2], merged_pdf)
        with pymupdf.open(merged_pdf) as mdoc:
            self.assertEqual(len(mdoc), 3)

        # Add watermark & text
        wm_pdf = os.path.join(self.work_dir, 'watermarked.pdf')
        add_watermark_text(pdf1, wm_pdf, 'CONFIDENTIAL')
        self.assertTrue(os.path.exists(wm_pdf))

        # Protect & Unlock PDF
        enc_pdf = os.path.join(self.work_dir, 'enc.pdf')
        protect_pdf(pdf1, enc_pdf, 'secret123')
        dec_pdf = os.path.join(self.work_dir, 'dec.pdf')
        unlock_pdf(enc_pdf, dec_pdf, 'secret123')
        self.assertTrue(os.path.exists(dec_pdf))

    def test_video_tools(self):
        # Generate a synthetic 2-second test video with audio using ffmpeg
        test_video = os.path.join(self.work_dir, 'test_in.mp4')
        ffmpeg_exe = get_ffmpeg_path()
        cmd = [
            '-y',
            '-f', 'lavfi', '-i', 'testsrc=duration=2:size=320x240:rate=15',
            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2',
            '-c:v', 'libx264', '-c:a', 'aac',
            test_video
        ]
        run_ffmpeg(cmd)
        self.assertTrue(os.path.exists(test_video))

        # Video to GIF
        gif_out = os.path.join(self.work_dir, 'test.gif')
        video_to_gif(test_video, gif_out, fps=10, scale_width=160)
        self.assertTrue(os.path.exists(gif_out))

        # Extract Audio
        audio_out = os.path.join(self.work_dir, 'audio.mp3')
        extract_audio(test_video, audio_out, 'mp3')
        self.assertTrue(os.path.exists(audio_out))

        # Mute Video
        muted_out = os.path.join(self.work_dir, 'muted.mp4')
        mute_video(test_video, muted_out)
        self.assertTrue(os.path.exists(muted_out))

        # Speed Change
        speed_out = os.path.join(self.work_dir, 'speed.mp4')
        change_video_speed(test_video, speed_out, speed_factor=1.5)
        self.assertTrue(os.path.exists(speed_out))

if __name__ == '__main__':
    unittest.main()
