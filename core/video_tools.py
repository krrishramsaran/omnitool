import os
import io
import subprocess
import tempfile
from PIL import Image
from .ffmpeg_utils import run_ffmpeg, get_media_info, get_ffmpeg_path

def extract_video_frame(input_path: str, timestamp_sec: float) -> Image.Image:
    '''Extract a single frame from video at given timestamp as a PIL Image.'''
    ffmpeg_exe = get_ffmpeg_path()
    t_str = f'{max(0.0, timestamp_sec):.3f}'
    cmd = [
        ffmpeg_exe,
        '-ss', t_str,
        '-i', input_path,
        '-vframes', '1',
        '-f', 'image2pipe',
        '-vcodec', 'mjpeg',
        '-'
    ]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags
    )
    if p.returncode == 0 and len(p.stdout) > 0:
        return Image.open(io.BytesIO(p.stdout))
    return None

def trim_video(input_path: str, output_path: str, start_time: str, end_time: str = None, fast_copy: bool = True):
    '''Trim video. Fast copy avoids re-encoding.'''
    args = ['-y']
    if start_time:
        args.extend(['-ss', str(start_time)])
    if end_time:
        args.extend(['-to', str(end_time)])
    args.extend(['-i', input_path])

    if fast_copy:
        args.extend(['-c', 'copy'])
    else:
        args.extend(['-c:v', 'libx264', '-crf', '22', '-c:a', 'aac'])

    args.append(output_path)
    run_ffmpeg(args)
    return output_path

def merge_videos(video_paths: list[str], output_path: str):
    '''Concatenate multiple video files into a single video.'''
    if not video_paths:
        return None
    if len(video_paths) == 1:
        import shutil
        shutil.copyfile(video_paths[0], output_path)
        return output_path

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tf:
        for p in video_paths:
            safe_p = p.replace('\\', '/')
            tf.write(f'file \'{safe_p}\'\n')
        list_file = tf.name

    try:
        try:
            run_ffmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', output_path])
        except Exception:
            inputs = []
            filter_parts = []
            for i, p in enumerate(video_paths):
                inputs.extend(['-i', p])
                filter_parts.append(f'[{i}:v:0][{i}:a:0]')
            joined = ''.join(filter_parts)
            filter_str = f'{joined}concat=n={len(video_paths)}:v=1:a=1[outv][outa]'
            args = ['-y'] + inputs + ['-filter_complex', filter_str, '-map', '[outv]', '-map', '[outa]', '-c:v', 'libx264', '-c:a', 'aac', output_path]
            run_ffmpeg(args)
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)

    return output_path

def merge_audios(audio_paths: list[str], output_path: str):
    '''Concatenate multiple audio tracks into a single audio file.'''
    if not audio_paths:
        return None
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tf:
        for p in audio_paths:
            safe_p = p.replace('\\', '/')
            tf.write(f'file \'{safe_p}\'\n')
        list_file = tf.name

    try:
        try:
            run_ffmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', output_path])
        except Exception:
            inputs = []
            for p in audio_paths:
                inputs.extend(['-i', p])
            filter_str = f'concat=n={len(audio_paths)}:v=0:a=1[outa]'
            args = ['-y'] + inputs + ['-filter_complex', filter_str, '-map', '[outa]', output_path]
            run_ffmpeg(args)
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)

    return output_path

def replace_video_audio(video_path: str, audio_path: str, output_path: str):
    '''Mux or replace audio track in a video file.'''
    args = [
        '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-shortest',
        output_path
    ]
    run_ffmpeg(args)
    return output_path

def video_to_gif(input_path: str, output_path: str, fps: int = 15, scale_width: int = 480,
                 start_time: str = None, duration: str = None):
    '''Convert video to high-quality smooth GIF using 2-pass palette generation.'''
    args = ['-y']
    if start_time:
        args.extend(['-ss', str(start_time)])
    if duration:
        args.extend(['-t', str(duration)])
    args.extend(['-i', input_path])

    vf_filter = f'fps={fps},scale={scale_width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer'
    args.extend(['-vf', vf_filter, output_path])
    run_ffmpeg(args)
    return output_path

