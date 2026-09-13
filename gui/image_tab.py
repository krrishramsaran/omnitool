import os
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

from core.image_tools import (
    process_image, strip_exif, generate_favicons, remove_background, PRESETS
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

        self._setup_ui()

    def _setup_ui(self):
        # Left Column: File selection & Live Previews
        left_frame = ctk.CTkFrame(self.tab, width=380)
        left_frame.pack(side='left', fill='both', expand=False, padx=(10, 5), pady=10)

        ctk.CTkLabel(left_frame, text='Selected Images', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(10, 5))

        btn_row = ctk.CTkFrame(left_frame, fg_color='transparent')
        btn_row.pack(fill='x', padx=10, pady=5)
        ctk.CTkButton(btn_row, text='+ Add Images', width=130, command=self._add_images).pack(side='left', padx=(0, 5))
        ctk.CTkButton(btn_row, text='Clear', width=70, fg_color='#6c757d', hover_color='#5a6268', command=self._clear_images).pack(side='right')

        self.img_listbox = ctk.CTkTextbox(left_frame, height=120, state='disabled')
        self.img_listbox.pack(fill='x', padx=10, pady=5)

        self.img_count_lbl = ctk.CTkLabel(left_frame, text='0 images selected', text_color='gray', font=ctk.CTkFont(size=11))
        self.img_count_lbl.pack(anchor='w', padx=10, pady=(0, 5))

        # Visual Side-by-Side Preview Section
        ctk.CTkLabel(left_frame, text='Side-by-Side Preview', font=ctk.CTkFont(size=13, weight='bold')).pack(anchor='w', padx=10, pady=(5, 2))

        preview_box = ctk.CTkFrame(left_frame, fg_color='transparent')
        preview_box.pack(fill='both', expand=True, padx=10, pady=5)

        # Before Card
        before_card = ctk.CTkFrame(preview_box, width=170, height=180)
        before_card.pack(side='left', fill='both', expand=True, padx=(0, 5))
        ctk.CTkLabel(before_card, text='Original', font=ctk.CTkFont(size=11, weight='bold'), text_color='gray').pack(pady=(4, 2))
        self.preview_before_lbl = ctk.CTkLabel(before_card, text='[No Image]')
        self.preview_before_lbl.pack(expand=True, fill='both', padx=5, pady=5)

        # After Card
        after_card = ctk.CTkFrame(preview_box, width=170, height=180)
        after_card.pack(side='right', fill='both', expand=True, padx=(5, 0))
        ctk.CTkLabel(after_card, text='Preview', font=ctk.CTkFont(size=11, weight='bold'), text_color='#1f8b4c').pack(pady=(4, 2))
        self.preview_after_lbl = ctk.CTkLabel(after_card, text='[No Preview]')
        self.preview_after_lbl.pack(expand=True, fill='both', padx=5, pady=5)

        # Update Preview Button
        update_prev_btn = ctk.CTkButton(left_frame, text='🔄 Refresh Live Preview', command=self._update_preview, height=28)
        update_prev_btn.pack(fill='x', padx=10, pady=(5, 10))

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

        self.keep_aspect_chk = ctk.CTkCheckBox(preset_frame, text='🔒 Lock Aspect Ratio (Proportional Resizing)')
        self.keep_aspect_chk.select()
        self.keep_aspect_chk.pack(anchor='w', padx=10, pady=(0, 8))

        # Section B: Tuning & Color Sliders
        ctk.CTkLabel(right_frame, text='2. Color Adjustments & Filters', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(15, 5))

        tune_frame = ctk.CTkFrame(right_frame)
        tune_frame.pack(fill='x', padx=10, pady=5)

        self.bright_slider = self._create_slider_row(tune_frame, 'Brightness', 0.2, 2.0, 1.0)
        self.contrast_slider = self._create_slider_row(tune_frame, 'Contrast', 0.2, 2.0, 1.0)
        self.sharp_slider = self._create_slider_row(tune_frame, 'Sharpness', 0.0, 3.0, 1.0)
        self.sat_slider = self._create_slider_row(tune_frame, 'Saturation', 0.0, 2.0, 1.0)

        self.grayscale_chk = ctk.CTkCheckBox(tune_frame, text='Monochrome / Black & White', command=self._update_preview)
        self.grayscale_chk.pack(anchor='w', padx=10, pady=6)

        # Section C: Superpowers & Privacy
        ctk.CTkLabel(right_frame, text='3. Superpowers & Output Options', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(15, 5))

        super_frame = ctk.CTkFrame(right_frame)
        super_frame.pack(fill='x', padx=10, pady=5)

        self.rembg_chk = ctk.CTkCheckBox(super_frame, text='✨ AI Background Remover (Auto cutout transparent PNG)')
        self.rembg_chk.pack(anchor='w', padx=10, pady=(8, 4))

        self.strip_exif_chk = ctk.CTkCheckBox(super_frame, text='🛡️ Strip EXIF & Metadata (Scrub GPS, camera serials, timestamps)')
        self.strip_exif_chk.select()
        self.strip_exif_chk.pack(anchor='w', padx=10, pady=4)

        self.favicon_chk = ctk.CTkCheckBox(super_frame, text='📦 Generate Multi-Size Favicon / App Icon (.ico bundle)')
        self.favicon_chk.pack(anchor='w', padx=10, pady=(4, 8))

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
        self.img_fmt_combo = ctk.CTkComboBox(out_fmt_row, values=['Original Format', 'PNG', 'JPEG', 'WEBP', 'ICO', 'BMP'], width=140)
        self.img_fmt_combo.set('Original Format')
        self.img_fmt_combo.pack(side='left', padx=5)

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

    def _load_preview_original(self, path):
        try:
            with Image.open(path) as img:
                self.preview_orig_img = img.copy()
                self.original_w = img.width
                self.original_h = img.height
                self.aspect_ratio = img.width / float(max(1, img.height))

            # Format file size
            sz_bytes = os.path.getsize(path)
            sz_str = f'{sz_bytes / (1024*1024):.2f} MB' if sz_bytes >= 1024*1024 else f'{sz_bytes / 1024:.1f} KB'

            self.current_size_lbl.configure(
                text=f'Current Size: {self.original_w} × {self.original_h} px  ({sz_str})'
            )

            # Prepopulate width and height inputs
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
            self._update_preview()
        except Exception:
            self.preview_before_lbl.configure(text='Error loading')

    def _update_preview(self):
        if not self.preview_orig_img:
            return
        try:
            img = self.preview_orig_img.copy()
            bright = self.bright_slider.get()
            contrast = self.contrast_slider.get()
            sharp = self.sharp_slider.get()
            sat = self.sat_slider.get()
            gray = self.grayscale_chk.get()

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

            if self.rotate_angle_val != 0:
                img = img.rotate(-self.rotate_angle_val, expand=True)
            if self.flip_h_var.get():
                img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if self.flip_v_var.get():
                img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

            thumb = img.copy()
            thumb.thumbnail((150, 150))
            self.preview_processed_tk = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
            self.preview_after_lbl.configure(image=self.preview_processed_tk, text='')
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

                out_path = os.path.join(out_dir, f'{bname}_edited{ext}')

                if do_favicon:
                    fav_sub = os.path.join(out_dir, f'{bname}_icons')
                    generate_favicons(img_path, fav_sub, base_name=bname)

                process_image(
                    input_path=img_path,
                    output_path=out_path,
                    scale_percent=scale_pct,
                    width=w_val,
                    height=h_val,
                    keep_aspect=keep_asp,
                    preset_name=preset,
                    brightness=bright,
                    contrast=contrast,
                    sharpness=sharp,
                    saturation=sat,
                    grayscale=gray,
                    rotate_angle=rot,
                    flip_h=fl_h,
                    flip_v=fl_v,
                    strip_metadata=strip_meta,
                    watermark_text=wm
                )

                if do_rembg:
                    self.img_status_lbl.configure(text=f'Removing Background ({idx+1}/{total})...')
                    remove_background(out_path, out_path)

                self.img_progress.set((idx + 1) / total)

            self.img_status_lbl.configure(text=f'Complete! Successfully processed {total} images.')
            messagebox.showinfo('Success', 'Image processing completed successfully!')
        except Exception as e:
            self.img_status_lbl.configure(text=f'Error: {str(e)}')
            messagebox.showerror('Error', f'Image processing failed:\n{str(e)}')
        finally:
            self.img_run_btn.configure(state='normal')
