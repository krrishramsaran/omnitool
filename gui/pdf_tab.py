import os
import copy
import threading
from tkinter import filedialog, messagebox, Canvas, colorchooser
import customtkinter as ctk
from PIL import Image, ImageTk
import pymupdf

from core.pdf_tools import (
    merge_pdfs, split_pdf, rotate_pdf, pdf_to_images,
    images_to_pdf, compress_pdf, add_text_to_pdf,
    add_watermark_text, protect_pdf, unlock_pdf,
    apply_annotations_to_pdf, add_highlight, add_underline, add_strikeout,
    redact_regions, search_and_redact, extract_page_text, extract_document_text,
    list_form_fields, fill_form_fields,
    reorder_pdf_pages, delete_pdf_pages, get_pdf_thumbnails,
    is_ocr_available, ocr_pdf
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
        self.pen_color = (0, 0, 0)
        self.pen_width = 2
        self.signature_img_path = None

        # Annotations store: { page_idx: { 'drawings': [], 'texts': [], 'signatures': [], 'highlights': [], 'underlines': [], 'strikeouts': [], 'redactions': [] } }
        self.annotations = {}
        self.current_stroke = []
        self.shape_start = None
        self.temp_rect_id = None

        # History for Undo / Redo
        self.history = []
        self.redo_stack = []

        # Interactive form fields
        self.detected_forms = []

        # Thumbnails and in-viewer search
        self.thumb_buttons = []
        self.sidebar_visible = True
        self.search_matches = []
        self.search_match_idx = -1

        self.canvas_img_tk = None
        self.render_scale = 1.0  # Scale between canvas pixels and PDF points

        self._setup_ui()

    def _setup_ui(self):
        # Top Mode Switch
        top_bar = ctk.CTkFrame(self.tab, height=45, fg_color='transparent')
        top_bar.pack(fill='x', padx=10, pady=(5, 5))

        self.mode_switch = ctk.CTkSegmentedButton(
            top_bar,
            values=['🎨 Visual Annotator & Signature Studio', '⚡ Batch Utilities (Merge, Split, OCR, etc.)'],
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
        # 1. Left Panel: Controls & Toolbars (width 260)
        ctrl_panel = ctk.CTkScrollableFrame(self.annotator_frame, width=260)
        ctrl_panel.pack(side='left', fill='both', expand=False, padx=(5, 2), pady=5)

        ctk.CTkLabel(ctrl_panel, text='PDF Document', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(5, 2))

        load_btn = ctk.CTkButton(ctrl_panel, text='📂 Open PDF to Edit', command=self._open_pdf_for_annotating, height=32)
        load_btn.pack(fill='x', padx=10, pady=5)

        self.doc_name_lbl = ctk.CTkLabel(ctrl_panel, text='No document loaded', text_color='gray', font=ctk.CTkFont(size=11), wraplength=240)
        self.doc_name_lbl.pack(anchor='w', padx=10, pady=(0, 8))

        # Page Navigation
        ctk.CTkLabel(ctrl_panel, text='Page Navigation', font=ctk.CTkFont(size=13, weight='bold')).pack(anchor='w', padx=10, pady=(5, 2))
        nav_row = ctk.CTkFrame(ctrl_panel, fg_color='transparent')
        nav_row.pack(fill='x', padx=10, pady=4)

        self.prev_btn = ctk.CTkButton(nav_row, text='◀ Prev', width=60, command=self._prev_page)
        self.prev_btn.pack(side='left')
        self.page_lbl = ctk.CTkLabel(nav_row, text='Page 0 of 0', font=ctk.CTkFont(size=12, weight='bold'))
        self.page_lbl.pack(side='left', expand=True)
        self.next_btn = ctk.CTkButton(nav_row, text='Next ▶', width=60, command=self._next_page)
        self.next_btn.pack(side='right')

        # Annotation Tools
        ctk.CTkLabel(ctrl_panel, text='Annotation Tools', font=ctk.CTkFont(size=13, weight='bold')).pack(anchor='w', padx=10, pady=(12, 2))

        self.tool_var = ctk.StringVar(value='pen')
        tool_frame = ctk.CTkFrame(ctrl_panel)
        tool_frame.pack(fill='x', padx=10, pady=4)

        ctk.CTkRadioButton(tool_frame, text='✏️ Freehand Pen / Draw', variable=self.tool_var, value='pen').pack(anchor='w', padx=10, pady=3)
        ctk.CTkRadioButton(tool_frame, text='🖐️ Pan / Hand Tool', variable=self.tool_var, value='hand').pack(anchor='w', padx=10, pady=3)
        ctk.CTkRadioButton(tool_frame, text='🖊️ Highlight Box', variable=self.tool_var, value='highlight').pack(anchor='w', padx=10, pady=3)
        ctk.CTkRadioButton(tool_frame, text='📏 Underline Area', variable=self.tool_var, value='underline').pack(anchor='w', padx=10, pady=3)
        ctk.CTkRadioButton(tool_frame, text='✂️ Strikeout Area', variable=self.tool_var, value='strikeout').pack(anchor='w', padx=10, pady=3)
        ctk.CTkRadioButton(tool_frame, text='⬛ Redact Area (Blackout)', variable=self.tool_var, value='redact').pack(anchor='w', padx=10, pady=3)
        ctk.CTkRadioButton(tool_frame, text='📝 Add Text Anywhere', variable=self.tool_var, value='text').pack(anchor='w', padx=10, pady=3)
        ctk.CTkRadioButton(tool_frame, text='🖋️ Place Signature / Stamp', variable=self.tool_var, value='signature').pack(anchor='w', padx=10, pady=3)

        # Pen & Color Options
        pen_box = ctk.CTkFrame(ctrl_panel)
        pen_box.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(pen_box, text='Color & Line Width:').pack(anchor='w', padx=10, pady=(5, 2))

        col_row = ctk.CTkFrame(pen_box, fg_color='transparent')
        col_row.pack(fill='x', padx=10, pady=3)
        self.color_combo = ctk.CTkComboBox(col_row, values=['Black', 'Red', 'Blue', 'Green', 'Gold', 'Yellow'], command=self._on_color_changed, width=120)
        self.color_combo.set('Black')
        self.color_combo.pack(side='left', padx=(0, 5))
        ctk.CTkButton(col_row, text='🎨 Color', width=75, command=self._pick_custom_color).pack(side='left')

        w_row = ctk.CTkFrame(pen_box, fg_color='transparent')
        w_row.pack(fill='x', padx=10, pady=(2, 6))
        ctk.CTkLabel(w_row, text='Width:').pack(side='left')
        self.width_combo = ctk.CTkComboBox(w_row, values=['1 px', '2 px', '4 px', '6 px'], width=85, command=self._on_width_changed)
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
        self.sig_lbl = ctk.CTkLabel(sig_box, text='No signature file chosen', text_color='gray', font=ctk.CTkFont(size=11), wraplength=230)
        self.sig_lbl.pack(anchor='w', padx=10, pady=(0, 6))

        # Undo / Redo Row
        hist_row = ctk.CTkFrame(ctrl_panel, fg_color='transparent')
        hist_row.pack(fill='x', padx=10, pady=(8, 3))
        self.undo_btn = ctk.CTkButton(hist_row, text='↩ Undo (Ctrl+Z)', width=110, fg_color='#495057', hover_color='#343a40', command=self._undo)
        self.undo_btn.pack(side='left', padx=(0, 5))
        self.redo_btn = ctk.CTkButton(hist_row, text='↪ Redo (Ctrl+Y)', width=110, fg_color='#495057', hover_color='#343a40', command=self._redo)
        self.redo_btn.pack(side='left')

        # Copy Text Button
        ctk.CTkButton(ctrl_panel, text='📋 Copy Page Text to Clipboard', fg_color='#2b5b84', hover_color='#1d3e5a', command=self._copy_page_text).pack(fill='x', padx=10, pady=3)

        # Interactive Form Button (Shown if forms detected)
        self.form_btn = ctk.CTkButton(
            ctrl_panel,
            text='📝 Fill Interactive Form (0 fields)',
            fg_color='#d35400',
            hover_color='#ba4a00',
            command=self._open_form_dialog
        )

        # Action Buttons
        ctk.CTkButton(ctrl_panel, text='🧹 Clear Page Annotations', fg_color='#6c757d', hover_color='#5a6268', command=self._clear_current_page_annots).pack(fill='x', padx=10, pady=(8, 4))

        self.save_annot_btn = ctk.CTkButton(
            ctrl_panel,
            text='💾 Save Annotated PDF',
            height=38,
            font=ctk.CTkFont(size=14, weight='bold'),
            fg_color='#1f8b4c',
            hover_color='#176d3b',
            command=self._save_annotated_pdf
        )
        self.save_annot_btn.pack(fill='x', padx=10, pady=(4, 15))

        # 2. Middle Panel: Page Thumbnail Sidebar (Collapsible)
        self.thumb_panel = ctk.CTkFrame(self.annotator_frame, width=135)
        self.thumb_panel.pack(side='left', fill='both', expand=False, padx=(2, 2), pady=5)

        thumb_top = ctk.CTkFrame(self.thumb_panel, fg_color='transparent')
        thumb_top.pack(fill='x', padx=6, pady=(6, 2))
        self.thumb_count_lbl = ctk.CTkLabel(thumb_top, text='Pages (0)', font=ctk.CTkFont(size=12, weight='bold'))
        self.thumb_count_lbl.pack(side='left')

        reorder_row = ctk.CTkFrame(self.thumb_panel, fg_color='transparent')
        reorder_row.pack(fill='x', padx=4, pady=2)
        ctk.CTkButton(reorder_row, text='▲', width=35, height=24, command=self._move_current_page_up).pack(side='left', padx=1)
        ctk.CTkButton(reorder_row, text='▼', width=35, height=24, command=self._move_current_page_down).pack(side='left', padx=1)
        ctk.CTkButton(reorder_row, text='🗑️', width=35, height=24, fg_color='#c0392b', hover_color='#962d22', command=self._delete_current_page).pack(side='left', padx=1)

        self.thumb_scroll = ctk.CTkScrollableFrame(self.thumb_panel, width=120)
        self.thumb_scroll.pack(fill='both', expand=True, padx=4, pady=(2, 6))

        # 3. Right Panel: Canvas & Viewer with Scrollbars
        self.viewer_panel = ctk.CTkFrame(self.annotator_frame)
        self.viewer_panel.pack(side='right', fill='both', expand=True, padx=(2, 5), pady=5)

        # Viewer Header Toolbar
        viewer_top = ctk.CTkFrame(self.viewer_panel, fg_color='transparent', height=36)
        viewer_top.pack(fill='x', padx=8, pady=(4, 4))

        # Left of top bar: Toggle sidebar button
        ctk.CTkButton(viewer_top, text='📑 Sidebar', width=75, height=26, command=self._toggle_thumb_sidebar).pack(side='left', padx=(0, 6))

        # Search Bar
        search_frame = ctk.CTkFrame(viewer_top, fg_color='transparent')
        search_frame.pack(side='left', padx=4)
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text='Search page text...', width=150, height=26)
        self.search_entry.pack(side='left', padx=(0, 2))
        self.search_entry.bind('<Return>', lambda e: self._search_text())
        ctk.CTkButton(search_frame, text='🔍', width=30, height=26, command=self._search_text).pack(side='left', padx=1)
        ctk.CTkButton(search_frame, text='◀', width=26, height=26, command=self._prev_search_match).pack(side='left', padx=1)
        ctk.CTkButton(search_frame, text='▶', width=26, height=26, command=self._next_search_match).pack(side='left', padx=1)
        self.search_lbl = ctk.CTkLabel(search_frame, text='0/0', width=45, font=ctk.CTkFont(size=11), text_color='gray')
        self.search_lbl.pack(side='left', padx=2)

        # Zoom Controls & Fit Presets
        zoom_row = ctk.CTkFrame(viewer_top, fg_color='transparent')
        zoom_row.pack(side='right', padx=2)

        ctk.CTkButton(zoom_row, text='Fit Width', width=65, height=26, command=self._fit_width).pack(side='left', padx=2)
        ctk.CTkButton(zoom_row, text='Fit Page', width=65, height=26, command=self._fit_page).pack(side='left', padx=2)
        ctk.CTkButton(zoom_row, text='🔍 -', width=34, height=26, command=self._zoom_out).pack(side='left', padx=1)
        self.zoom_lbl = ctk.CTkLabel(zoom_row, text='100%', width=42, font=ctk.CTkFont(size=11, weight='bold'))
        self.zoom_lbl.pack(side='left', padx=2)
        ctk.CTkButton(zoom_row, text='🔍 +', width=34, height=26, command=self._zoom_in).pack(side='left', padx=1)

        # Scrollable Viewport Container
        canvas_container = ctk.CTkFrame(self.viewer_panel, fg_color='#1c1c1c')
        canvas_container.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)

        self.canvas = Canvas(canvas_container, bg='#2b2b2b', highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky='nsew')

        self.v_scrollbar = ctk.CTkScrollbar(canvas_container, orientation='vertical', command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky='ns')

        self.h_scrollbar = ctk.CTkScrollbar(canvas_container, orientation='horizontal', command=self.canvas.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky='ew')

        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)

        # Canvas Mouse Bindings for Annotations & Scrolling / Panning
        self.canvas.bind('<Button-1>', self._on_canvas_click)
        self.canvas.bind('<B1-Motion>', self._on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_canvas_release)

        # Scrolling & Panning Bindings
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Shift-MouseWheel>', self._on_shift_mousewheel)
        self.canvas.bind('<ButtonPress-2>', self._on_pan_start)
        self.canvas.bind('<B2-Motion>', self._on_pan_drag)
        self.canvas.bind('<ButtonPress-3>', self._on_pan_start)
        self.canvas.bind('<B3-Motion>', self._on_pan_drag)

        # Keyboard hotkeys for undo / redo
        def _guarded_pdf_undo(e=None):
            try:
                if hasattr(self.app, 'tabview') and self.app.tabview.get() == '📄 PDF Tools':
                    focused = self.app.focus_get()
                    if focused and ('entry' in str(type(focused)).lower() or 'text' in str(type(focused)).lower()):
                        return
                    self._undo()
            except Exception:
                pass

        def _guarded_pdf_redo(e=None):
            try:
                if hasattr(self.app, 'tabview') and self.app.tabview.get() == '📄 PDF Tools':
                    focused = self.app.focus_get()
                    if focused and ('entry' in str(type(focused)).lower() or 'text' in str(type(focused)).lower()):
                        return
                    self._redo()
            except Exception:
                pass

        try:
            self.app.bind_all('<Control-z>', _guarded_pdf_undo)
            self.app.bind_all('<Control-y>', _guarded_pdf_redo)
        except Exception:
            pass

    # =========================================================================
    # SCROLLING, PANNING & ZOOMING VIEWPORT ENGINE
    # =========================================================================
    def _toggle_thumb_sidebar(self):
        if self.sidebar_visible:
            self.thumb_panel.pack_forget()
            self.sidebar_visible = False
        else:
            self.thumb_panel.pack(side='left', fill='both', expand=False, padx=(2, 2), pady=5, before=self.viewer_panel)
            self.sidebar_visible = True

    def _on_mousewheel(self, event):
        if self.canvas:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def _on_shift_mousewheel(self, event):
        if self.canvas:
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), 'units')

    def _on_pan_start(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def _on_pan_drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _fit_width(self):
        if not self.current_pdf or self.total_pages == 0:
            return
        cw = self.canvas.winfo_width()
        if cw < 60:
            cw = 750
        with pymupdf.open(self.current_pdf) as doc:
            pw = doc[self.current_page_idx].rect.width
        target_dpi = max(50, ((cw - 40) / pw) * 72)
        self.page_zoom = max(0.4, min(3.0, target_dpi / 120.0))
        self._render_current_page()

    def _fit_page(self):
        if not self.current_pdf or self.total_pages == 0:
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 60 or ch < 60:
            cw, ch = 750, 650
        with pymupdf.open(self.current_pdf) as doc:
            rect = doc[self.current_page_idx].rect
        zoom_w = (cw - 40) / rect.width * 72 / 120.0
        zoom_h = (ch - 40) / rect.height * 72 / 120.0
        self.page_zoom = max(0.4, min(3.0, min(zoom_w, zoom_h)))
        self._render_current_page()

    def _zoom_in(self):
        self.page_zoom = min(3.0, self.page_zoom + 0.25)
        self._render_current_page()

    def _zoom_out(self):
        self.page_zoom = max(0.4, self.page_zoom - 0.25)
        self._render_current_page()

    # =========================================================================
    # IN-VIEWER SEARCH ENGINE
    # =========================================================================
    def _search_text(self):
        if not self.current_pdf or self.total_pages == 0:
            return
        query = self.search_entry.get().strip()
        if not query:
            self.search_matches.clear()
            self.search_match_idx = -1
            self.search_lbl.configure(text='0/0', text_color='gray')
            self._render_current_page()
            return

        with pymupdf.open(self.current_pdf) as doc:
            page = doc[self.current_page_idx]
            self.search_matches = page.search_for(query)

        if not self.search_matches:
            self.search_match_idx = -1
            self.search_lbl.configure(text='0 matches', text_color='#e74c3c')
        else:
            self.search_match_idx = 0
            self.search_lbl.configure(text=f'1/{len(self.search_matches)}', text_color='#f1c40f')
            self._scroll_to_match(0)
        self._render_current_page()

    def _prev_search_match(self):
        if not self.search_matches:
            return
        self.search_match_idx = (self.search_match_idx - 1) % len(self.search_matches)
        self.search_lbl.configure(text=f'{self.search_match_idx + 1}/{len(self.search_matches)}')
        self._scroll_to_match(self.search_match_idx)
        self._render_current_page()

    def _next_search_match(self):
        if not self.search_matches:
            return
        self.search_match_idx = (self.search_match_idx + 1) % len(self.search_matches)
        self.search_lbl.configure(text=f'{self.search_match_idx + 1}/{len(self.search_matches)}')
        self._scroll_to_match(self.search_match_idx)
        self._render_current_page()

    def _scroll_to_match(self, idx):
        if 0 <= idx < len(self.search_matches):
            rect = self.search_matches[idx]
            match_cx = rect.x0 * self.render_scale
            match_cy = rect.y0 * self.render_scale
            try:
                sr = self.canvas.cget('scrollregion').split()
                if len(sr) == 4:
                    pw, ph = float(sr[2]), float(sr[3])
                    if pw > 0:
                        self.canvas.xview_moveto(max(0.0, (match_cx - 100) / pw))
                    if ph > 0:
                        self.canvas.yview_moveto(max(0.0, (match_cy - 100) / ph))
            except Exception:
                pass

    # =========================================================================
    # THUMBNAILS & PAGE REORDERING
    # =========================================================================
    def _load_thumbnails(self):
        for widget in self.thumb_scroll.winfo_children():
            widget.destroy()
        self.thumb_buttons.clear()
        if not self.current_pdf:
            self.thumb_count_lbl.configure(text='Pages (0)')
            return

        def bg_worker():
            try:
                thumbs = get_pdf_thumbnails(self.current_pdf, max_pages=100, dpi=25)
                self.app.after(0, lambda: self._populate_thumbnails(thumbs))
            except Exception:
                pass
        threading.Thread(target=bg_worker, daemon=True).start()

    def _populate_thumbnails(self, thumbs):
        for idx, img in enumerate(thumbs):
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            is_active = (idx == self.current_page_idx)
            btn = ctk.CTkButton(
                self.thumb_scroll,
                text=f'p. {idx + 1}',
                image=ctk_img,
                compound='top',
                width=105,
                height=img.height + 24,
                fg_color='#1f8b4c' if is_active else '#2a2a2a',
                hover_color='#333333',
                font=ctk.CTkFont(size=10, weight='bold'),
                command=lambda p=idx: self._goto_page(p)
            )
            btn.pack(pady=3, padx=2)
            self.thumb_buttons.append(btn)
        self.thumb_count_lbl.configure(text=f'Pages ({len(thumbs)})')

    def _goto_page(self, page_idx):
        if 0 <= page_idx < self.total_pages:
            self.current_page_idx = page_idx
            self.search_matches.clear()
            self.search_match_idx = -1
            self.search_lbl.configure(text='0/0', text_color='gray')
            self._update_active_thumb_highlight()
            self._render_current_page()

    def _update_active_thumb_highlight(self):
        for idx, btn in enumerate(self.thumb_buttons):
            if idx == self.current_page_idx:
                btn.configure(fg_color='#1f8b4c')
            else:
                btn.configure(fg_color='#2a2a2a')

    def _move_current_page_up(self):
        if not self.current_pdf or self.current_page_idx <= 0:
            return
        p = self.current_page_idx
        order = list(range(self.total_pages))
        order[p], order[p - 1] = order[p - 1], order[p]
        self._apply_page_reorder(order, new_current_idx=p - 1)

    def _move_current_page_down(self):
        if not self.current_pdf or self.current_page_idx >= self.total_pages - 1:
            return
        p = self.current_page_idx
        order = list(range(self.total_pages))
        order[p], order[p + 1] = order[p + 1], order[p]
        self._apply_page_reorder(order, new_current_idx=p + 1)

    def _delete_current_page(self):
        if not self.current_pdf or self.total_pages <= 1:
            messagebox.showwarning('Cannot Delete', 'Cannot delete page from a single-page document.')
            return
        if not messagebox.askyesno('Confirm Delete', f'Are you sure you want to delete Page {self.current_page_idx + 1}?'):
            return
        p = self.current_page_idx
        out_dir = self.app.output_dir
        bname = os.path.splitext(os.path.basename(self.current_pdf))[0]
        out_f = os.path.join(out_dir, f'{bname}_page_deleted.pdf')
        try:
            delete_pdf_pages(self.current_pdf, out_f, [p])
            self.current_pdf = out_f
            self.total_pages -= 1
            if self.current_page_idx >= self.total_pages:
                self.current_page_idx = self.total_pages - 1
            self._load_thumbnails()
            self._render_current_page()
            messagebox.showinfo('Page Deleted', f'Page removed. Updated document saved to:\n{out_f}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to delete page:\n{str(e)}')

    def _apply_page_reorder(self, order, new_current_idx):
        out_dir = self.app.output_dir
        bname = os.path.splitext(os.path.basename(self.current_pdf))[0]
        out_f = os.path.join(out_dir, f'{bname}_reordered.pdf')
        try:
            reorder_pdf_pages(self.current_pdf, out_f, order)
            self.current_pdf = out_f
            self.current_page_idx = new_current_idx
            self._load_thumbnails()
            self._render_current_page()
        except Exception as e:
            messagebox.showerror('Reorder Error', f'Failed to reorder pages:\n{str(e)}')

    # =========================================================================
    # HISTORY & COLOR PICKER
    # =========================================================================
    def _push_history(self):
        self.history.append(copy.deepcopy(self.annotations))
        if len(self.history) > 40:
            self.history.pop(0)
        self.redo_stack.clear()

    def _undo(self):
        if not self.history:
            return
        self.redo_stack.append(copy.deepcopy(self.annotations))
        self.annotations = self.history.pop()
        self._render_current_page()

    def _redo(self):
        if not self.redo_stack:
            return
        self.history.append(copy.deepcopy(self.annotations))
        self.annotations = self.redo_stack.pop()
        self._render_current_page()

    def _pick_custom_color(self):
        col = colorchooser.askcolor(title='Choose Annotation Color')
        if col and col[0]:
            r, g, b = int(col[0][0]), int(col[0][1]), int(col[0][2])
            self.pen_color = (r, g, b)
            self.color_combo.set('Custom')

    def _copy_page_text(self):
        if not self.current_pdf:
            messagebox.showwarning('No Document', 'Please open a PDF document first.')
            return
        txt = extract_page_text(self.current_pdf, self.current_page_idx + 1)
        if not txt.strip():
            messagebox.showinfo('Text Empty', 'No selectable text layer found on this page (it might be a scanned image).')
            return
        self.tab.clipboard_clear()
        self.tab.clipboard_append(txt)
        messagebox.showinfo('Text Copied', f'Copied {len(txt)} characters of page text to clipboard!')

    def _open_form_dialog(self):
        if not self.current_pdf or not self.detected_forms:
            return

        dialog = ctk.CTkToplevel(self.tab)
        dialog.title('Interactive Form Filling (AcroForms)')
        dialog.geometry('540x500')
        dialog.grab_set()

        ctk.CTkLabel(dialog, text='Interactive PDF Form Fields', font=ctk.CTkFont(size=15, weight='bold')).pack(anchor='w', padx=15, pady=(12, 4))
        ctk.CTkLabel(dialog, text='Edit field values below and click Save to generate a filled PDF.', font=ctk.CTkFont(size=11), text_color='gray').pack(anchor='w', padx=15, pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(dialog, height=340)
        scroll.pack(fill='both', expand=True, padx=15, pady=5)

        field_entries = {}
        for f in self.detected_forms:
            row = ctk.CTkFrame(scroll, fg_color='transparent')
            row.pack(fill='x', pady=4)
            name = f['name']
            ftype = f['type']
            curr_val = f['value']

            lbl_text = f'{name} ({ftype}, p.{f["page"]+1}):'
            ctk.CTkLabel(row, text=lbl_text, width=200, anchor='w', font=ctk.CTkFont(size=12)).pack(side='left')

            if ftype == 'CheckBox':
                var = ctk.BooleanVar(value=(curr_val in ('Yes', 'On', True)))
                chk = ctk.CTkCheckBox(row, text='', variable=var)
                chk.pack(side='left', padx=5)
                field_entries[name] = var
            else:
                entry = ctk.CTkEntry(row, width=260)
                entry.insert(0, str(curr_val))
                entry.pack(side='left', padx=5)
                field_entries[name] = entry

        def save_filled():
            out_dir = self.app.output_dir
            os.makedirs(out_dir, exist_ok=True)
            bname = os.path.splitext(os.path.basename(self.current_pdf))[0]
            out_file = os.path.join(out_dir, f'{bname}_filled.pdf')
            vals = {}
            for k, widget in field_entries.items():
                if isinstance(widget, ctk.BooleanVar):
                    vals[k] = widget.get()
                else:
                    vals[k] = widget.get()
            try:
                fill_form_fields(self.current_pdf, out_file, vals)
                dialog.destroy()
                messagebox.showinfo('Form Saved', f'Filled PDF saved to:\n{out_file}')
            except Exception as e:
                messagebox.showerror('Error', f'Failed to fill form fields:\n{str(e)}')

        btn_row = ctk.CTkFrame(dialog, fg_color='transparent')
        btn_row.pack(fill='x', padx=15, pady=12)
        ctk.CTkButton(btn_row, text='Save Filled PDF', fg_color='#1f8b4c', hover_color='#176d3b', command=save_filled).pack(side='right', padx=5)
        ctk.CTkButton(btn_row, text='Cancel', fg_color='#6c757d', hover_color='#5a6268', command=dialog.destroy).pack(side='right')

    def _open_pdf_for_annotating(self):
        f = filedialog.askopenfilename(title='Select PDF File to Annotate', filetypes=[('PDF Files', '*.pdf')])
        if f:
            self.current_pdf = f
            self.doc_name_lbl.configure(text=os.path.basename(f), text_color='white')
            with pymupdf.open(f) as doc:
                self.total_pages = len(doc)
            self.current_page_idx = 0
            self.annotations = {}
            self.history.clear()
            self.redo_stack.clear()
            self.search_matches.clear()
            self.search_match_idx = -1
            self.search_lbl.configure(text='0/0', text_color='gray')

            # Check for interactive forms
            try:
                self.detected_forms = list_form_fields(f)
                if self.detected_forms:
                    self.form_btn.configure(text=f'📝 Fill Form Fields ({len(self.detected_forms)} found)')
                    self.form_btn.pack(fill='x', padx=10, pady=3, after=self.undo_btn.master)
                else:
                    self.form_btn.pack_forget()
            except Exception:
                self.form_btn.pack_forget()

            self._load_thumbnails()
            self._render_current_page()

    def _prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.search_matches.clear()
            self.search_match_idx = -1
            self.search_lbl.configure(text='0/0', text_color='gray')
            self._update_active_thumb_highlight()
            self._render_current_page()

    def _next_page(self):
        if self.current_page_idx < self.total_pages - 1:
            self.current_page_idx += 1
            self.search_matches.clear()
            self.search_match_idx = -1
            self.search_lbl.configure(text='0/0', text_color='gray')
            self._update_active_thumb_highlight()
            self._render_current_page()

    # =========================================================================
    # CANVAS RENDERING
    # =========================================================================
    def _render_current_page(self):
        if not self.current_pdf or not os.path.exists(self.current_pdf):
            return

        self.page_lbl.configure(text=f'Page {self.current_page_idx + 1} of {self.total_pages}')
        self.zoom_lbl.configure(text=f'{int(self.page_zoom * 100)}%')

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

            # Draw highlights
            for hl in page_data.get('highlights', []):
                rx0 = hl['rect'][0] * self.render_scale
                ry0 = hl['rect'][1] * self.render_scale
                rx1 = hl['rect'][2] * self.render_scale
                ry1 = hl['rect'][3] * self.render_scale
                col_hex = '#{:02x}{:02x}{:02x}'.format(*hl.get('color', (255, 255, 0)))
                self.canvas.create_rectangle(rx0, ry0, rx1, ry1, fill=col_hex, stipple='gray50', outline='')

            # Draw underlines
            for ul in page_data.get('underlines', []):
                rx0 = ul['rect'][0] * self.render_scale
                ry1 = ul['rect'][3] * self.render_scale
                rx1 = ul['rect'][2] * self.render_scale
                col_hex = '#{:02x}{:02x}{:02x}'.format(*ul.get('color', (0, 0, 255)))
                self.canvas.create_line(rx0, ry1, rx1, ry1, fill=col_hex, width=max(2, int(2 * self.render_scale)))

            # Draw strikeouts
            for so in page_data.get('strikeouts', []):
                rx0 = so['rect'][0] * self.render_scale
                ry0 = so['rect'][1] * self.render_scale
                rx1 = so['rect'][2] * self.render_scale
                ry1 = so['rect'][3] * self.render_scale
                mid_y = (ry0 + ry1) / 2
                col_hex = '#{:02x}{:02x}{:02x}'.format(*so.get('color', (255, 0, 0)))
                self.canvas.create_line(rx0, mid_y, rx1, mid_y, fill=col_hex, width=max(2, int(2 * self.render_scale)))

            # Draw redactions
            for rd in page_data.get('redactions', []):
                rx0 = rd['rect'][0] * self.render_scale
                ry0 = rd['rect'][1] * self.render_scale
                rx1 = rd['rect'][2] * self.render_scale
                ry1 = rd['rect'][3] * self.render_scale
                self.canvas.create_rectangle(rx0, ry0, rx1, ry1, fill='#000000', outline='#ff3333', width=1)
                if (rx1 - rx0) > 40 and (ry1 - ry0) > 12:
                    self.canvas.create_text((rx0 + rx1) / 2, (ry0 + ry1) / 2, text='[REDACTED]', fill='#ffffff', font=('Arial', 8, 'bold'))

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

            # Draw search match highlights
            for s_idx, srect in enumerate(self.search_matches):
                rx0 = srect.x0 * self.render_scale
                ry0 = srect.y0 * self.render_scale
                rx1 = srect.x1 * self.render_scale
                ry1 = srect.y1 * self.render_scale
                is_active = (s_idx == self.search_match_idx)
                outline_col = '#e67e22' if is_active else '#f39c12'
                fill_col = '#fff3cd' if is_active else '#fffae6'
                self.canvas.create_rectangle(rx0, ry0, rx1, ry1, fill=fill_col, stipple='gray50', outline=outline_col, width=2 if is_active else 1)

    # =========================================================================
    # CANVAS INTERACTION HANDLERS
    # =========================================================================
    def _on_color_changed(self, choice):
        c_map = {
            'Black': (0, 0, 0),
            'Red': (220, 30, 30),
            'Blue': (30, 100, 220),
            'Green': (30, 160, 60),
            'Gold': (212, 175, 55),
            'Yellow': (255, 230, 0)
        }
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
        if tool == 'hand':
            self.canvas.scan_mark(event.x, event.y)
            return

        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        pdf_x = cx / self.render_scale
        pdf_y = cy / self.render_scale

        if self.current_page_idx not in self.annotations:
            self.annotations[self.current_page_idx] = {
                'drawings': [], 'texts': [], 'signatures': [],
                'highlights': [], 'underlines': [], 'strikeouts': [], 'redactions': []
            }

        if tool == 'pen':
            self.current_stroke = [(pdf_x, pdf_y)]
        elif tool in ('highlight', 'underline', 'strikeout', 'redact'):
            self.shape_start = (pdf_x, pdf_y, cx, cy)
            self.temp_rect_id = None
        elif tool == 'text':
            txt = self.text_entry.get().strip() or 'Annotation'
            fsize = 14
            try:
                fsize = int(self.fsize_entry.get().strip())
            except ValueError:
                pass
            self.annotations[self.current_page_idx]['texts'].append({
                'text': txt,
                'x': pdf_x,
                'y': pdf_y,
                'font_size': fsize,
                'color': self.pen_color
            })
            self._push_history()
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
            self._push_history()
            self._render_current_page()

    def _on_canvas_drag(self, event):
        if not self.current_pdf:
            return
        tool = self.tool_var.get()
        if tool == 'hand':
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            return

        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        pdf_x = cx / self.render_scale
        pdf_y = cy / self.render_scale

        if tool == 'pen':
            if self.current_stroke:
                last_x, last_y = self.current_stroke[-1]
                col_hex = '#{:02x}{:02x}{:02x}'.format(*self.pen_color)
                w = max(1, int(self.pen_width * self.render_scale))
                self.canvas.create_line(
                    last_x * self.render_scale, last_y * self.render_scale,
                    cx, cy,
                    fill=col_hex, width=w, capstyle='round', smooth=True
                )
                self.current_stroke.append((pdf_x, pdf_y))
        elif tool in ('highlight', 'underline', 'strikeout', 'redact') and self.shape_start:
            sx, sy, scx, scy = self.shape_start
            if self.temp_rect_id:
                self.canvas.delete(self.temp_rect_id)
            if tool == 'highlight':
                self.temp_rect_id = self.canvas.create_rectangle(scx, scy, cx, cy, fill='#ffff00', stipple='gray50', outline='#e6b800', width=1)
            elif tool == 'underline':
                self.temp_rect_id = self.canvas.create_line(scx, cy, cx, cy, fill='#0055ff', width=2)
            elif tool == 'strikeout':
                mid = (scy + cy) / 2
                self.temp_rect_id = self.canvas.create_line(scx, mid, cx, mid, fill='#ff0000', width=2)
            elif tool == 'redact':
                self.temp_rect_id = self.canvas.create_rectangle(scx, scy, cx, cy, fill='#000000', outline='#ff3333', width=1)

    def _on_canvas_release(self, event):
        if not self.current_pdf:
            return
        tool = self.tool_var.get()
        if tool == 'hand':
            return

        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        pdf_x = cx / self.render_scale
        pdf_y = cy / self.render_scale

        if tool == 'pen':
            if self.current_stroke and len(self.current_stroke) > 1:
                if self.current_page_idx not in self.annotations:
                    self.annotations[self.current_page_idx] = {'drawings': [], 'texts': [], 'signatures': [], 'highlights': [], 'underlines': [], 'strikeouts': [], 'redactions': []}
                self.annotations[self.current_page_idx]['drawings'].append({
                    'points': self.current_stroke,
                    'color': self.pen_color,
                    'width': self.pen_width
                })
                self.current_stroke = []
                self._push_history()
                self._render_current_page()
        elif tool in ('highlight', 'underline', 'strikeout', 'redact') and self.shape_start:
            sx, sy, _, _ = self.shape_start
            self.shape_start = None
            if self.temp_rect_id:
                self.canvas.delete(self.temp_rect_id)
                self.temp_rect_id = None

            x0, x1 = min(sx, pdf_x), max(sx, pdf_x)
            y0, y1 = min(sy, pdf_y), max(sy, pdf_y)
            if (x1 - x0) > 3 or (y1 - y0) > 3:
                if self.current_page_idx not in self.annotations:
                    self.annotations[self.current_page_idx] = {'drawings': [], 'texts': [], 'signatures': [], 'highlights': [], 'underlines': [], 'strikeouts': [], 'redactions': []}

                rect_tuple = (x0, y0, x1, y1)
                if tool == 'highlight':
                    self.annotations[self.current_page_idx]['highlights'].append({'rect': rect_tuple, 'color': (255, 255, 0)})
                elif tool == 'underline':
                    self.annotations[self.current_page_idx]['underlines'].append({'rect': rect_tuple, 'color': (0, 0, 255)})
                elif tool == 'strikeout':
                    self.annotations[self.current_page_idx]['strikeouts'].append({'rect': rect_tuple, 'color': (255, 0, 0)})
                elif tool == 'redact':
                    self.annotations[self.current_page_idx]['redactions'].append({'rect': rect_tuple, 'fill': (0, 0, 0)})

                self._push_history()
                self._render_current_page()

    def _clear_current_page_annots(self):
        if self.current_page_idx in self.annotations:
            self._push_history()
            self.annotations[self.current_page_idx] = {
                'drawings': [], 'texts': [], 'signatures': [],
                'highlights': [], 'underlines': [], 'strikeouts': [], 'redactions': []
            }
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
    # BATCH UTILITIES (Merge, Split, Rotate, Compress, Images to PDF, OCR, etc.)
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
            ('Search & Redact Sensitive Text', 'search_redact'),
            ('Extract All Text to .txt Document', 'extract_text'),
            ('OCR Scanned PDF (Make Searchable Text)', 'ocr'),
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
            ).pack(anchor='w', padx=15, pady=3)

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
        elif act == 'search_redact':
            ctk.CTkLabel(self.pdf_opts_frame, text='Search terms to permanently redact (comma-separated):').pack(anchor='w', padx=10, pady=(10, 2))
            self.pdf_redact_entry = ctk.CTkEntry(self.pdf_opts_frame, placeholder_text='e.g. SSN, Confidential, password')
            self.pdf_redact_entry.pack(fill='x', padx=10, pady=(0, 10))
        elif act == 'extract_text':
            ctk.CTkLabel(self.pdf_opts_frame, text='Extract full searchable text layer of all pages into clean .txt files.').pack(padx=10, pady=10)
        elif act == 'ocr':
            avail = is_ocr_available()
            status_text = '🟢 Tesseract OCR Engine Detected' if avail else '⚠️ Tesseract OCR Engine Not Detected'
            color = '#2ecc71' if avail else '#e67e22'
            ctk.CTkLabel(self.pdf_opts_frame, text=status_text, font=ctk.CTkFont(size=12, weight='bold'), text_color=color).pack(anchor='w', padx=10, pady=(10, 2))
            if not avail:
                ctk.CTkLabel(
                    self.pdf_opts_frame,
                    text='To enable OCR, install Tesseract via PowerShell:\nwinget install UB-Mannheim.TesseractOCR\nor download installer from GitHub.',
                    font=ctk.CTkFont(size=11), text_color='gray', justify='left'
                ).pack(anchor='w', padx=10, pady=(0, 10))
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
                    elif act == 'search_redact':
                        raw_terms = self.pdf_redact_entry.get().strip()
                        terms = [t.strip() for t in raw_terms.split(',') if t.strip()]
                        if not terms:
                            raise ValueError('Please enter at least one word/phrase to redact.')
                        out_f = os.path.join(out_dir, f'{bname}_redacted.pdf')
                        search_and_redact(f, out_f, terms)
                    elif act == 'extract_text':
                        out_f = os.path.join(out_dir, f'{bname}_extracted_text.txt')
                        extract_document_text(f, out_f)
                    elif act == 'ocr':
                        out_f = os.path.join(out_dir, f'{bname}_ocr.pdf')
                        ocr_pdf(f, out_f)
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
