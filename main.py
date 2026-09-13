import os
import sys
import threading
import subprocess
from tkinter import filedialog, messagebox
import customtkinter as ctk

from gui.pdf_tab import PDFTab
from gui.video_tab import VideoTab
from gui.image_tab import ImageTab
from gui.update_dialog import UpdateProgressDialog
from core.updater import CURRENT_VERSION, check_for_updates

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')

class OmniToolApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f'OmniTool v{CURRENT_VERSION} — 100% Local Media & PDF Suite')
        self.geometry('1120x780')
        self.minsize(980, 680)

        # Output folder default
        default_out = os.path.join(os.path.expanduser('~'), 'Desktop', 'OmniTool_Output')
        self.output_dir = default_out

        self._create_header()
        self._create_update_banner()
        self._create_tabs()
        self._create_footer()

        # Start silent background update check
        threading.Thread(target=self._check_updates_background, daemon=True).start()

    def _create_header(self):
        header_frame = ctk.CTkFrame(self, corner_radius=0, height=55)
        header_frame.pack(fill='x', side='top')

        title_lbl = ctk.CTkLabel(
            header_frame,
            text='🛠️ OmniTool Local Suite',
            font=ctk.CTkFont(size=20, weight='bold')
        )
        title_lbl.pack(side='left', padx=20, pady=10)

        ver_badge = ctk.CTkLabel(
            header_frame,
            text=f'v{CURRENT_VERSION}',
            font=ctk.CTkFont(size=11, weight='bold'),
            fg_color='#1f4463',
            corner_radius=6,
            text_color='#88c0d0'
        )
        ver_badge.pack(side='left', padx=(0, 10), pady=12)

        subtitle_lbl = ctk.CTkLabel(
            header_frame,
            text='100% Offline • PDF Visual Studio • Video Timeline • Image Resizer',
            font=ctk.CTkFont(size=12),
            text_color='gray'
        )
        subtitle_lbl.pack(side='left', padx=5, pady=10)

        # Check updates button
        check_up_btn = ctk.CTkButton(
            header_frame,
            text='🔄 Check Updates',
            width=110,
            height=26,
            fg_color='#2b3a4a',
            hover_color='#1f2b38',
            font=ctk.CTkFont(size=11),
            command=self._manual_check_updates
        )
        check_up_btn.pack(side='right', padx=15, pady=10)

        # Theme toggle
        self.theme_btn = ctk.CTkSwitch(
            header_frame,
            text='Dark',
            command=self._toggle_theme,
            font=ctk.CTkFont(size=12)
        )
        self.theme_btn.select()
        self.theme_btn.pack(side='right', padx=10, pady=10)

    def _create_update_banner(self):
        self.banner_frame = ctk.CTkFrame(self, fg_color='#1f472e', corner_radius=0, height=38)
        # Unpacked by default, packed when update is detected
        self.banner_lbl = ctk.CTkLabel(
            self.banner_frame,
            text='✨ A new update is available!',
            font=ctk.CTkFont(size=12, weight='bold'),
            text_color='#70e090'
        )
        self.banner_lbl.pack(side='left', padx=20, pady=6)

        self.banner_update_btn = ctk.CTkButton(
            self.banner_frame,
            text='⚡ Update Now',
            width=100,
            height=26,
            fg_color='#2fa554',
            hover_color='#238241',
            font=ctk.CTkFont(size=11, weight='bold')
        )
        self.banner_update_btn.pack(side='left', padx=10, pady=6)

        dismiss_btn = ctk.CTkButton(
            self.banner_frame,
            text='✕',
            width=28,
            height=26,
            fg_color='transparent',
            hover_color='#163823',
            command=lambda: self.banner_frame.pack_forget()
        )
        dismiss_btn.pack(side='right', padx=15, pady=6)

    def _check_updates_background(self):
        token = None
        # Try finding gh token if available locally
        try:
            gh_out = subprocess.check_output(['C:\\Program Files\\GitHub CLI\\gh.exe', 'auth', 'token'], text=True).strip()
            if gh_out:
                token = gh_out
        except Exception:
            pass

        info = check_for_updates(token)
        if info.get('has_update'):
            self.after(500, lambda: self._show_update_notification(info))

    def _show_update_notification(self, info: dict):
        new_v = info.get('latest_version', 'latest')
        self.banner_lbl.configure(text=f'🎉 OmniTool {new_v} is available! Update now to get the latest features.')
        self.banner_update_btn.configure(command=lambda: self._start_update_process(info))
        self.banner_frame.pack(fill='x', side='top', after=self.winfo_children()[0])

    def _manual_check_updates(self):
        token = None
        try:
            gh_out = subprocess.check_output(['C:\\Program Files\\GitHub CLI\\gh.exe', 'auth', 'token'], text=True).strip()
            if gh_out:
                token = gh_out
        except Exception:
            pass

        info = check_for_updates(token)
        if info.get('has_update'):
            self._show_update_notification(info)
            latest = info.get('latest_version')
            messagebox.showinfo('Update Available', f'A new version {latest} is available!')
        elif 'error' in info:
            err = info.get('error')
            messagebox.showwarning('Update Check', f'Could not check for updates:\n{err}')
        else:
            messagebox.showinfo('Up to Date', f'OmniTool is already up to date! (v{CURRENT_VERSION})')

    def _start_update_process(self, info: dict):
        d_url = info.get('download_url')
        if not d_url:
            messagebox.showerror('Update Error', 'Download link could not be found for the release.')
            return
        UpdateProgressDialog(self, d_url, info.get('latest_version', 'Update'))

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
