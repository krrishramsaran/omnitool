import os
import unittest
import tempfile
import pymupdf
from PIL import Image
from core.pdf_tools import images_to_pdf, split_pdf, compress_pdf, add_text_to_pdf
from core.image_tools import remove_background, process_image
from core.video_tools import compress_video_target_size
from core.ffmpeg_utils import run_ffmpeg

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
        # Draw a small red square in center
        for x in range(20, 44):
            for y in range(20, 44):
                im.putpixel((x, y), (255, 0, 0))
        im.save(img_path)

        out_bg = os.path.join(self.work_dir, 'nobg.png')
        remove_background(img_path, out_bg)
        self.assertTrue(os.path.exists(out_bg))

if __name__ == '__main__':
    unittest.main()
