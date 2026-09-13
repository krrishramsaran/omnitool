import os
import threading
from tkinter import filedialog, messagebox, Canvas
import customtkinter as ctk
from PIL import Image, ImageTk
import pymupdf

from core.pdf_tools import (
    merge_pdfs, split_pdf, rotate_pdf, pdf_to_images,
    images_to_pdf, compress_pdf, add_text_to_pdf,
    add_watermark_text, protect_pdf, unlock_pdf,
    apply_annotations_to_pdf
)

class PDFTab:
    def __init__(self, app, parent_tab):
        self.app = app
        self.tab = parent_tab
        self.pdf_files = []
        self.current_pdf = None
        self.current_page_idx = 0
        self.total_pages = 0
        self.page_zoom = 1.0
        self.active_tool = 'pen'  # 'pen', 'text', 'signature'
        self.pen_color = (0, 0, 0)
        self.pen_width = 2
        self.signature_img_path = None

        # Annotations store: { page_idx: { 'drawings': [], 'texts': [], 'signatures': [] } }
        self.annotations = {}
        self.current_stroke = []

        self.canvas_img_tk = None
        self.render_scale = 1.0  # Scale between canvas pixels and PDF points

        self._setup_ui()

    def _setup_ui(self):
        # Top Mode Switch
        top_bar = ctk.CTkFrame(self.tab, height=45, fg_color='transparent')
        top_bar.pack(fill='x', padx=10, pady=(5, 5))

        self.mode_switch = ctk.CTkSegmentedButton(
            top_bar,
            values=['🎨 Visual Annotator & Signature Studio', '⚡ Batch Utilities (Merge, Split, Compress)'],
            command=self._on_mode_change
        )
        self.mode_switch.set('🎨 Visual Annotator & Signature Studio')
        self.mode_switch.pack(side='left', padx=10)

        # Container frames
        self.annotator_frame = ctk.CTkFrame(self.tab, fg_color='transparent')
        self.batch_frame = ctk.CTkFrame(self.tab, fg_color='transparent')

        self._setup_annotator_ui()
        self._setup_batch_ui()

        self.annotator_frame.pack(fill='both', expand=True, padx=5, pady=5)

    def _on_mode_change(self, val):
        if 'Visual Annotator' in val:
            self.batch_frame.pack_forget()
            self.annotator_frame.pack(fill='both', expand=True, padx=5, pady=5)
        else:
            self.annotator_frame.pack_forget()
            self.batch_frame.pack(fill='both', expand=True, padx=5, pady=5)

    # =========================================================================
    # VISUAL ANNOTATOR & SIGNATURE STUDIO
    # =========================================================================
    def _setup_annotator_ui(self):
        # Left Panel: Controls & Toolbars
        ctrl_panel = ctk.CTkScrollableFrame(self.annotator_frame, width=280)
        ctrl_panel.pack(side='left', fill='both', expand=False, padx=(5, 5), pady=5)

        ctk.CTkLabel(ctrl_panel, text='PDF Document', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(5, 2))
        
        load_btn = ctk.CTkButton(ctrl_panel, text='📂 Open PDF to Edit', command=self._open_pdf_for_annotating, height=32)
        load_btn.pack(fill='x', padx=10, pady=5)

        self.doc_name_lbl = ctk.CTkLabel(ctrl_panel, text='No document loaded', text_color='gray', font=ctk.CTkFont(size=11), wraplength=250)
        self.doc_name_lbl.pack(anchor='w', padx=10, pady=(0, 10))

        # Page Navigation
        ctk.CTkLabel(ctrl_panel, text='Page Navigation', font=ctk.CTkFont(size=13, weight='bold')).pack(anchor='w', padx=10, pady=(5, 2))
        nav_row = ctk.CTkFrame(ctrl_panel, fg_color='transparent')
        nav_row.pack(fill='x', padx=10, pady=5)

        self.prev_btn = ctk.CTkButton(nav_row, text='◀ Prev', width=65, command=self._prev_page)
        self.prev_btn.pack(side='left')
        self.page_lbl = ctk.CTkLabel(nav_row, text='Page 0 of 0', font=ctk.CTkFont(size=12, weight='bold'))
        self.page_lbl.pack(side='left', expand=True)
        self.next_btn = ctk.CTkButton(nav_row, text='Next ▶', width=65, command=self._next_page)
        self.next_btn.pack(side='right')

        # Annotation Tools
        ctk.CTkLabel(ctrl_panel, text='Annotation Tools', font=ctk.CTkFont(size=13, weight='bold')).pack(anchor='w', padx=10, pady=(15, 2))

        self.tool_var = ctk.StringVar(value='pen')
        tool_frame = ctk.CTkFrame(ctrl_panel)
        tool_frame.pack(fill='x', padx=10, pady=5)

        ctk.CTkRadioButton(tool_frame, text='✏️ Freehand Pen / Draw', variable=self.tool_var, value='pen').pack(anchor='w', padx=10, pady=6)
        ctk.CTkRadioButton(tool_frame, text='📝 Add Text Anywhere', variable=self.tool_var, value='text').pack(anchor='w', padx=10, pady=6)
        ctk.CTkRadioButton(tool_frame, text='🖋️ Place Signature / Stamp', variable=self.tool_var, value='signature').pack(anchor='w', padx=10, pady=6)

        # Pen Options
        pen_box = ctk.CTkFrame(ctrl_panel)
        pen_box.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(pen_box, text='Pen Color & Width:').pack(anchor='w', padx=10, pady=(5, 2))
        
        self.color_combo = ctk.CTkComboBox(pen_box, values=['Black', 'Red', 'Blue', 'Green', 'Gold'], command=self._on_color_changed)
        self.color_combo.set('Black')
        self.color_combo.pack(fill='x', padx=10, pady=3)

        w_row = ctk.CTkFrame(pen_box, fg_color='transparent')
        w_row.pack(fill='x', padx=10, pady=(2, 6))
        ctk.CTkLabel(w_row, text='Width:').pack(side='left')
        self.width_combo = ctk.CTkComboBox(w_row, values=['1 px', '2 px', '4 px', '6 px'], width=90, command=self._on_width_changed)
        self.width_combo.set('2 px')
        self.width_combo.pack(side='left', padx=5)

        # Text Options
        text_box = ctk.CTkFrame(ctrl_panel)
        text_box.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(text_box, text='Text to Place on Click:').pack(anchor='w', padx=10, pady=(5, 2))
        self.text_entry = ctk.CTkEntry(text_box, placeholder_text='Click anywhere on PDF to paste')
        self.text_entry.insert(0, 'Approved / Signature')
        self.text_entry.pack(fill='x', padx=10, pady=3)

        t_row = ctk.CTkFrame(text_box, fg_color='transparent')
        t_row.pack(fill='x', padx=10, pady=(2, 6))
        ctk.CTkLabel(t_row, text='Font Size:').pack(side='left')
        self.fsize_entry = ctk.CTkEntry(t_row, width=60)
        self.fsize_entry.insert(0, '14')
        self.fsize_entry.pack(side='left', padx=5)

        # Signature Options
        sig_box = ctk.CTkFrame(ctrl_panel)
        sig_box.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(sig_box, text='Signature Image:').pack(anchor='w', padx=10, pady=(5, 2))
        self.sig_btn = ctk.CTkButton(sig_box, text='Browse Signature File', command=self._browse_signature_file, height=28)
        self.sig_btn.pack(fill='x', padx=10, pady=3)
        self.sig_lbl = ctk.CTkLabel(sig_box, text='No signature file chosen', text_color='gray', font=ctk.CTkFont(size=11), wraplength=240)
        self.sig_lbl.pack(anchor='w', padx=10, pady=(0, 6))

        # Action Buttons
        ctk.CTkButton(ctrl_panel, text='🧹 Clear Page Annotations', fg_color='#6c757d', hover_color='#5a6268', command=self._clear_current_page_annots).pack(fill='x', padx=10, pady=(15, 5))

        self.save_annot_btn = ctk.CTkButton(
            ctrl_panel,
            text='💾 Save Annotated PDF',
            height=40,
            font=ctk.CTkFont(size=14, weight='bold'),
            fg_color='#1f8b4c',
            hover_color='#176d3b',
            command=self._save_annotated_pdf
        )
        self.save_annot_btn.pack(fill='x', padx=10, pady=(5, 15))

        # Right Panel: Canvas & Viewer
        viewer_panel = ctk.CTkFrame(self.annotator_frame)
        viewer_panel.pack(side='right', fill='both', expand=True, padx=(5, 5), pady=5)

        viewer_top = ctk.CTkFrame(viewer_panel, fg_color='transparent', height=35)
        viewer_top.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(viewer_top, text='Interactive Page View (Click/Draw anywhere)', font=ctk.CTkFont(size=13, weight='bold')).pack(side='left')

        zoom_row = ctk.CTkFrame(viewer_top, fg_color='transparent')
        zoom_row.pack(side='right')
        ctk.CTkButton(zoom_row, text='🔍 -', width=45, command=self._zoom_out).pack(side='left', padx=2)
        ctk.CTkButton(zoom_row, text='🔍 +', width=45, command=self._zoom_in).pack(side='left', padx=2)

        # Scrollable Canvas
        self.canvas = Canvas(viewer_panel, bg='#2b2b2b', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # Bindings
        self.canvas.bind('<Button-1>', self._on_canvas_click)
        self.canvas.bind('<B1-Motion>', self._on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_canvas_release)

    def _open_pdf_for_annotating(self):
        f = filedialog.askopenfilename(title='Select PDF File to Annotate', filetypes=[('PDF Files', '*.pdf')])
        if f:
            self.current_pdf = f
            self.doc_name_lbl.configure(text=os.path.basename(f), text_color='white')
            with pymupdf.open(f) as doc:
                self.total_pages = len(doc)
            self.current_page_idx = 0
            self.annotations = {}
            self._render_current_page()

    def _prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            self._render_current_page()

    def _next_page(self):
        if self.current_page_idx < self.total_pages - 1:
            self.current_page_idx += 1
            self._render_current_page()

    def _zoom_in(self):
        self.page_zoom = min(2.5, self.page_zoom + 0.25)
        self._render_current_page()

    def _zoom_out(self):
        self.page_zoom = max(0.5, self.page_zoom - 0.25)
        self._render_current_page()

    def _render_current_page(self):
        if not self.current_pdf or not os.path.exists(self.current_pdf):
            return
        
        self.page_lbl.configure(text=f'Page {self.current_page_idx + 1} of {self.total_pages}')
        
        with pymupdf.open(self.current_pdf) as doc:
            page = doc[self.current_page_idx]
            rect = page.rect
            dpi = int(120 * self.page_zoom)
            pix = page.get_pixmap(dpi=dpi)
            
            img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            self.canvas_img_tk = ImageTk.PhotoImage(img)

            self.render_scale = pix.width / rect.width  # pixels per point

            self.canvas.delete('all')
            self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
            self.canvas.create_image(0, 0, anchor='nw', image=self.canvas_img_tk)

            # Redraw existing annotations for this page on canvas
            page_data = self.annotations.get(self.current_page_idx, {})
            # Draw strokes
            for s in page_data.get('drawings', []):
                pts = s.get('points', [])
                col_hex = '#{:02x}{:02x}{:02x}'.format(*s.get('color', (0,0,0)))
                w = int(s.get('width', 2) * self.render_scale)
                for i in range(len(pts) - 1):
                    x1, y1 = pts[i][0] * self.render_scale, pts[i][1] * self.render_scale
                    x2, y2 = pts[i+1][0] * self.render_scale, pts[i+1][1] * self.render_scale
                    self.canvas.create_line(x1, y1, x2, y2, fill=col_hex, width=max(1, w), capstyle='round', smooth=True)

            # Draw texts
            for t in page_data.get('texts', []):
                tx = t['x'] * self.render_scale
                ty = t['y'] * self.render_scale
                col_hex = '#{:02x}{:02x}{:02x}'.format(*t.get('color', (0,0,0)))
                sz = int(t.get('font_size', 14) * self.page_zoom)
                self.canvas.create_text(tx, ty, text=t['text'], fill=col_hex, font=('Arial', sz, 'bold'), anchor='nw')

            # Draw signatures
            for sig in page_data.get('signatures', []):
                sx = sig['x'] * self.render_scale
                sy = sig['y'] * self.render_scale
                sw = sig['width'] * self.render_scale
                sh = sig['height'] * self.render_scale
                self.canvas.create_rectangle(sx, sy, sx + sw, sy + sh, outline='#1f8b4c', width=2, dash=(4, 2))
                self.canvas.create_text(sx + 5, sy + 5, text='[Signature / Stamp]', fill='#1f8b4c', anchor='nw', font=('Arial', 10, 'bold'))

    def _on_color_changed(self, choice):
        c_map = {'Black': (0, 0, 0), 'Red': (220, 30, 30), 'Blue': (30, 100, 220), 'Green': (30, 160, 60), 'Gold': (212, 175, 55)}
        self.pen_color = c_map.get(choice, (0, 0, 0))

    def _on_width_changed(self, choice):
        try:
            self.pen_width = int(choice.split()[0])
        except Exception:
            self.pen_width = 2

    def _browse_signature_file(self):
        f = filedialog.askopenfilename(title='Select Signature Image', filetypes=[('Images', '*.png;*.jpg;*.jpeg')])
        if f:
            self.signature_img_path = f
            self.sig_lbl.configure(text=os.path.basename(f), text_color='white')
            self.tool_var.set('signature')

    def _on_canvas_click(self, event):
        if not self.current_pdf:
            return
        
        tool = self.tool_var.get()
        pdf_x = event.x / self.render_scale
        pdf_y = event.y / self.render_scale

        if self.current_page_idx not in self.annotations:
            self.annotations[self.current_page_idx] = {'drawings': [], 'texts': [], 'signatures': []}

        if tool == 'pen':
            self.current_stroke = [(pdf_x, pdf_y)]
        elif tool == 'text':
            txt = self.text_entry.get().strip() or 'Annotation'
            fsize = int(self.fsize_entry.get().strip() or '14')
            self.annotations[self.current_page_idx]['texts'].append({
                'text': txt,
                'x': pdf_x,
                'y': pdf_y,
                'font_size': fsize,
                'color': self.pen_color
            })
            self._render_current_page()
        elif tool == 'signature':
            if not self.signature_img_path or not os.path.exists(self.signature_img_path):
                messagebox.showwarning('No Signature Image', 'Please browse and choose a signature image first.')
                return
            self.annotations[self.current_page_idx]['signatures'].append({
                'image_path': self.signature_img_path,
                'x': pdf_x,
                'y': pdf_y,
                'width': 120,
                'height': 50
            })
            self._render_current_page()

    def _on_canvas_drag(self, event):
        if not self.current_pdf or self.tool_var.get() != 'pen':
            return
        
        pdf_x = event.x / self.render_scale
        pdf_y = event.y / self.render_scale

        if self.current_stroke:
            last_x, last_y = self.current_stroke[-1]
            col_hex = '#{:02x}{:02x}{:02x}'.format(*self.pen_color)
            w = max(1, int(self.pen_width * self.render_scale))
            self.canvas.create_line(
                last_x * self.render_scale, last_y * self.render_scale,
                event.x, event.y,
                fill=col_hex, width=w, capstyle='round', smooth=True
            )
            self.current_stroke.append((pdf_x, pdf_y))

    def _on_canvas_release(self, event):
        if not self.current_pdf or self.tool_var.get() != 'pen':
            return
        if self.current_stroke and len(self.current_stroke) > 1:
            if self.current_page_idx not in self.annotations:
                self.annotations[self.current_page_idx] = {'drawings': [], 'texts': [], 'signatures': []}
            self.annotations[self.current_page_idx]['drawings'].append({
                'points': self.current_stroke,
                'color': self.pen_color,
                'width': self.pen_width
            })
            self.current_stroke = []

    def _clear_current_page_annots(self):
        if self.current_page_idx in self.annotations:
            self.annotations[self.current_page_idx] = {'drawings': [], 'texts': [], 'signatures': []}
            self._render_current_page()

    def _save_annotated_pdf(self):
        if not self.current_pdf:
            messagebox.showwarning('No Document', 'Please open a PDF document first.')
            return

        out_dir = self.app.output_dir
        os.makedirs(out_dir, exist_ok=True)
        bname = os.path.splitext(os.path.basename(self.current_pdf))[0]
        out_file = os.path.join(out_dir, f'{bname}_annotated.pdf')

        try:
            apply_annotations_to_pdf(self.current_pdf, out_file, self.annotations)
            messagebox.showinfo('Saved Successfully', f'Annotated PDF saved to:\n{out_file}')
        except Exception as e:
            messagebox.showerror('Save Error', f'Failed to save annotated PDF:\n{str(e)}')

    # =========================================================================
    # BATCH UTILITIES (Merge, Split, Rotate, Compress, Images to PDF, etc.)
    # =========================================================================
    def _setup_batch_ui(self):
        left_frame = ctk.CTkFrame(self.batch_frame, width=380)
        left_frame.pack(side='left', fill='both', expand=False, padx=(5, 5), pady=5)

        ctk.CTkLabel(left_frame, text='Selected PDF / Image Files', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(10, 5))

        btn_row = ctk.CTkFrame(left_frame, fg_color='transparent')
        btn_row.pack(fill='x', padx=10, pady=5)
        ctk.CTkButton(btn_row, text='+ Add PDFs', width=110, command=self._add_pdf_files).pack(side='left', padx=(0, 5))
        ctk.CTkButton(btn_row, text='+ Add Images', width=110, command=self._add_images_for_pdf).pack(side='left', padx=5)
        ctk.CTkButton(btn_row, text='Clear', width=70, fg_color='#6c757d', hover_color='#5a6268', command=self._clear_pdf_files).pack(side='right')

        self.pdf_listbox = ctk.CTkTextbox(left_frame, height=350, state='disabled')
        self.pdf_listbox.pack(fill='both', expand=True, padx=10, pady=5)

        self.pdf_count_lbl = ctk.CTkLabel(left_frame, text='0 files selected', text_color='gray', font=ctk.CTkFont(size=11))
        self.pdf_count_lbl.pack(anchor='w', padx=10, pady=(2, 10))

        # Right panel: Operations
        right_frame = ctk.CTkScrollableFrame(self.batch_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 5), pady=5)

        ctk.CTkLabel(right_frame, text='Choose Batch Operation', font=ctk.CTkFont(size=16, weight='bold')).pack(anchor='w', padx=10, pady=(5, 10))

        self.pdf_action = ctk.StringVar(value='merge')

        actions = [
            ('Merge Selected PDFs into One Document', 'merge'),
            ('Split / Extract Pages (e.g. 1-3, 5)', 'split'),
            ('Rotate Pages (90°, 180°, 270°)', 'rotate'),
            ('Images to PDF (Stitch photos into single PDF)', 'images_to_pdf'),
            ('PDF to Images (Extract pages as PNG/JPG)', 'pdf_to_images'),
            ('Compress PDF (Reduce file size for email)', 'compress'),
            ('Add Watermark Text Across Pages', 'watermark'),
            ('Protect with Password (AES-256)', 'protect'),
            ('Unlock / Decrypt Password-Protected PDF', 'unlock'),
        ]

        for text, val in actions:
            ctk.CTkRadioButton(
                right_frame,
                text=text,
                variable=self.pdf_action,
                value=val,
                command=self._update_opts_ui
            ).pack(anchor='w', padx=15, pady=4)

        self.pdf_opts_frame = ctk.CTkFrame(right_frame)
        self.pdf_opts_frame.pack(fill='x', padx=10, pady=15)
        self._update_opts_ui()

        self.pdf_progress = ctk.CTkProgressBar(right_frame)
        self.pdf_progress.set(0)
        self.pdf_progress.pack(fill='x', padx=10, pady=(15, 5))

        self.pdf_status_lbl = ctk.CTkLabel(right_frame, text='Ready', font=ctk.CTkFont(size=12))
        self.pdf_status_lbl.pack(anchor='w', padx=10, pady=2)

        self.pdf_run_btn = ctk.CTkButton(
            right_frame,
            text='🚀 Execute Batch Task',
            height=40,
            font=ctk.CTkFont(size=14, weight='bold'),
            fg_color='#1f8b4c',
            hover_color='#176d3b',
            command=self._run_task_thread
        )
        self.pdf_run_btn.pack(fill='x', padx=10, pady=10)

    def _update_opts_ui(self):
        for widget in self.pdf_opts_frame.winfo_children():
            widget.destroy()

        act = self.pdf_action.get()
        if act == 'split':
            ctk.CTkLabel(self.pdf_opts_frame, text='Page range to extract (blank to split all pages):').pack(anchor='w', padx=10, pady=(10, 2))
            self.pdf_split_entry = ctk.CTkEntry(self.pdf_opts_frame, placeholder_text='e.g. 1-3, 5')
            self.pdf_split_entry.pack(fill='x', padx=10, pady=(0, 10))
        elif act == 'rotate':
            ctk.CTkLabel(self.pdf_opts_frame, text='Rotation Angle:').pack(anchor='w', padx=10, pady=(10, 2))
            self.pdf_rotate_combo = ctk.CTkComboBox(self.pdf_opts_frame, values=['90', '180', '270'])
            self.pdf_rotate_combo.set('90')
            self.pdf_rotate_combo.pack(anchor='w', padx=10, pady=(0, 10))
        elif act == 'pdf_to_images':
            ctk.CTkLabel(self.pdf_opts_frame, text='Output Image Format:').pack(anchor='w', padx=10, pady=(10, 2))
            self.pdf_img_fmt = ctk.CTkSegmentedButton(self.pdf_opts_frame, values=['PNG', 'JPG'])
            self.pdf_img_fmt.set('PNG')
            self.pdf_img_fmt.pack(anchor='w', padx=10, pady=(0, 10))
        elif act == 'compress':
            ctk.CTkLabel(self.pdf_opts_frame, text='Max Image Dimension:').pack(anchor='w', padx=10, pady=(10, 2))
            self.pdf_comp_dim = ctk.CTkComboBox(self.pdf_opts_frame, values=['800 (Max Compression)', '1200 (Balanced)', '1600 (High Quality)'])
            self.pdf_comp_dim.set('1200 (Balanced)')
            self.pdf_comp_dim.pack(anchor='w', padx=10, pady=(0, 10))
        elif act == 'watermark':
            ctk.CTkLabel(self.pdf_opts_frame, text='Watermark Text:').pack(anchor='w', padx=10, pady=(10, 2))
            self.pdf_wm_entry = ctk.CTkEntry(self.pdf_opts_frame, placeholder_text='e.g. CONFIDENTIAL')
            self.pdf_wm_entry.insert(0, 'CONFIDENTIAL')
            self.pdf_wm_entry.pack(fill='x', padx=10, pady=(0, 10))
        elif act in ('protect', 'unlock'):
            ctk.CTkLabel(self.pdf_opts_frame, text='Password:').pack(anchor='w', padx=10, pady=(10, 2))
            self.pdf_pw_entry = ctk.CTkEntry(self.pdf_opts_frame, show='*')
            self.pdf_pw_entry.pack(fill='x', padx=10, pady=(0, 10))
        else:
            ctk.CTkLabel(self.pdf_opts_frame, text='Ready to process selected files in order.').pack(padx=10, pady=10)

    def _add_pdf_files(self):
        files = filedialog.askopenfilenames(title='Select PDF Files', filetypes=[('PDF Files', '*.pdf')])
        if files:
            self.pdf_files.extend(files)
            self._update_listbox()

    def _add_images_for_pdf(self):
        files = filedialog.askopenfilenames(
            title='Select Images to convert to PDF',
            filetypes=[('Images', '*.png;*.jpg;*.jpeg;*.webp;*.bmp')]
        )
        if files:
            self.pdf_files.extend(files)
            self._update_listbox()

    def _clear_pdf_files(self):
        self.pdf_files.clear()
        self._update_listbox()

    def _update_listbox(self):
        self.pdf_listbox.configure(state='normal')
        self.pdf_listbox.delete('1.0', 'end')
        for i, f in enumerate(self.pdf_files):
            self.pdf_listbox.insert('end', f'{i+1}. {os.path.basename(f)}\n')
        self.pdf_listbox.configure(state='disabled')
        self.pdf_count_lbl.configure(text=f'{len(self.pdf_files)} files selected')

    def _run_task_thread(self):
        if not self.pdf_files:
            messagebox.showwarning('No Files', 'Please select at least one PDF or image file first.')
            return
        threading.Thread(target=self._execute_task, daemon=True).start()

    def _execute_task(self):
        self.pdf_run_btn.configure(state='disabled')
        self.pdf_progress.set(0.1)
        out_dir = self.app.output_dir
        os.makedirs(out_dir, exist_ok=True)
        act = self.pdf_action.get()

        try:
            if act == 'merge':
                self.pdf_status_lbl.configure(text='Merging PDFs...')
                out_file = os.path.join(out_dir, 'merged_document.pdf')
                merge_pdfs(self.pdf_files, out_file)
                self.pdf_status_lbl.configure(text=f'Done! Saved: {os.path.basename(out_file)}')
            elif act == 'images_to_pdf':
                self.pdf_status_lbl.configure(text='Stitching images to PDF...')
                out_file = os.path.join(out_dir, 'stitched_images.pdf')
                images_to_pdf(self.pdf_files, out_file)
                self.pdf_status_lbl.configure(text=f'Done! Saved: {os.path.basename(out_file)}')
            else:
                total = len(self.pdf_files)
                for idx, f in enumerate(self.pdf_files):
                    bname = os.path.splitext(os.path.basename(f))[0]
                    self.pdf_status_lbl.configure(text=f'Processing ({idx+1}/{total}): {os.path.basename(f)}')

                    if act == 'split':
                        rng = self.pdf_split_entry.get().strip() or None
                        split_pdf(f, out_dir, rng)
                    elif act == 'rotate':
                        deg = int(self.pdf_rotate_combo.get())
                        out_f = os.path.join(out_dir, f'{bname}_rotated.pdf')
                        rotate_pdf(f, out_f, angle=deg)
                    elif act == 'pdf_to_images':
                        fmt = self.pdf_img_fmt.get().lower()
                        pdf_to_images(f, out_dir, fmt=fmt)
                    elif act == 'compress':
                        dim_map = {'800 (Max Compression)': 800, '1200 (Balanced)': 1200, '1600 (High Quality)': 1600}
                        dim = dim_map.get(self.pdf_comp_dim.get(), 1200)
                        out_f = os.path.join(out_dir, f'{bname}_compressed.pdf')
                        compress_pdf(f, out_f, max_image_dimension=dim)
                    elif act == 'watermark':
                        wm = self.pdf_wm_entry.get().strip() or 'CONFIDENTIAL'
                        out_f = os.path.join(out_dir, f'{bname}_watermarked.pdf')
                        add_watermark_text(f, out_f, watermark_text=wm)
                    elif act == 'protect':
                        pw = self.pdf_pw_entry.get().strip()
                        if not pw:
                            raise ValueError('Please enter a password.')
                        out_f = os.path.join(out_dir, f'{bname}_protected.pdf')
                        protect_pdf(f, out_f, password=pw)
                    elif act == 'unlock':
                        pw = self.pdf_pw_entry.get().strip()
                        out_f = os.path.join(out_dir, f'{bname}_unlocked.pdf')
                        unlock_pdf(f, out_f, password=pw)

                    self.pdf_progress.set((idx + 1) / total)

                self.pdf_status_lbl.configure(text=f'Complete! Processed {total} files.')

            self.pdf_progress.set(1.0)
            messagebox.showinfo('Success', 'PDF operation completed successfully!')
        except Exception as e:
            self.pdf_status_lbl.configure(text=f'Error: {str(e)}')
            messagebox.showerror('Error', f'Failed to process PDF:\n{str(e)}')
        finally:
            self.pdf_run_btn.configure(state='normal')
