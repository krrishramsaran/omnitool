import threading
from tkinter import messagebox
import customtkinter as ctk
from core.updater import download_and_install_update

class UpdateProgressDialog(ctk.CTkToplevel):
    def __init__(self, parent, download_url: str, version_tag: str):
        super().__init__(parent)
        self.title(f'Updating OmniTool to {version_tag}')
        self.geometry('420x220')
        self.resizable(False, False)
        self.download_url = download_url
        self.version_tag = version_tag

        self.lift()
        self.attributes('-topmost', True)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text=f'🚀 Downloading OmniTool {self.version_tag}...',
            font=ctk.CTkFont(size=15, weight='bold')
        ).pack(padx=20, pady=(20, 10))

        self.status_lbl = ctk.CTkLabel(
            self,
            text='Connecting to GitHub Releases...',
            text_color='gray',
            font=ctk.CTkFont(size=12)
        )
        self.status_lbl.pack(padx=20, pady=5)

        self.progress_bar = ctk.CTkProgressBar(self, width=340)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(padx=20, pady=15)

        self.pct_lbl = ctk.CTkLabel(self, text='0%', font=ctk.CTkFont(size=11, weight='bold'))
        self.pct_lbl.pack(padx=20, pady=(0, 15))

        threading.Thread(target=self._run_download, daemon=True).start()

    def _run_download(self):
        try:
            def on_progress(pct):
                self.progress_bar.set(pct)
                self.pct_lbl.configure(text=f'{int(pct * 100)}%')
                self.status_lbl.configure(text=f'Downloading: {int(pct * 100)}%')

            self.status_lbl.configure(text='Downloading update archive...')
            download_and_install_update(self.download_url, progress_callback=on_progress)
        except Exception as e:
            self.status_lbl.configure(text=f'Update failed: {str(e)}')
            messagebox.showerror('Update Failed', f'Could not complete auto-update:\n{str(e)}')
            self.destroy()
