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