def compress_video_target_size(input_path: str, output_path: str, target_size_mb: float = 25.0):
    '''Compress a video to meet a specific target size.'''
    info = get_media_info(input_path)
    duration = info.get('duration', 0.0)
    if duration <= 0:
        run_ffmpeg(['-y', '-i', input_path, '-c:v', 'libx264', '-crf', '28', '-c:a', 'aac', '-b:a', '96k', output_path])
        return output_path

    audio_bitrate_kbps = 128
    total_target_bits = target_size_mb * 8 * 1024 * 1024 * 0.95
    total_bitrate_kbps = (total_target_bits / duration) / 1024.0
    video_bitrate_kbps = max(50.0, total_bitrate_kbps - audio_bitrate_kbps)

    args = [
        '-y', '-i', input_path,
        '-c:v', 'libx264',
        '-b:v', f'{int(video_bitrate_kbps)}k',
        '-maxrate', f'{int(video_bitrate_kbps * 1.5)}k',
        '-bufsize', f'{int(video_bitrate_kbps * 2)}k',
        '-preset', 'medium',
        '-c:a', 'aac',
        '-b:a', f'{audio_bitrate_kbps}k',
        output_path
    ]
    run_ffmpeg(args)
    return output_path

def extract_audio(input_path: str, output_path: str, audio_format: str = 'mp3', bitrate: str = '192k'):
    '''Extract audio from video file.'''
    args = ['-y', '-i', input_path, '-vn']
    if audio_format.lower() == 'mp3':
        args.extend(['-c:a', 'libmp3lame', '-b:a', bitrate])
    elif audio_format.lower() == 'wav':
        args.extend(['-c:a', 'pcm_s16le'])
    elif audio_format.lower() == 'aac':
        args.extend(['-c:a', 'aac', '-b:a', bitrate])
    else:
        args.extend(['-c:a', 'copy'])
    args.append(output_path)
    run_ffmpeg(args)
    return output_path

def mute_video(input_path: str, output_path: str):
    '''Strip audio completely to mute video.'''
    args = ['-y', '-i', input_path, '-c:v', 'copy', '-an', output_path]
    run_ffmpeg(args)
    return output_path

def change_video_speed(input_path: str, output_path: str, speed_factor: float = 1.5):
    '''Adjust video speed.'''
    args = ['-y', '-i', input_path]
    v_pts = 1.0 / speed_factor
    v_filter = f'setpts={v_pts}*PTS'

    remaining_speed = speed_factor
    atempo_chain = []
    while remaining_speed > 2.0:
        atempo_chain.append('atempo=2.0')
        remaining_speed /= 2.0
    while remaining_speed < 0.5:
        atempo_chain.append('atempo=0.5')
        remaining_speed /= 0.5
    atempo_chain.append(f'atempo={remaining_speed:.4f}')
    a_filter = ','.join(atempo_chain)

    args.extend([
        '-filter:v', v_filter,
        '-filter:a', a_filter,
        '-c:v', 'libx264',
        '-crf', '22',
        '-c:a', 'aac',
        output_path
    ])
    run_ffmpeg(args)
    return output_path

def convert_video_format(input_path: str, output_path: str, resolution: str = None, crf: int = 23):
    '''Convert video format.'''
    args = ['-y', '-i', input_path]
    if resolution:
        args.extend(['-vf', f'scale={resolution}'])

    out_ext = os.path.splitext(output_path)[1].lower()
    if out_ext == '.webm':
        args.extend(['-c:v', 'libvpx-vp9', '-crf', str(crf), '-b:v', '0', '-c:a', 'libopus'])
    else:
        args.extend(['-c:v', 'libx264', '-crf', str(crf), '-c:a', 'aac'])

    args.append(output_path)
    run_ffmpeg(args)
    return output_path

