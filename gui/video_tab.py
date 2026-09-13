import os
import time
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

from core.video_tools import (
    extract_video_frame, trim_video, merge_videos, merge_audios,
    replace_video_audio, video_to_gif, compress_video_target_size,
    extract_audio, mute_video, change_video_speed, convert_video_format
)
from core.ffmpeg_utils import get_media_info

class VideoTab:
    def __init__(self, app, parent_tab):
        self.app = app
        self.tab = parent_tab
        self.video_files = []
        self.current_video = None
        self.video_duration = 0.0
        self.current_time = 0.0
        self.cut_start = 0.0
        self.cut_end = 0.0
        self.is_playing = False
        self.play_thread = None
        self.last_frame_tk = None

        self._setup_ui()

    def _setup_ui(self):
        # Top Mode Switch
        top_bar = ctk.CTkFrame(self.tab, height=45, fg_color='transparent')
        top_bar.pack(fill='x', padx=10, pady=(5, 5))

        self.mode_switch = ctk.CTkSegmentedButton(
            top_bar,
            values=['🎬 Timeline Editor & Cutter', '🔗 Merge & Batch Tools'],
            command=self._on_mode_change
        )
        self.mode_switch.set('🎬 Timeline Editor & Cutter')
        self.mode_switch.pack(side='left', padx=10)

        # Container frames
        self.timeline_frame = ctk.CTkFrame(self.tab, fg_color='transparent')
        self.batch_frame = ctk.CTkFrame(self.tab, fg_color='transparent')

        self._setup_timeline_ui()
        self._setup_batch_ui()

        self.timeline_frame.pack(fill='both', expand=True, padx=5, pady=5)

    def _on_mode_change(self, val):
        if 'Timeline' in val:
            self.batch_frame.pack_forget()
            self.timeline_frame.pack(fill='both', expand=True, padx=5, pady=5)
        else:
            self.is_playing = False
            self.timeline_frame.pack_forget()
            self.batch_frame.pack(fill='both', expand=True, padx=5, pady=5)

    # =========================================================================
    # TIMELINE EDITOR & VIDEO PLAYER
    # =========================================================================
    def _setup_timeline_ui(self):
        # Left Panel: File Info & Cut Actions
        left_panel = ctk.CTkFrame(self.timeline_frame, width=280)
        left_panel.pack(side='left', fill='both', expand=False, padx=(5, 5), pady=5)

        ctk.CTkLabel(left_panel, text='Active Video', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(10, 2))
        
        load_btn = ctk.CTkButton(left_panel, text='📂 Open Video to Edit', command=self._open_video_for_timeline, height=32)
        load_btn.pack(fill='x', padx=10, pady=5)

        self.vid_name_lbl = ctk.CTkLabel(left_panel, text='No video loaded', text_color='gray', font=ctk.CTkFont(size=11), wraplength=250)
        self.vid_name_lbl.pack(anchor='w', padx=10, pady=(0, 10))

        self.vid_info_lbl = ctk.CTkLabel(left_panel, text='Duration: 00:00 | Resolution: -', text_color='gray', font=ctk.CTkFont(size=11))
        self.vid_info_lbl.pack(anchor='w', padx=10, pady=(0, 10))

        # Cut Marker Panel
        cut_card = ctk.CTkFrame(left_panel)
        cut_card.pack(fill='x', padx=10, pady=10)

        ctk.CTkLabel(cut_card, text='Timeline Cut Markers', font=ctk.CTkFont(size=13, weight='bold')).pack(anchor='w', padx=10, pady=(8, 4))
        
        btn_row = ctk.CTkFrame(cut_card, fg_color='transparent')
        btn_row.pack(fill='x', padx=10, pady=5)
        ctk.CTkButton(btn_row, text='[ Set Start (In)', width=110, command=self._set_cut_start).pack(side='left', padx=(0, 5))
        ctk.CTkButton(btn_row, text='Set End (Out) ]', width=110, command=self._set_cut_end).pack(side='right')

        self.cut_summary_lbl = ctk.CTkLabel(
            cut_card,
            text='Cut: 00:00.0 ➔ 00:00.0\nDuration: 0.0s',
            font=ctk.CTkFont(size=12, weight='bold'),
            text_color='#1f8b4c'
        )
        self.cut_summary_lbl.pack(padx=10, pady=8)

        self.cut_btn = ctk.CTkButton(
            left_panel,
            text='✂️ Cut & Export Selected Clip',
            height=40,
            font=ctk.CTkFont(size=13, weight='bold'),
            fg_color='#1f8b4c',
            hover_color='#176d3b',
            command=self._export_cut_clip
        )
        self.cut_btn.pack(fill='x', padx=10, pady=(10, 5))

        # Right Panel: Video Screen & Scrubber Bar
        screen_panel = ctk.CTkFrame(self.timeline_frame)
        screen_panel.pack(side='right', fill='both', expand=True, padx=(5, 5), pady=5)

        # Video Frame Canvas / Screen
        self.screen_lbl = ctk.CTkLabel(
            screen_panel,
            text='[ Open a video to start editing ]\n\nDrag the timeline bar below to scrub frames in real time.',
            fg_color='#1a1a1a',
            corner_radius=8
        )
        self.screen_lbl.pack(fill='both', expand=True, padx=10, pady=(10, 5))

        # Scrubber Bar & Timestamps
        scrubber_box = ctk.CTkFrame(screen_panel)
        scrubber_box.pack(fill='x', padx=10, pady=(5, 10))

        time_row = ctk.CTkFrame(scrubber_box, fg_color='transparent')
        time_row.pack(fill='x', padx=10, pady=(6, 2))

        self.time_lbl = ctk.CTkLabel(time_row, text='00:00.0 / 00:00.0', font=ctk.CTkFont(size=12, weight='bold'))
        self.time_lbl.pack(side='left')

        self.timeline_slider = ctk.CTkSlider(
            scrubber_box,
            from_=0.0,
            to=100.0,
            command=self._on_timeline_drag
        )
        self.timeline_slider.set(0.0)
        self.timeline_slider.pack(fill='x', padx=10, pady=5)

        # Controls row
        ctrl_row = ctk.CTkFrame(scrubber_box, fg_color='transparent')
        ctrl_row.pack(fill='x', padx=10, pady=(2, 8))

        ctk.CTkButton(ctrl_row, text='⏪ -1s', width=60, command=self._step_back).pack(side='left', padx=5)
        self.play_btn = ctk.CTkButton(ctrl_row, text='▶ Play Preview', width=110, command=self._toggle_playback)
        self.play_btn.pack(side='left', padx=5)
        ctk.CTkButton(ctrl_row, text='+1s ⏩', width=60, command=self._step_fwd).pack(side='left', padx=5)

    def _open_video_for_timeline(self):
        f = filedialog.askopenfilename(
            title='Select Video File to Edit',
            filetypes=[('Video Files', '*.mp4;*.mkv;*.mov;*.webm;*.avi;*.flv')]
        )
        if f:
            self.current_video = f
            self.vid_name_lbl.configure(text=os.path.basename(f), text_color='white')
            info = get_media_info(f)
            self.video_duration = info.get('duration', 0.0)
            res_w = info.get('width', 0)
            res_h = info.get('height', 0)
            self.vid_info_lbl.configure(text=f'Duration: {self._format_time(self.video_duration)} | {res_w}x{res_h}')
            
            self.current_time = 0.0
            self.cut_start = 0.0
            self.cut_end = self.video_duration
            self.timeline_slider.configure(to=max(1.0, self.video_duration))
            self.timeline_slider.set(0.0)
            self._update_cut_labels()
            self._render_frame_at(0.0)

    def _format_time(self, seconds: float) -> str:
        m = int(seconds // 60)
        s = seconds % 60
        return f'{m:02d}:{s:04.1f}'

    def _on_timeline_drag(self, val):
        self.current_time = float(val)
        self._render_frame_at(self.current_time)

    def _step_back(self):
        self.current_time = max(0.0, self.current_time - 1.0)
        self.timeline_slider.set(self.current_time)
        self._render_frame_at(self.current_time)

    def _step_fwd(self):
        self.current_time = min(self.video_duration, self.current_time + 1.0)
        self.timeline_slider.set(self.current_time)
        self._render_frame_at(self.current_time)

    def _set_cut_start(self):
        self.cut_start = self.current_time
        if self.cut_end <= self.cut_start:
            self.cut_end = min(self.video_duration, self.cut_start + 5.0)
        self._update_cut_labels()

    def _set_cut_end(self):
        self.cut_end = self.current_time
        if self.cut_end <= self.cut_start:
            self.cut_start = max(0.0, self.cut_end - 5.0)
        self._update_cut_labels()

    def _update_cut_labels(self):
        dur = max(0.0, self.cut_end - self.cut_start)
        self.cut_summary_lbl.configure(
            text=f'Cut: {self._format_time(self.cut_start)} ➔ {self._format_time(self.cut_end)}\nDuration: {dur:.1f}s'
        )

    def _toggle_playback(self):
        if self.is_playing:
            self.is_playing = False
            self.play_btn.configure(text='▶ Play Preview')
        else:
            if not self.current_video:
                return
            self.is_playing = True
            self.play_btn.configure(text='⏸ Pause')
            self.play_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.play_thread.start()

    def _playback_loop(self):
        while self.is_playing and self.current_time < self.video_duration:
            time.sleep(0.1)
            self.current_time = min(self.video_duration, self.current_time + 0.1)
            self.timeline_slider.set(self.current_time)
            self._render_frame_at(self.current_time)
        self.is_playing = False
        self.play_btn.configure(text='▶ Play Preview')

    def _render_frame_at(self, timestamp: float):
        if not self.current_video:
            return
        
        self.time_lbl.configure(text=f'{self._format_time(timestamp)} / {self._format_time(self.video_duration)}')

        def worker():
            frame = extract_video_frame(self.current_video, timestamp)
            if frame:
                # Resize frame to fit screen area
                frame.thumbnail((560, 360), Image.Resampling.BILINEAR)
                img_tk = ctk.CTkImage(light_image=frame, dark_image=frame, size=frame.size)
                self.screen_lbl.configure(image=img_tk, text='')
        threading.Thread(target=worker, daemon=True).start()

    def _export_cut_clip(self):
        if not self.current_video:
            messagebox.showwarning('No Video', 'Please load a video file first.')
            return

        out_dir = self.app.output_dir
        os.makedirs(out_dir, exist_ok=True)
        bname = os.path.splitext(os.path.basename(self.current_video))[0]
        out_file = os.path.join(out_dir, f'{bname}_cut_{int(self.cut_start)}s_{int(self.cut_end)}s.mp4')

        try:
            trim_video(self.current_video, out_file, start_time=f'{self.cut_start:.2f}', end_time=f'{self.cut_end:.2f}', fast_copy=True)
            messagebox.showinfo('Clip Exported', f'Trimmed clip saved successfully to:\n{out_file}')
        except Exception as e:
            messagebox.showerror('Trim Error', f'Failed to cut clip:\n{str(e)}')

    # =========================================================================
    # BATCH & MERGE UTILITIES
    # =========================================================================
    def _setup_batch_ui(self):
        left_frame = ctk.CTkFrame(self.batch_frame, width=380)
        left_frame.pack(side='left', fill='both', expand=False, padx=(5, 5), pady=5)

        ctk.CTkLabel(left_frame, text='Selected Media Files (Video & Audio)', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', padx=10, pady=(10, 5))

        btn_row = ctk.CTkFrame(left_frame, fg_color='transparent')
        btn_row.pack(fill='x', padx=10, pady=5)
        ctk.CTkButton(btn_row, text='+ Add Media', width=120, command=self._add_video_files).pack(side='left', padx=(0, 5))
        ctk.CTkButton(btn_row, text='Clear', width=70, fg_color='#6c757d', hover_color='#5a6268', command=self._clear_video_files).pack(side='right')

        self.video_listbox = ctk.CTkTextbox(left_frame, height=220, state='disabled')
        self.video_listbox.pack(fill='both', expand=True, padx=10, pady=5)

        self.video_count_lbl = ctk.CTkLabel(left_frame, text='0 files selected', text_color='gray', font=ctk.CTkFont(size=11))
        self.video_count_lbl.pack(anchor='w', padx=10, pady=(2, 10))

        # Quick Merge Action Box
        merge_box = ctk.CTkFrame(left_frame)
        merge_box.pack(fill='x', padx=10, pady=10)
        ctk.CTkLabel(merge_box, text='Quick Merging', font=ctk.CTkFont(size=13, weight='bold')).pack(anchor='w', padx=10, pady=(8, 4))
        
        ctk.CTkButton(merge_box, text='🔗 Merge Selected Videos', fg_color='#2b5b84', hover_color='#1f4463', command=self._merge_all_videos).pack(fill='x', padx=10, pady=4)
        ctk.CTkButton(merge_box, text='🎵 Merge Selected Audios', fg_color='#2b5b84', hover_color='#1f4463', command=self._merge_all_audios).pack(fill='x', padx=10, pady=4)
        ctk.CTkButton(merge_box, text='🔊 Replace / Add Audio Track', fg_color='#2b5b84', hover_color='#1f4463', command=self._replace_audio_track).pack(fill='x', padx=10, pady=(4, 8))

        # Right panel: Operations
        right_frame = ctk.CTkScrollableFrame(self.batch_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 5), pady=5)

        ctk.CTkLabel(right_frame, text='Batch Conversions & Tools', font=ctk.CTkFont(size=16, weight='bold')).pack(anchor='w', padx=10, pady=(5, 10))

        self.video_action = ctk.StringVar(value='convert')

        video_actions = [
            ('Convert Format (MP4, MKV, MOV, WEBM, MP3, WAV)', 'convert'),
            ('Video to Smooth GIF Maker (2-pass palette)', 'gif'),
            ('Target File Size Compressor (Discord 25MB, WhatsApp 16MB)', 'compress_size'),
            ('Audio Extractor (Extract MP3/WAV from video)', 'audio_extract'),
            ('Mute Video (Strip audio track)', 'mute'),
            ('Video Speed Controller (0.5x, 1.25x, 1.5x, 2.0x)', 'speed')
        ]

        for text, val in video_actions:
            ctk.CTkRadioButton(
                right_frame,
                text=text,
                variable=self.video_action,
                value=val,
                command=self._update_opts_ui
            ).pack(anchor='w', padx=15, pady=4)

        self.video_opts_frame = ctk.CTkFrame(right_frame)
        self.video_opts_frame.pack(fill='x', padx=10, pady=15)
        self._update_opts_ui()

        self.video_progress = ctk.CTkProgressBar(right_frame)
        self.video_progress.set(0)
        self.video_progress.pack(fill='x', padx=10, pady=(15, 5))

        self.video_status_lbl = ctk.CTkLabel(right_frame, text='Ready', font=ctk.CTkFont(size=12))
        self.video_status_lbl.pack(anchor='w', padx=10, pady=2)

        self.video_run_btn = ctk.CTkButton(
            right_frame,
            text='🎬 Process Media Batch',
            height=40,
            font=ctk.CTkFont(size=14, weight='bold'),
            fg_color='#1f8b4c',
            hover_color='#176d3b',
            command=self._run_task_thread
        )
        self.video_run_btn.pack(fill='x', padx=10, pady=10)

    def _update_opts_ui(self):
        for w in self.video_opts_frame.winfo_children():
            w.destroy()

        act = self.video_action.get()
        if act == 'convert':
            ctk.CTkLabel(self.video_opts_frame, text='Target Output Format:').pack(anchor='w', padx=10, pady=(10, 2))
            self.vid_fmt_combo = ctk.CTkComboBox(self.video_opts_frame, values=['mp4', 'mkv', 'mov', 'webm', 'avi', 'mp3', 'wav'])
            self.vid_fmt_combo.set('mp4')
            self.vid_fmt_combo.pack(anchor='w', padx=10, pady=(0, 10))
        elif act == 'gif':
            row = ctk.CTkFrame(self.video_opts_frame, fg_color='transparent')
            row.pack(fill='x', padx=10, pady=10)
            ctk.CTkLabel(row, text='FPS:').pack(side='left')
            self.gif_fps_combo = ctk.CTkComboBox(row, values=['10', '15', '24'], width=80)
            self.gif_fps_combo.set('15')
            self.gif_fps_combo.pack(side='left', padx=5)

            ctk.CTkLabel(row, text='Width (px):').pack(side='left', padx=(15, 0))
            self.gif_w_combo = ctk.CTkComboBox(row, values=['320', '480', '640', '800'], width=90)
            self.gif_w_combo.set('480')
            self.gif_w_combo.pack(side='left', padx=5)
        elif act == 'compress_size':
            ctk.CTkLabel(self.video_opts_frame, text='Target Maximum File Size:').pack(anchor='w', padx=10, pady=(10, 2))
            self.vid_target_mb = ctk.CTkComboBox(self.video_opts_frame, values=['25 MB (Discord Nitro-Free)', '16 MB (WhatsApp)', '10 MB (Email)', '50 MB', '100 MB'])
            self.vid_target_mb.set('25 MB (Discord Nitro-Free)')
            self.vid_target_mb.pack(anchor='w', padx=10, pady=(0, 10))
        elif act == 'audio_extract':
            ctk.CTkLabel(self.video_opts_frame, text='Audio Format:').pack(anchor='w', padx=10, pady=(10, 2))
            self.audio_fmt_combo = ctk.CTkComboBox(self.video_opts_frame, values=['mp3', 'wav', 'aac'])
            self.audio_fmt_combo.set('mp3')
            self.audio_fmt_combo.pack(anchor='w', padx=10, pady=(0, 10))
        elif act == 'speed':
            ctk.CTkLabel(self.video_opts_frame, text='Speed Multiplier:').pack(anchor='w', padx=10, pady=(10, 2))
            self.speed_combo = ctk.CTkComboBox(self.video_opts_frame, values=['0.5x (Slow Motion)', '0.75x', '1.25x', '1.5x (Fast)', '2.0x (Double Speed)'])
            self.speed_combo.set('1.5x (Fast)')
            self.speed_combo.pack(anchor='w', padx=10, pady=(0, 10))
        else:
            ctk.CTkLabel(self.video_opts_frame, text='Mute action will instantly strip the audio stream.').pack(padx=10, pady=10)

    def _add_video_files(self):
        files = filedialog.askopenfilenames(
            title='Select Video or Audio Files',
            filetypes=[('Media Files', '*.mp4;*.mkv;*.mov;*.webm;*.avi;*.flv;*.mp3;*.wav;*.aac')]
        )
        if files:
            self.video_files.extend(files)
            self._update_listbox()

    def _clear_video_files(self):
        self.video_files.clear()
        self._update_listbox()

    def _update_listbox(self):
        self.video_listbox.configure(state='normal')
        self.video_listbox.delete('1.0', 'end')
        for i, f in enumerate(self.video_files):
            self.video_listbox.insert('end', f'{i+1}. {os.path.basename(f)}\n')
        self.video_listbox.configure(state='disabled')
        self.video_count_lbl.configure(text=f'{len(self.video_files)} files selected')

    def _merge_all_videos(self):
        vids = [f for f in self.video_files if f.lower().endswith(('.mp4', '.mkv', '.mov', '.webm', '.avi'))]
        if len(vids) < 2:
            messagebox.showwarning('Need More Videos', 'Please add at least 2 video files to the queue to merge.')
            return

        out_dir = self.app.output_dir
        os.makedirs(out_dir, exist_ok=True)
        out_f = os.path.join(out_dir, 'merged_video.mp4')

        def worker():
            try:
                self.video_status_lbl.configure(text='Merging videos...')
                merge_videos(vids, out_f)
                self.video_status_lbl.configure(text='Videos merged successfully!')
                messagebox.showinfo('Success', f'Merged videos saved to:\n{out_f}')
            except Exception as e:
                messagebox.showerror('Merge Error', f'Failed to merge videos:\n{str(e)}')
        threading.Thread(target=worker, daemon=True).start()

    def _merge_all_audios(self):
        auds = [f for f in self.video_files if f.lower().endswith(('.mp3', '.wav', '.aac', '.m4a', '.ogg'))]
        if len(auds) < 2:
            messagebox.showwarning('Need More Audios', 'Please add at least 2 audio files to the queue to merge.')
            return

        out_dir = self.app.output_dir
        os.makedirs(out_dir, exist_ok=True)
        out_f = os.path.join(out_dir, 'merged_audio.mp3')

        def worker():
            try:
                self.video_status_lbl.configure(text='Merging audios...')
                merge_audios(auds, out_f)
                self.video_status_lbl.configure(text='Audios merged successfully!')
                messagebox.showinfo('Success', f'Merged audio saved to:\n{out_f}')
            except Exception as e:
                messagebox.showerror('Merge Error', f'Failed to merge audios:\n{str(e)}')
        threading.Thread(target=worker, daemon=True).start()

    def _replace_audio_track(self):
        v_file = filedialog.askopenfilename(title='Select Video File', filetypes=[('Video Files', '*.mp4;*.mkv;*.mov')])
        if not v_file:
            return
        a_file = filedialog.askopenfilename(title='Select Audio Track File', filetypes=[('Audio Files', '*.mp3;*.wav;*.aac')])
        if not a_file:
            return

        out_dir = self.app.output_dir
        os.makedirs(out_dir, exist_ok=True)
        bname = os.path.splitext(os.path.basename(v_file))[0]
        out_f = os.path.join(out_dir, f'{bname}_with_new_audio.mp4')

        def worker():
            try:
                self.video_status_lbl.configure(text='Adding audio track to video...')
                replace_video_audio(v_file, a_file, out_f)
                self.video_status_lbl.configure(text='Audio track replaced!')
                messagebox.showinfo('Success', f'New video saved to:\n{out_f}')
            except Exception as e:
                messagebox.showerror('Audio Replace Error', f'Failed to replace audio:\n{str(e)}')
        threading.Thread(target=worker, daemon=True).start()

    def _run_task_thread(self):
        if not self.video_files:
            messagebox.showwarning('No Files', 'Please select at least one media file first.')
            return
        threading.Thread(target=self._execute_task, daemon=True).start()

    def _execute_task(self):
        self.video_run_btn.configure(state='disabled')
        self.video_progress.set(0.05)
        out_dir = self.app.output_dir
        os.makedirs(out_dir, exist_ok=True)
        act = self.video_action.get()
        total = len(self.video_files)

        try:
            for idx, f in enumerate(self.video_files):
                bname = os.path.splitext(os.path.basename(f))[0]
                self.video_status_lbl.configure(text=f'Processing ({idx+1}/{total}): {os.path.basename(f)}')

                if act == 'convert':
                    target_fmt = self.vid_fmt_combo.get().lower()
                    out_file = os.path.join(out_dir, f'{bname}.{target_fmt}')
                    if target_fmt in ('mp3', 'wav', 'aac'):
                        extract_audio(f, out_file, audio_format=target_fmt)
                    else:
                        convert_video_format(f, out_file)
                elif act == 'gif':
                    fps = int(self.gif_fps_combo.get())
                    w = int(self.gif_w_combo.get())
                    out_file = os.path.join(out_dir, f'{bname}.gif')
                    video_to_gif(f, out_file, fps=fps, scale_width=w)
                elif act == 'compress_size':
                    mb_text = self.vid_target_mb.get().split()[0]
                    mb_val = float(mb_text)
                    out_file = os.path.join(out_dir, f'{bname}_compressed.mp4')
                    compress_video_target_size(f, out_file, target_size_mb=mb_val)
                elif act == 'audio_extract':
                    afmt = self.audio_fmt_combo.get().lower()
                    out_file = os.path.join(out_dir, f'{bname}.{afmt}')
                    extract_audio(f, out_file, audio_format=afmt)
                elif act == 'mute':
                    ext = os.path.splitext(f)[1]
                    out_file = os.path.join(out_dir, f'{bname}_muted{ext}')
                    mute_video(f, out_file)
                elif act == 'speed':
                    sp_str = self.speed_combo.get().split('x')[0]
                    sp_factor = float(sp_str)
                    out_file = os.path.join(out_dir, f'{bname}_{sp_factor}x.mp4')
                    change_video_speed(f, out_file, speed_factor=sp_factor)

                self.video_progress.set((idx + 1) / total)

            self.video_status_lbl.configure(text=f'Complete! Successfully processed {total} files.')
            messagebox.showinfo('Success', 'Media processing completed successfully!')
        except Exception as e:
            self.video_status_lbl.configure(text=f'Error: {str(e)}')
            messagebox.showerror('Error', f'Media operation failed:\n{str(e)}')
        finally:
            self.video_run_btn.configure(state='normal')
