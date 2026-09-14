import os
import threading
from tkinter import filedialog, messagebox, colorchooser
import customtkinter as ctk
from PIL import Image

from core.image_tools import (
    process_image, strip_exif, generate_favicons, remove_background, PRESETS,
    add_canvas_padding, round_corners, add_drop_shadow, crop_image,
    estimate_output_size, extract_color_palette, apply_rename_pattern,
    adjust_color_temperature, smart_upscale_image
)

class ImageTab:
    def __init__(self, app, parent_tab):
        self.app = app
        self.tab = parent_tab
        self.image_files = []
        self.preview_orig_img = None
        self.preview_orig_tk = None
        self.preview_processed_tk = None
        self.rotate_angle_val = 0
        self.original_w = 0
        self.original_h = 0
        self.aspect_ratio = 1.0
        self._updating_dimensions = False

        # Phase 1 & 2 Properties
        self.crop_box = None
        self.palette_colors = []
        self.padding_color = (255, 255, 255)

        self._setup_ui()

    def _setup_ui(self):
        # Left Column: File selection & Live Previews
        left_frame = ctk.CTkFrame(self.tab, width=380)
        left_frame.pack(side='left', fill='both', expand=False, padx=(10, 5), pady=10)

        # Drag and drop file support
        try:
            left_frame.drop_target_register('DND_Files')
            left_frame.dnd_bind('<<Drop>>', self._on_dnd_drop)
        except Exception:
            pass

        ctk.CTkLabel(left_frame, text='Selected Images (Drag & Drop supported)', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(10, 5))

        btn_row = ctk.CTkFrame(left_frame, fg_color='transparent')
        btn_row.pack(fill='x', padx=10, pady=5)
        ctk.CTkButton(btn_row, text='+ Add Images', width=130, command=self._add_images).pack(side='left', padx=(0, 5))
        ctk.CTkButton(btn_row, text='Clear', width=70, fg_color='#6c757d', hover_color='#5a6268', command=self._clear_images).pack(side='right')

        self.img_listbox = ctk.CTkTextbox(left_frame, height=100, state='disabled')
        self.img_listbox.pack(fill='x', padx=10, pady=5)

        self.img_count_lbl = ctk.CTkLabel(left_frame, text='0 images selected', text_color='gray', font=ctk.CTkFont(size=11))
        self.img_count_lbl.pack(anchor='w', padx=10, pady=(0, 5))

        # Visual Side-by-Side Preview Section
        ctk.CTkLabel(left_frame, text='Side-by-Side Preview', font=ctk.CTkFont(size=13, weight='bold')).pack(anchor='w', padx=10, pady=(5, 2))

        preview_box = ctk.CTkFrame(left_frame, fg_color='transparent')
        preview_box.pack(fill='both', expand=True, padx=10, pady=5)

        # Before Card
        before_card = ctk.CTkFrame(preview_box, width=170, height=170)
        before_card.pack(side='left', fill='both', expand=True, padx=(0, 5))
        ctk.CTkLabel(before_card, text='Original', font=ctk.CTkFont(size=11, weight='bold'), text_color='gray').pack(pady=(4, 2))
        self.preview_before_lbl = ctk.CTkLabel(before_card, text='[No Image]')
        self.preview_before_lbl.pack(expand=True, fill='both', padx=5, pady=5)

        # After Card
        after_card = ctk.CTkFrame(preview_box, width=170, height=170)
        after_card.pack(side='right', fill='both', expand=True, padx=(5, 0))
        ctk.CTkLabel(after_card, text='Preview', font=ctk.CTkFont(size=11, weight='bold'), text_color='#1f8b4c').pack(pady=(4, 2))
        self.preview_after_lbl = ctk.CTkLabel(after_card, text='[No Preview]')
        self.preview_after_lbl.pack(expand=True, fill='both', padx=5, pady=5)

        # Dominant Palette Swatches Card
        palette_card = ctk.CTkFrame(left_frame)
        palette_card.pack(fill='x', padx=10, pady=(4, 6))
        ctk.CTkLabel(palette_card, text='🎨 Color Palette (Click to copy hex):', font=ctk.CTkFont(size=11, weight='bold')).pack(anchor='w', padx=8, pady=(4, 2))
        self.palette_swatches_frame = ctk.CTkFrame(palette_card, fg_color='transparent')
        self.palette_swatches_frame.pack(fill='x', padx=8, pady=(0, 6))
        self.palette_empty_lbl = ctk.CTkLabel(self.palette_swatches_frame, text='Load an image to extract palette', text_color='gray', font=ctk.CTkFont(size=10))
        self.palette_empty_lbl.pack(anchor='w')

        # Update Preview Button
        update_prev_btn = ctk.CTkButton(left_frame, text='🔄 Refresh Live Preview', command=self._update_preview, height=28)
        update_prev_btn.pack(fill='x', padx=10, pady=(2, 10))

        # Right Column: Controls & Superpowers (Scrollable)
        right_frame = ctk.CTkScrollableFrame(self.tab)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 10), pady=10)

        # Section A: Resizing & Presets
        ctk.CTkLabel(right_frame, text='1. Image Resizer & Platform Presets', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(5, 5))
        
        preset_frame = ctk.CTkFrame(right_frame)
        preset_frame.pack(fill='x', padx=10, pady=5)

        # Current Size Indicator Display Card
        current_size_card = ctk.CTkFrame(preset_frame, fg_color='#1f3326', corner_radius=6)
        current_size_card.pack(fill='x', padx=10, pady=(8, 8))
        
        self.current_size_lbl = ctk.CTkLabel(
            current_size_card,
            text='Current Size: Select an image to view dimensions',
            font=ctk.CTkFont(size=12, weight='bold'),
            text_color='#70e090'
        )
        self.current_size_lbl.pack(padx=10, pady=6)

        ctk.CTkLabel(preset_frame, text='Social / Platform Preset:').pack(anchor='w', padx=10, pady=(4, 2))
        preset_choices = ['None (Custom)'] + list(PRESETS.keys())
        self.preset_combo = ctk.CTkComboBox(preset_frame, values=preset_choices, command=self._on_preset_selected, width=280)
        self.preset_combo.set('None (Custom)')
        self.preset_combo.pack(anchor='w', padx=10, pady=(0, 8))

        # Interactive Width, Height & Scale %
        dim_row = ctk.CTkFrame(preset_frame, fg_color='transparent')
        dim_row.pack(fill='x', padx=10, pady=(0, 8))

        ctk.CTkLabel(dim_row, text='Width (px):', font=ctk.CTkFont(weight='bold')).pack(side='left')
        self.custom_w_entry = ctk.CTkEntry(dim_row, width=80)
        self.custom_w_entry.pack(side='left', padx=(5, 15))
        self.custom_w_entry.bind('<KeyRelease>', self._on_width_type)

        ctk.CTkLabel(dim_row, text='Height (px):', font=ctk.CTkFont(weight='bold')).pack(side='left')
        self.custom_h_entry = ctk.CTkEntry(dim_row, width=80)
        self.custom_h_entry.pack(side='left', padx=(5, 15))
        self.custom_h_entry.bind('<KeyRelease>', self._on_height_type)

        ctk.CTkLabel(dim_row, text='Scale %:').pack(side='left')
        self.scale_pct_entry = ctk.CTkEntry(dim_row, width=65)
        self.scale_pct_entry.insert(0, '100')
        self.scale_pct_entry.pack(side='left', padx=5)
        self.scale_pct_entry.bind('<KeyRelease>', self._on_scale_pct_type)

        crop_row = ctk.CTkFrame(preset_frame, fg_color='transparent')
        crop_row.pack(fill='x', padx=10, pady=(0, 8))
        self.keep_aspect_chk = ctk.CTkCheckBox(crop_row, text='🔒 Lock Aspect Ratio')
        self.keep_aspect_chk.select()
        self.keep_aspect_chk.pack(side='left')

        self.crop_btn = ctk.CTkButton(crop_row, text='✂️ Crop Tool', width=100, fg_color='#2b5b84', hover_color='#1f4463', command=self._open_crop_dialog)
        self.crop_btn.pack(side='right')

        # Section B: Tuning & Color Sliders
        ctk.CTkLabel(right_frame, text='2. Color Adjustments & Filters', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(15, 5))

        tune_frame = ctk.CTkFrame(right_frame)
        tune_frame.pack(fill='x', padx=10, pady=5)

        self.bright_slider = self._create_slider_row(tune_frame, 'Brightness', 0.2, 2.0, 1.0)
        self.contrast_slider = self._create_slider_row(tune_frame, 'Contrast', 0.2, 2.0, 1.0)
        self.sharp_slider = self._create_slider_row(tune_frame, 'Sharpness', 0.0, 3.0, 1.0)
        self.sat_slider = self._create_slider_row(tune_frame, 'Saturation', 0.0, 2.0, 1.0)
        self.temp_slider = self._create_slider_row(tune_frame, 'Temperature', -100.0, 100.0, 0.0)

        self.grayscale_chk = ctk.CTkCheckBox(tune_frame, text='Monochrome / Black & White', command=self._update_preview)
        self.grayscale_chk.pack(anchor='w', padx=10, pady=6)

        # Section C: Superpowers & Privacy
        ctk.CTkLabel(right_frame, text='3. Superpowers, Canvas & Styling', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(15, 5))

        super_frame = ctk.CTkFrame(right_frame)
        super_frame.pack(fill='x', padx=10, pady=5)

        self.rembg_chk = ctk.CTkCheckBox(super_frame, text='✨ AI Background Remover (Auto cutout transparent PNG)')
        self.rembg_chk.pack(anchor='w', padx=10, pady=(8, 4))

        self.strip_exif_chk = ctk.CTkCheckBox(super_frame, text='🛡️ Strip EXIF & Metadata (Scrub GPS, camera serials, timestamps)')
        self.strip_exif_chk.select()
        self.strip_exif_chk.pack(anchor='w', padx=10, pady=4)

        self.favicon_chk = ctk.CTkCheckBox(super_frame, text='📦 Generate Multi-Size Favicon / App Icon (.ico bundle)')
        self.favicon_chk.pack(anchor='w', padx=10, pady=4)

        # Canvas Border / Padding
        pad_row = ctk.CTkFrame(super_frame, fg_color='transparent')
        pad_row.pack(fill='x', padx=10, pady=4)
        self.pad_chk = ctk.CTkCheckBox(pad_row, text='🖼️ Canvas Padding (px):', command=self._update_preview)
        self.pad_chk.pack(side='left')
        self.pad_val_entry = ctk.CTkEntry(pad_row, width=55)
        self.pad_val_entry.insert(0, '25')
        self.pad_val_entry.pack(side='left', padx=5)
        self.pad_val_entry.bind('<KeyRelease>', lambda e: self._update_preview())
        ctk.CTkButton(pad_row, text='🎨 Color', width=70, command=self._pick_pad_color).pack(side='left', padx=5)

        # Rounded Corners & Drop Shadow
        round_row = ctk.CTkFrame(super_frame, fg_color='transparent')
        round_row.pack(fill='x', padx=10, pady=4)
        self.round_chk = ctk.CTkCheckBox(round_row, text='🔘 Rounded Corners (px):', command=self._update_preview)
        self.round_chk.pack(side='left')
        self.round_radius_entry = ctk.CTkEntry(round_row, width=55)
        self.round_radius_entry.insert(0, '30')
        self.round_radius_entry.pack(side='left', padx=5)
        self.round_radius_entry.bind('<KeyRelease>', lambda e: self._update_preview())

        self.shadow_chk = ctk.CTkCheckBox(super_frame, text='🌑 Soft Drop Shadow (Translucent Alpha)', command=self._update_preview)
        self.shadow_chk.pack(anchor='w', padx=10, pady=(4, 4))

        self.upscale_chk = ctk.CTkCheckBox(super_frame, text='🔍 Smart Super-Resolution (Crisp 2x edge-preserving upscale)')
        self.upscale_chk.pack(anchor='w', padx=10, pady=(4, 8))

        # Transformations & Watermarking
        trans_frame = ctk.CTkFrame(right_frame)
        trans_frame.pack(fill='x', padx=10, pady=10)

        t_row = ctk.CTkFrame(trans_frame, fg_color='transparent')
        t_row.pack(fill='x', padx=10, pady=8)
        ctk.CTkButton(t_row, text='↷ Rotate 90°', width=100, command=self._rotate_90).pack(side='left', padx=3)
        self.flip_h_var = ctk.BooleanVar(value=False)
        self.flip_v_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(t_row, text='Flip H', variable=self.flip_h_var, command=self._update_preview).pack(side='left', padx=10)
        ctk.CTkCheckBox(t_row, text='Flip V', variable=self.flip_v_var, command=self._update_preview).pack(side='left', padx=5)

        wm_row = ctk.CTkFrame(trans_frame, fg_color='transparent')
        wm_row.pack(fill='x', padx=10, pady=(0, 8))
        ctk.CTkLabel(wm_row, text='Watermark:').pack(side='left')
        self.img_wm_entry = ctk.CTkEntry(wm_row, placeholder_text='Optional watermark text', width=180)
        self.img_wm_entry.pack(side='left', padx=5)

        out_fmt_row = ctk.CTkFrame(trans_frame, fg_color='transparent')
        out_fmt_row.pack(fill='x', padx=10, pady=(0, 8))
        ctk.CTkLabel(out_fmt_row, text='Format:').pack(side='left')
        self.img_fmt_combo = ctk.CTkComboBox(out_fmt_row, values=['Original Format', 'PNG', 'JPEG', 'WEBP', 'ICO', 'BMP'], width=140, command=lambda e: self._update_size_estimate())
        self.img_fmt_combo.set('Original Format')
        self.img_fmt_combo.pack(side='left', padx=5)

        # Quality Slider & Squoosh-style Live Size Readout
        qual_box = ctk.CTkFrame(trans_frame)
        qual_box.pack(fill='x', padx=10, pady=(4, 8))
        q_header = ctk.CTkFrame(qual_box, fg_color='transparent')
        q_header.pack(fill='x', padx=8, pady=(4, 2))
        ctk.CTkLabel(q_header, text='Output Quality:').pack(side='left')
        self.qual_val_lbl = ctk.CTkLabel(q_header, text='85%', font=ctk.CTkFont(weight='bold'))
        self.qual_val_lbl.pack(side='left', padx=4)
        self.qual_size_lbl = ctk.CTkLabel(q_header, text='Est. Size: -', text_color='#70e090', font=ctk.CTkFont(weight='bold'))
        self.qual_size_lbl.pack(side='right')

        self.quality_slider = ctk.CTkSlider(qual_box, from_=10, to=100, command=self._on_quality_slide)
        self.quality_slider.set(85)
        self.quality_slider.pack(fill='x', padx=8, pady=(0, 6))

        # Batch Rename with Pattern
        rename_box = ctk.CTkFrame(trans_frame)
        rename_box.pack(fill='x', padx=10, pady=(4, 8))
        self.rename_chk = ctk.CTkCheckBox(rename_box, text='🏷️ Batch Rename Pattern', command=self._update_rename_preview)
        self.rename_chk.pack(anchor='w', padx=8, pady=(4, 2))
        self.rename_pattern_entry = ctk.CTkEntry(rename_box, placeholder_text='e.g. {name}_{index:03d}')
        self.rename_pattern_entry.insert(0, '{name}_{index:03d}')
        self.rename_pattern_entry.pack(fill='x', padx=8, pady=(0, 4))
        self.rename_pattern_entry.bind('<KeyRelease>', lambda e: self._update_rename_preview())
        self.rename_preview_lbl = ctk.CTkLabel(rename_box, text='Example: photo_001.jpg  (Tokens: {name}, {index}, {width}, {height}, {date})', text_color='gray', font=ctk.CTkFont(size=10))
        self.rename_preview_lbl.pack(anchor='w', padx=8, pady=(0, 4))

        # Progress & Run
        self.img_progress = ctk.CTkProgressBar(right_frame)
        self.img_progress.set(0)
        self.img_progress.pack(fill='x', padx=10, pady=(15, 5))

        self.img_status_lbl = ctk.CTkLabel(right_frame, text='Ready', font=ctk.CTkFont(size=12))
        self.img_status_lbl.pack(anchor='w', padx=10, pady=2)

        self.img_run_btn = ctk.CTkButton(
            right_frame,
            text='🎨 Process Image(s)',
            height=40,
            font=ctk.CTkFont(size=14, weight='bold'),
            fg_color='#1f8b4c',
            hover_color='#176d3b',
            command=self._run_task_thread
        )
        self.img_run_btn.pack(fill='x', padx=10, pady=10)

    def _rotate_90(self):
        self.rotate_angle_val = (self.rotate_angle_val + 90) % 360
        self._update_preview()

    def _create_slider_row(self, parent, label, min_val, max_val, default):
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=10, pady=3)
        lbl = ctk.CTkLabel(row, text=f'{label}:', width=80, anchor='w')
        lbl.pack(side='left')
        val_lbl = ctk.CTkLabel(row, text=f'{default:.2f}', width=45)
        
        def on_slide(val):
            val_lbl.configure(text=f'{val:.2f}')
            self._update_preview()

        slider = ctk.CTkSlider(row, from_=min_val, to=max_val, command=on_slide)
        slider.set(default)
        slider.pack(side='left', fill='x', expand=True, padx=5)
        val_lbl.pack(side='right')
        return slider

    def _on_width_type(self, event=None):
        if self._updating_dimensions or not self.keep_aspect_chk.get() or self.aspect_ratio <= 0:
            return
        try:
            w_text = self.custom_w_entry.get().strip()
            if w_text.isdigit():
                w = int(w_text)
                new_h = max(1, int(w / self.aspect_ratio))
                self._updating_dimensions = True
                self.custom_h_entry.delete(0, 'end')
                self.custom_h_entry.insert(0, str(new_h))
                self._updating_dimensions = False
        except Exception:
            self._updating_dimensions = False

    def _on_height_type(self, event=None):
        if self._updating_dimensions or not self.keep_aspect_chk.get() or self.aspect_ratio <= 0:
            return
        try:
            h_text = self.custom_h_entry.get().strip()
            if h_text.isdigit():
                h = int(h_text)
                new_w = max(1, int(h * self.aspect_ratio))
                self._updating_dimensions = True
                self.custom_w_entry.delete(0, 'end')
                self.custom_w_entry.insert(0, str(new_w))
                self._updating_dimensions = False
        except Exception:
            self._updating_dimensions = False

    def _on_scale_pct_type(self, event=None):
        if self._updating_dimensions or self.original_w <= 0 or self.original_h <= 0:
            return
        try:
            pct_text = self.scale_pct_entry.get().strip()
            if pct_text.replace('.', '', 1).isdigit():
                pct = float(pct_text) / 100.0
                new_w = max(1, int(self.original_w * pct))
                new_h = max(1, int(self.original_h * pct))
                self._updating_dimensions = True
                self.custom_w_entry.delete(0, 'end')
                self.custom_w_entry.insert(0, str(new_w))
                self.custom_h_entry.delete(0, 'end')
                self.custom_h_entry.insert(0, str(new_h))
                self._updating_dimensions = False
        except Exception:
            self._updating_dimensions = False

    def _on_preset_selected(self, choice):
        if choice in PRESETS:
            w, h, _ = PRESETS[choice]
            self._updating_dimensions = True
            self.custom_w_entry.delete(0, 'end')
            self.custom_w_entry.insert(0, str(w))
            self.custom_h_entry.delete(0, 'end')
            self.custom_h_entry.insert(0, str(h))
            self.scale_pct_entry.delete(0, 'end')
            self.scale_pct_entry.insert(0, '100')
            self._updating_dimensions = False
        self._update_preview()

    def _add_images(self):
        files = filedialog.askopenfilenames(
            title='Select Images to Edit',
            filetypes=[('Images', '*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tiff')]
        )
        if files:
            self.image_files.extend(files)
            self._update_listbox()
            self._load_preview_original(files[0])

    def _clear_images(self):
        self.image_files.clear()
        self.preview_orig_img = None
        self.preview_before_lbl.configure(image='', text='[No Image]')
        self.preview_after_lbl.configure(image='', text='[No Preview]')
        self.current_size_lbl.configure(text='Current Size: Select an image to view dimensions')
        self._update_listbox()

    def _update_listbox(self):
        self.img_listbox.configure(state='normal')
        self.img_listbox.delete('1.0', 'end')
        for i, f in enumerate(self.image_files):
            self.img_listbox.insert('end', f'{i+1}. {os.path.basename(f)}\n')
        self.img_listbox.configure(state='disabled')
        self.img_count_lbl.configure(text=f'{len(self.image_files)} images selected')

    def _on_dnd_drop(self, event):
        data = getattr(event, 'data', '')
        if not data:
            return
        import re
        files = re.findall(r'\{([^}]+)\}|(\S+)', data)
        paths = [f[0] or f[1] for f in files]
        valid = [p for p in paths if p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff')) and os.path.exists(p)]
        if valid:
            self.image_files.extend(valid)
            self._update_listbox()
            if not self.preview_orig_img:
                self._load_preview_original(valid[0])

    def _copy_hex(self, hex_code):
        try:
            self.tab.clipboard_clear()
            self.tab.clipboard_append(hex_code)
            self.img_status_lbl.configure(text=f'Copied {hex_code} to clipboard!')
        except Exception:
            pass

    def _pick_pad_color(self):
        color = colorchooser.askcolor(title='Choose Canvas Padding Color', initialcolor='#ffffff')
        if color and color[0]:
            self.padding_color = tuple(int(c) for c in color[0])
            self._update_preview()

    def _on_quality_slide(self, val):
        self.qual_val_lbl.configure(text=f'{int(val)}%')
        self._update_size_estimate()

    def _update_size_estimate(self):
        if not self.preview_orig_img:
            self.qual_size_lbl.configure(text='Est. Size: -')
            return
        try:
            fmt = self.img_fmt_combo.get()
            if fmt == 'Original Format':
                fmt = 'JPEG'
            qual = int(self.quality_slider.get())
            sz_bytes = estimate_output_size(self.preview_orig_img, format_name=fmt, quality=qual)
            if sz_bytes >= 1024 * 1024:
                sz_str = f'Est: {sz_bytes / (1024*1024):.2f} MB'
            else:
                sz_str = f'Est: {sz_bytes / 1024:.1f} KB'
            self.qual_size_lbl.configure(text=sz_str)
        except Exception:
            self.qual_size_lbl.configure(text='Est. Size: -')

    def _update_rename_preview(self, event=None):
        if not self.rename_chk.get():
            self.rename_preview_lbl.configure(text='Disabled (Original filename preserved)')
            return
        pattern = self.rename_pattern_entry.get().strip() or '{name}_{index:03d}'
        sample_w = self.original_w or 1920
        sample_h = self.original_h or 1080
        sample = apply_rename_pattern('photo.jpg', pattern, index=1, img_size=(sample_w, sample_h))
        self.rename_preview_lbl.configure(text=f'Preview: {sample} (Tokens: {{name}}, {{index}}, {{width}}, {{height}}, {{date}})')

    def _open_crop_dialog(self):
        if not self.preview_orig_img:
            messagebox.showinfo('No Image', 'Please load an image first to crop.')
            return

        crop_win = ctk.CTkToplevel(self.tab)
        crop_win.title('✂️ Interactive Crop Tool')
        crop_win.geometry('650x740')
        crop_win.grab_set()

        ctk.CTkLabel(crop_win, text='Click and drag a box on the image, or fine-tune coordinates below:', font=ctk.CTkFont(size=12, weight='bold')).pack(padx=10, pady=(10, 4))

        # Aspect Ratio Selector
        ratio_frame = ctk.CTkFrame(crop_win, fg_color='transparent')
        ratio_frame.pack(fill='x', padx=20, pady=(0, 6))
        ctk.CTkLabel(ratio_frame, text='Aspect Ratio:', font=ctk.CTkFont(size=11, weight='bold')).pack(side='left', padx=(0, 8))
        ratio_seg = ctk.CTkSegmentedButton(ratio_frame, values=['Free', '1:1', '16:9', '9:16', '4:3', '3:2'])
        ratio_seg.set('Free')
        ratio_seg.pack(side='left')

        max_cw, max_ch = 560, 460
        orig_w, orig_h = self.preview_orig_img.width, self.preview_orig_img.height
        scale = min(max_cw / orig_w, max_ch / orig_h)
        disp_w = max(1, int(orig_w * scale))
        disp_h = max(1, int(orig_h * scale))

        import tkinter as tk
        cv = tk.Canvas(crop_win, width=disp_w, height=disp_h, bg='#1a1a1a', highlightthickness=1, highlightbackground='#444444')
        cv.pack(padx=10, pady=5)

        disp_img = self.preview_orig_img.copy().resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        from PIL import ImageTk
        disp_photo = ImageTk.PhotoImage(disp_img)
        cv.create_image(0, 0, anchor='nw', image=disp_photo)
        cv.image = disp_photo

        crop_state = {'start_x': 0, 'start_y': 0, 'rect_id': None}

        def on_ratio_change(ratio_val):
            if ratio_val == 'Free' or not crop_state['rect_id']:
                return
            r_map = {'1:1': 1.0, '16:9': 16.0 / 9.0, '9:16': 9.0 / 16.0, '4:3': 4.0 / 3.0, '3:2': 3.0 / 2.0}
            target_ratio = r_map.get(ratio_val, 1.0)
            coords = cv.coords(crop_state['rect_id'])
            if len(coords) == 4:
                x0, y0, x1, y1 = coords
                cx = (x0 + x1) / 2.0
                cy = (y0 + y1) / 2.0
                box_w = abs(x1 - x0)
                box_h = box_w / target_ratio
                if cy - box_h / 2.0 < 0 or cy + box_h / 2.0 > disp_h:
                    box_h = abs(y1 - y0)
                    box_w = box_h * target_ratio
                nx0 = max(0, cx - box_w / 2.0)
                nx1 = min(disp_w, cx + box_w / 2.0)
                ny0 = max(0, cy - box_h / 2.0)
                ny1 = min(disp_h, cy + box_h / 2.0)
                cv.coords(crop_state['rect_id'], nx0, ny0, nx1, ny1)
                sync_entries_to_coords(int(nx0 / scale), int(ny0 / scale), int(nx1 / scale), int(ny1 / scale))

        ratio_seg.configure(command=on_ratio_change)

        coord_row = ctk.CTkFrame(crop_win, fg_color='transparent')
        coord_row.pack(fill='x', padx=20, pady=8)

        ctk.CTkLabel(coord_row, text='X1:').pack(side='left', padx=(0, 2))
        e_x1 = ctk.CTkEntry(coord_row, width=60)
        e_x1.pack(side='left', padx=(0, 8))

        ctk.CTkLabel(coord_row, text='Y1:').pack(side='left', padx=(0, 2))
        e_y1 = ctk.CTkEntry(coord_row, width=60)
        e_y1.pack(side='left', padx=(0, 8))

        ctk.CTkLabel(coord_row, text='X2:').pack(side='left', padx=(0, 2))
        e_x2 = ctk.CTkEntry(coord_row, width=60)
        e_x2.pack(side='left', padx=(0, 8))

        ctk.CTkLabel(coord_row, text='Y2:').pack(side='left', padx=(0, 2))
        e_y2 = ctk.CTkEntry(coord_row, width=60)
        e_y2.pack(side='left', padx=(0, 8))

        crop_dim_lbl = ctk.CTkLabel(coord_row, text=f'Original: {orig_w}x{orig_h}px', text_color='gray', font=ctk.CTkFont(size=11))
        crop_dim_lbl.pack(side='right')

        def sync_entries_to_coords(x0, y0, x1, y1):
            for e, val in [(e_x1, x0), (e_y1, y0), (e_x2, x1), (e_y2, y1)]:
                e.delete(0, 'end')
                e.insert(0, str(int(val)))

        if self.crop_box:
            ox0, oy0, ox1, oy1 = self.crop_box
            sync_entries_to_coords(ox0, oy0, ox1, oy1)
            cx0, cy0 = ox0 * scale, oy0 * scale
            cx1, cy1 = ox1 * scale, oy1 * scale
            crop_state['rect_id'] = cv.create_rectangle(cx0, cy0, cx1, cy1, outline='#3498db', width=2, dash=(4, 2))
        else:
            sync_entries_to_coords(0, 0, orig_w, orig_h)

        def on_down(e):
            crop_state['start_x'] = max(0, min(disp_w, e.x))
            crop_state['start_y'] = max(0, min(disp_h, e.y))
            if crop_state['rect_id']:
                cv.delete(crop_state['rect_id'])
                crop_state['rect_id'] = None

        def on_drag(e):
            cur_x = max(0, min(disp_w, e.x))
            cur_y = max(0, min(disp_h, e.y))
            sx, sy = crop_state['start_x'], crop_state['start_y']

            ratio_val = ratio_seg.get()
            if ratio_val != 'Free':
                r_map = {'1:1': 1.0, '16:9': 16.0 / 9.0, '9:16': 9.0 / 16.0, '4:3': 4.0 / 3.0, '3:2': 3.0 / 2.0}
                target_ratio = r_map.get(ratio_val, 1.0)
                dx = cur_x - sx
                dy = cur_y - sy
                sign_x = 1 if dx >= 0 else -1
                sign_y = 1 if dy >= 0 else -1

                calc_w = abs(dx)
                calc_h = calc_w / target_ratio
                if (sy + sign_y * calc_h) < 0 or (sy + sign_y * calc_h) > disp_h:
                    calc_h = abs(dy)
                    calc_w = calc_h * target_ratio

                cur_x = max(0, min(disp_w, sx + sign_x * calc_w))
                cur_y = max(0, min(disp_h, sy + sign_y * calc_h))

            x0, x1 = min(sx, cur_x), max(sx, cur_x)
            y0, y1 = min(sy, cur_y), max(sy, cur_y)
            if not crop_state['rect_id']:
                crop_state['rect_id'] = cv.create_rectangle(x0, y0, x1, y1, outline='#3498db', width=2, dash=(4, 2))
            else:
                cv.coords(crop_state['rect_id'], x0, y0, x1, y1)

            img_x0 = int(x0 / scale)
            img_y0 = int(y0 / scale)
            img_x1 = int(x1 / scale)
            img_y1 = int(y1 / scale)
            sync_entries_to_coords(img_x0, img_y0, img_x1, img_y1)

        cv.bind('<ButtonPress-1>', on_down)
        cv.bind('<B1-Motion>', on_drag)

        btn_row = ctk.CTkFrame(crop_win, fg_color='transparent')
        btn_row.pack(fill='x', padx=20, pady=(10, 15))

        def apply_crop():
            try:
                x0 = int(e_x1.get().strip())
                y0 = int(e_y1.get().strip())
                x1 = int(e_x2.get().strip())
                y1 = int(e_y2.get().strip())
                if x1 > x0 and y1 > y0 and x1 <= orig_w and y1 <= orig_h:
                    self.crop_box = (x0, y0, x1, y1)
                    self.crop_btn.configure(text=f'✂️ Crop ({x1-x0}x{y1-y0})', fg_color='#1f8b4c')
                    self._update_preview()
                    crop_win.destroy()
                else:
                    messagebox.showerror('Invalid Coordinates', f'Coordinates must be within 0..{orig_w} and 0..{orig_h}, with X2 > X1 and Y2 > Y1.')
            except ValueError:
                messagebox.showerror('Invalid Input', 'Please enter valid integer pixel coordinates.')

        def clear_crop():
            self.crop_box = None
            self.crop_btn.configure(text='✂️ Crop Tool', fg_color='#2b5b84')
            self._update_preview()
            crop_win.destroy()

        ctk.CTkButton(btn_row, text='Apply Crop', fg_color='#1f8b4c', hover_color='#176d3b', width=130, command=apply_crop).pack(side='left', padx=(0, 5))
        ctk.CTkButton(btn_row, text='Reset Crop', fg_color='#6c757d', hover_color='#5a6268', width=110, command=clear_crop).pack(side='left', padx=5)
        ctk.CTkButton(btn_row, text='Cancel', fg_color='#495057', hover_color='#343a40', width=90, command=crop_win.destroy).pack(side='right')

    def _load_preview_original(self, path):
        try:
            with Image.open(path) as img:
                self.preview_orig_img = img.copy()
                self.original_w = img.width
                self.original_h = img.height
                self.aspect_ratio = img.width / float(max(1, img.height))

            sz_bytes = os.path.getsize(path)
            sz_str = f'{sz_bytes / (1024*1024):.2f} MB' if sz_bytes >= 1024*1024 else f'{sz_bytes / 1024:.1f} KB'

            self.current_size_lbl.configure(
                text=f'Current Size: {self.original_w} × {self.original_h} px  ({sz_str})'
            )

            self._updating_dimensions = True
            self.custom_w_entry.delete(0, 'end')
            self.custom_w_entry.insert(0, str(self.original_w))
            self.custom_h_entry.delete(0, 'end')
            self.custom_h_entry.insert(0, str(self.original_h))
            self.scale_pct_entry.delete(0, 'end')
            self.scale_pct_entry.insert(0, '100')
            self._updating_dimensions = False

            thumb = self.preview_orig_img.copy()
            thumb.thumbnail((150, 150))
            self.preview_orig_tk = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
            self.preview_before_lbl.configure(image=self.preview_orig_tk, text='')

            # Extract Color Palette
            for widget in self.palette_swatches_frame.winfo_children():
                widget.destroy()
            palette = extract_color_palette(self.preview_orig_img, n_colors=6)
            self.palette_colors = palette
            if palette:
                for hex_color in palette:
                    r = int(hex_color[1:3], 16)
                    g = int(hex_color[3:5], 16)
                    b = int(hex_color[5:7], 16)
                    lum = 0.299 * r + 0.587 * g + 0.114 * b
                    tc = '#000000' if lum > 140 else '#ffffff'
                    swatch = ctk.CTkButton(
                        self.palette_swatches_frame,
                        text=hex_color,
                        width=50,
                        height=22,
                        fg_color=hex_color,
                        hover_color=hex_color,
                        text_color=tc,
                        font=ctk.CTkFont(size=9, weight='bold'),
                        command=lambda c=hex_color: self._copy_hex(c)
                    )
                    swatch.pack(side='left', padx=2)
            else:
                ctk.CTkLabel(self.palette_swatches_frame, text='No palette extracted', text_color='gray', font=ctk.CTkFont(size=10)).pack(anchor='w')

            self._update_preview()
        except Exception:
            self.preview_before_lbl.configure(text='Error loading')

    def _update_preview(self):
        if not self.preview_orig_img:
            return
        try:
            img = self.preview_orig_img.copy()

            if self.crop_box and len(self.crop_box) == 4:
                img = crop_image(img, self.crop_box)

            bright = self.bright_slider.get()
            contrast = self.contrast_slider.get()
            sharp = self.sharp_slider.get()
            sat = self.sat_slider.get()
            gray = self.grayscale_chk.get()
            temp = float(self.temp_slider.get())

            if gray or sat == 0.0:
                from PIL import ImageOps
                img = ImageOps.grayscale(img)
            elif sat != 1.0:
                from PIL import ImageEnhance
                img = ImageEnhance.Color(img.convert('RGB')).enhance(sat)

            if bright != 1.0:
                from PIL import ImageEnhance
                img = ImageEnhance.Brightness(img.convert('RGB') if img.mode not in ('RGB', 'RGBA') else img).enhance(bright)

            if contrast != 1.0:
                from PIL import ImageEnhance
                img = ImageEnhance.Contrast(img.convert('RGB') if img.mode not in ('RGB', 'RGBA') else img).enhance(contrast)

            if sharp != 1.0:
                from PIL import ImageEnhance
                img = ImageEnhance.Sharpness(img.convert('RGB') if img.mode not in ('RGB', 'RGBA') else img).enhance(sharp)

            if temp != 0:
                img = adjust_color_temperature(img, int(temp))

            if self.rotate_angle_val != 0:
                img = img.rotate(-self.rotate_angle_val, expand=True)
            if self.flip_h_var.get():
                img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if self.flip_v_var.get():
                img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

            if self.pad_chk.get():
                try:
                    p_val = int(self.pad_val_entry.get().strip())
                    img = add_canvas_padding(img, p_val, self.padding_color)
                except Exception:
                    pass

            if self.round_chk.get():
                try:
                    r_val = int(self.round_radius_entry.get().strip())
                    img = round_corners(img, r_val)
                except Exception:
                    pass

            if self.shadow_chk.get():
                try:
                    img = add_drop_shadow(img)
                except Exception:
                    pass

            thumb = img.copy()
            thumb.thumbnail((150, 150))
            self.preview_processed_tk = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
            self.preview_after_lbl.configure(image=self.preview_processed_tk, text='')
            self._update_size_estimate()
        except Exception:
            pass

    def _run_task_thread(self):
        if not self.image_files:
            messagebox.showwarning('No Files', 'Please select at least one image file first.')
            return
        threading.Thread(target=self._execute_task, daemon=True).start()

    def _execute_task(self):
        self.img_run_btn.configure(state='disabled')
        self.img_progress.set(0.05)
        out_dir = self.app.output_dir
        os.makedirs(out_dir, exist_ok=True)
        total = len(self.image_files)

        preset = self.preset_combo.get()
        if preset == 'None (Custom)':
            preset = None

        scale_pct = None
        try:
            val = float(self.scale_pct_entry.get().strip())
            if val != 100:
                scale_pct = val
        except ValueError:
            pass

        w_val = None
        try:
            w_val = int(self.custom_w_entry.get().strip())
        except ValueError:
            pass

        h_val = None
        try:
            h_val = int(self.custom_h_entry.get().strip())
        except ValueError:
            pass

        keep_asp = bool(self.keep_aspect_chk.get())
        bright = float(self.bright_slider.get())
        contrast = float(self.contrast_slider.get())
        sharp = float(self.sharp_slider.get())
        sat = float(self.sat_slider.get())
        gray = bool(self.grayscale_chk.get())
        rot = self.rotate_angle_val
        fl_h = self.flip_h_var.get()
        fl_v = self.flip_v_var.get()
        strip_meta = bool(self.strip_exif_chk.get())
        do_rembg = bool(self.rembg_chk.get())
        do_favicon = bool(self.favicon_chk.get())
        wm = self.img_wm_entry.get().strip() or None
        target_fmt = self.img_fmt_combo.get()
        qual = int(self.quality_slider.get())
        color_temp = int(self.temp_slider.get())
        crop_b = self.crop_box

        pad_val = None
        if self.pad_chk.get():
            try:
                pad_val = int(self.pad_val_entry.get().strip())
            except ValueError:
                pass

        round_val = None
        if self.round_chk.get():
            try:
                round_val = int(self.round_radius_entry.get().strip())
            except ValueError:
                pass

        do_shadow = bool(self.shadow_chk.get())
        do_upscale = bool(self.upscale_chk.get())
        do_rename = bool(self.rename_chk.get())
        rename_pat = self.rename_pattern_entry.get().strip() or '{name}_{index:03d}'

        try:
            for idx, img_path in enumerate(self.image_files):
                bname, orig_ext = os.path.splitext(os.path.basename(img_path))
                self.img_status_lbl.configure(text=f'Processing ({idx+1}/{total}): {os.path.basename(img_path)}')

                if do_rembg:
                    ext = '.png'
                elif target_fmt == 'Original Format':
                    ext = orig_ext
                elif target_fmt == 'JPEG':
                    ext = '.jpg'
                elif target_fmt == 'PNG':
                    ext = '.png'
                elif target_fmt == 'WEBP':
                    ext = '.webp'
                elif target_fmt == 'ICO':
                    ext = '.ico'
                elif target_fmt == 'BMP':
                    ext = '.bmp'
                else:
                    ext = orig_ext

                if do_rename:
                    renamed = apply_rename_pattern(img_path, rename_pat, index=idx+1, img_size=(w_val or self.original_w, h_val or self.original_h))
                    r_name = os.path.splitext(renamed)[0]
                    out_path = os.path.join(out_dir, f'{r_name}{ext}')
                else:
                    out_path = os.path.join(out_dir, f'{bname}_edited{ext}')

                if do_favicon:
                    fav_sub = os.path.join(out_dir, f'{bname}_icons')
                    generate_favicons(img_path, fav_sub, base_name=bname)

                padding_arg = (pad_val, self.padding_color) if pad_val else None

                process_image(
                    input_path=img_path,
                    output_path=out_path,
                    scale_percent=scale_pct,
                    width=w_val,
                    height=h_val,
                    keep_aspect=keep_asp,
                    preset_name=preset,
                    crop_box=crop_b,
                    brightness=bright,
                    contrast=contrast,
                    sharpness=sharp,
                    saturation=sat,
                    color_temperature=color_temp,
                    grayscale=gray,
                    rotate_angle=rot,
                    flip_h=fl_h,
                    flip_v=fl_v,
                    canvas_padding=padding_arg,
                    round_corners_radius=round_val,
                    drop_shadow=do_shadow,
                    strip_metadata=strip_meta,
                    quality=qual,
                    watermark_text=wm
                )

                if do_rembg:
                    self.img_status_lbl.configure(text=f'Removing Background ({idx+1}/{total})...')
                    remove_background(out_path, out_path)

                if do_upscale:
                    self.img_status_lbl.configure(text=f'Super-Resolving 2x ({idx+1}/{total})...')
                    smart_upscale_image(out_path, out_path, scale_factor=2)

                self.img_progress.set((idx + 1) / total)

            self.img_status_lbl.configure(text=f'Complete! Successfully processed {total} images.')
            messagebox.showinfo('Success', 'Image processing completed successfully!')
        except Exception as e:
            self.img_status_lbl.configure(text=f'Error: {str(e)}')
            messagebox.showerror('Error', f'Image processing failed:\n{str(e)}')
        finally:
            self.img_run_btn.configure(state='normal')