def add_fade(input_path: str, output_path: str, fade_in: float = 1.0, fade_out: float = 1.0,
             audio_fade: bool = True, fade_in_sec: float = None, fade_out_sec: float = None):
    '''Add video and audio fade-in at the start and fade-out at the end.'''
    if fade_in_sec is not None:
        fade_in = fade_in_sec
    if fade_out_sec is not None:
        fade_out = fade_out_sec
    info = get_media_info(input_path)
    duration = info.get('duration', 0.0)
    if duration <= 0:
        raise ValueError('Cannot determine video duration for fade calculation.')

    vf_filters = []
    af_filters = []

    if fade_in > 0:
        vf_filters.append(f'fade=t=in:st=0:d={fade_in:.3f}')
        if audio_fade:
            af_filters.append(f'afade=t=in:st=0:d={fade_in:.3f}')

    if fade_out > 0:
        fo_start = max(0.0, duration - fade_out)
        vf_filters.append(f'fade=t=out:st={fo_start:.3f}:d={fade_out:.3f}')
        if audio_fade:
            af_filters.append(f'afade=t=out:st={fo_start:.3f}:d={fade_out:.3f}')

    args = ['-y', '-i', input_path]
    if vf_filters:
        args.extend(['-vf', ','.join(vf_filters)])
    if af_filters:
        args.extend(['-af', ','.join(af_filters)])

    args.extend(['-c:v', 'libx264', '-crf', '22', '-c:a', 'aac', output_path])
    run_ffmpeg(args)
    return output_path

def crossfade_videos(video1, video2=None, output_path: str = None, duration: float = 1.0, transition_duration: float = None):
    '''Crossfade dissolve transition between two video clips. Accepts pair of paths or list of paths.'''
    if transition_duration is not None:
        duration = transition_duration

    if isinstance(video1, (list, tuple)):
        v_list = video1
        if len(v_list) < 2:
            raise ValueError('Crossfade requires at least 2 videos.')
        out_path = video2
        v1 = v_list[0]
        v2 = v_list[1]
    else:
        v1 = video1
        v2 = video2
        out_path = output_path

    info1 = get_media_info(v1)
    dur1 = info1.get('duration', 0.0)
    offset = max(0.0, dur1 - duration)

    filter_complex = (
        f'[0:v][1:v]xfade=transition=dissolve:duration={duration:.3f}:offset={offset:.3f}[outv];'
        f'[0:a][1:a]acrossfade=d={duration:.3f}[outa]'
    )
    args = [
        '-y',
        '-i', v1,
        '-i', v2,
        '-filter_complex', filter_complex,
        '-map', '[outv]',
        '-map', '[outa]',
        '-c:v', 'libx264',
        '-crf', '22',
        '-c:a', 'aac',
        out_path
    ]
    run_ffmpeg(args)
    return out_path

def burn_subtitles(input_path: str, subtitle_path: str, output_path: str,
                   font_size: int = 24, font_color: str = 'white',
                   outline_color: str = 'black', outline_width: int = 2,
                   position: str = 'bottom'):
    '''Burn SRT or ASS subtitles permanently into video.'''
    ext = os.path.splitext(subtitle_path)[1].lower()
    sub_safe = subtitle_path.replace('\\', '/').replace(':', '\\:')

    if ext == '.ass':
        vf = f"ass='{sub_safe}'"
    else:
        margin_v = 20 if position == 'bottom' else 280
        color_map = {
            'white': 'FFFFFF', 'yellow': '00FFFF', 'black': '000000',
            'red': '0000FF', 'green': '00FF00', 'cyan': 'FFFF00'
        }
        primary = color_map.get(font_color.lower(), 'FFFFFF')
        outline = color_map.get(outline_color.lower(), '000000')
        style = (
            f"FontSize={font_size},"
            f"PrimaryColour=&H00{primary},"
            f"OutlineColour=&H00{outline},"
            f"Outline={outline_width},"
            f"MarginV={margin_v},"
            f"Alignment=2"
        )
        vf = f"subtitles='{sub_safe}':force_style='{style}'"

    args = [
        '-y', '-i', input_path,
        '-vf', vf,
        '-c:v', 'libx264', '-crf', '22',
        '-c:a', 'copy',
        output_path
    ]
    run_ffmpeg(args)
    return output_path

