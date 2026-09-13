import os
import sys
import subprocess
from tkinter import filedialog
import customtkinter as ctk

from gui.pdf_tab import PDFTab
from gui.video_tab import VideoTab
from gui.image_tab import ImageTab

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')

class OmniToolApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('OmniTool — 100% Local Media & PDF Suite')
        self.geometry('1120x780')
        self.minsize(980, 680)

        # Output folder default
        default_out = os.path.join(os.path.expanduser('~'), 'Desktop', 'OmniTool_Output')
        self.output_dir = default_out

        self._create_header()
        self._create_tabs()
        self._create_footer()

    def _create_header(self):
        header_frame = ctk.CTkFrame(self, corner_radius=0, height=55)
        header_frame.pack(fill='x', side='top')

        title_lbl = ctk.CTkLabel(
            header_frame,
            text='🛠️ OmniTool Local Suite',
            font=ctk.CTkFont(size=20, weight='bold')
        )
        title_lbl.pack(side='left', padx=20, pady=10)

        subtitle_lbl = ctk.CTkLabel(
            header_frame,
            text='100% Offline • PDF Power Tools • Video & Audio Converter • Image Editor',
            font=ctk.CTkFont(size=12),
            text_color='gray'
        )
        subtitle_lbl.pack(side='left', padx=10, pady=10)

        self.theme_btn = ctk.CTkSwitch(
            header_frame,
            text='Dark Mode',
            command=self._toggle_theme,
            font=ctk.CTkFont(size=12)
        )
        self.theme_btn.select()
        self.theme_btn.pack(side='right', padx=20, pady=10)

    def _toggle_theme(self):
        if self.theme_btn.get():
            ctk.set_appearance_mode('dark')
        else:
            ctk.set_appearance_mode('light')

    def _create_footer(self):
        footer_frame = ctk.CTkFrame(self, height=45, corner_radius=0)
        footer_frame.pack(fill='x', side='bottom', pady=(5, 0))

        out_lbl = ctk.CTkLabel(footer_frame, text='Output Directory:', font=ctk.CTkFont(size=12, weight='bold'))
        out_lbl.pack(side='left', padx=(20, 5), pady=8)

        self.out_path_lbl = ctk.CTkLabel(footer_frame, text=self.output_dir, font=ctk.CTkFont(size=11), text_color='gray')
        self.out_path_lbl.pack(side='left', padx=5, pady=8)

        browse_out_btn = ctk.CTkButton(
            footer_frame,
            text='Change Folder',
            width=110,
            height=28,
            command=self._choose_output_dir
        )
        browse_out_btn.pack(side='left', padx=10, pady=8)

        open_folder_btn = ctk.CTkButton(
            footer_frame,
            text='Open Output Folder',
            width=130,
            height=28,
            fg_color='#2b5b84',
            hover_color='#1f4463',
            command=self._open_output_folder
        )
        open_folder_btn.pack(side='right', padx=20, pady=8)

    def _choose_output_dir(self):
        chosen = filedialog.askdirectory(title='Select Output Directory', initialdir=self.output_dir)
        if chosen:
            self.output_dir = chosen
            self.out_path_lbl.configure(text=self.output_dir)

    def _open_output_folder(self):
        os.makedirs(self.output_dir, exist_ok=True)
        if sys.platform == 'win32':
            os.startfile(self.output_dir)
        elif sys.platform == 'darwin':
            subprocess.run(['open', self.output_dir])
        else:
            subprocess.run(['xdg-open', self.output_dir])

    def _create_tabs(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill='both', expand=True, padx=15, pady=10)

        tab_pdf = self.tabview.add('📄 PDF Tools')
        tab_video = self.tabview.add('🎬 Video & Audio')
        tab_image = self.tabview.add('🎨 Image Editor & Resizer')

        self.pdf_tab = PDFTab(self, tab_pdf)
        self.video_tab = VideoTab(self, tab_video)
        self.image_tab = ImageTab(self, tab_image)

if __name__ == '__main__':
    app = OmniToolApp()
    app.mainloop()