def extract_audio_waveform(input_path: str, num_samples: int = 400, num_points: int = None) -> list[float]:
    '''
    Extract normalized audio amplitude data [0.0..1.0] for waveform display.
    Uses FFmpeg to decode audio into mono raw 16-bit PCM.
    '''
    if num_points is not None:
        num_samples = num_points
    import struct
    ffmpeg_exe = get_ffmpeg_path()
    cmd = [
        ffmpeg_exe, '-i', input_path,
        '-vn',
        '-ac', '1',
        '-ar', '8000',
        '-f', 's16le',
        '-'
    ]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)

    if p.returncode != 0 or not p.stdout:
        return [0.0] * num_samples

    raw = p.stdout
    n_frames = len(raw) // 2
    if n_frames == 0:
        return [0.0] * num_samples

    samples = struct.unpack(f'{n_frames}h', raw[:n_frames * 2])
    bucket = max(1, n_frames // num_samples)
    waveform = []
    for i in range(num_samples):
        start = i * bucket
        end = min(start + bucket, n_frames)
        if start < n_frames:
            chunk = [abs(s) for s in samples[start:end]]
            waveform.append(max(chunk) / 32768.0 if chunk else 0.0)
        else:
            waveform.append(0.0)
    return waveform

COLOR_GRADE_PRESETS = {
    'Cinematic Teal & Orange': (
        'eq=contrast=1.12:saturation=1.25,'
        'colorbalance=rs=0.08:gs=-0.04:bs=-0.08:rh=-0.08:gh=0.04:bh=0.14'
    ),
    'Vintage 70s Warm Film': (
        'colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,'
        'eq=contrast=1.05:saturation=0.85'
    ),
    'B&W Noir (High Contrast)': (
        'hue=s=0,eq=contrast=1.35:brightness=-0.04'
    ),
    'Vibrant Pop / HDR': (
        'eq=saturation=1.45:contrast=1.15'
    ),
    'Cyberpunk / Neon Cool': (
        'colorbalance=rs=-0.1:gs=-0.05:bs=0.2:rh=0.15:gh=-0.05:bh=0.25,'
        'eq=saturation=1.3'
    ),
}

def apply_color_grade(input_path: str, output_path: str, preset_name: str) -> str:
    '''Apply a cinematic color grading LUT/filter preset to video.'''
    if preset_name not in COLOR_GRADE_PRESETS:
        raise ValueError(f"Unknown preset '{preset_name}'. Choose from: {list(COLOR_GRADE_PRESETS.keys())}")

    vf = COLOR_GRADE_PRESETS[preset_name]
    args = [
        '-y', '-i', input_path,
        '-vf', vf,
        '-c:v', 'libx264', '-crf', '20',
        '-c:a', 'copy',
        output_path
    ]
    run_ffmpeg(args)
    return output_path

def render_clip_sequence(clips: list[dict], output_path: str) -> str:
    '''
    Stitch a sequence of video clips with individual In/Out trim markers.
    clips: [{'path': str, 'start': float (opt), 'end': float (opt)}, ...]
    '''
    if not clips:
        raise ValueError('No clips specified for sequence.')
    if len(clips) == 1:
        c = clips[0]
        st = c.get('start', 0.0) or 0.0
        en = c.get('end')
        if en:
            return trim_video(c['path'], output_path, st, en, reencode=True)
        else:
            return convert_video_format(c['path'], output_path)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        temp_files = []
        for idx, c in enumerate(clips):
            cp = c['path']
            st = c.get('start', 0.0) or 0.0
            en = c.get('end')
            t_out = os.path.join(td, f'seg_{idx:03d}.mp4')
            scale_filter = 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2'
            if en and en > st:
                dur = en - st
                args = ['-y', '-ss', str(st), '-i', cp, '-t', str(dur),
                        '-vf', scale_filter,
                        '-c:v', 'libx264', '-crf', '22', '-r', '30', '-c:a', 'aac', '-ar', '44100', '-ac', '2', t_out]
            else:
                args = ['-y', '-i', cp,
                        '-vf', scale_filter,
                        '-c:v', 'libx264', '-crf', '22', '-r', '30', '-c:a', 'aac', '-ar', '44100', '-ac', '2', t_out]
            run_ffmpeg(args)
            temp_files.append(t_out)

        merge_videos(temp_files, output_path)
    return output_path

