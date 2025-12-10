import io
import os
import cv2
import tempfile
import subprocess
from PIL import Image


def processar_video(file):
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_input.write(file.read())
    temp_input.close()
    video_path = temp_input.name

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Erro ao abrir vídeo")

    largura  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps      = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duracao = frame_count / fps if fps > 0 else 0

    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

    cmd_bitrate = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=bit_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    try:
        bitrate_output = subprocess.check_output(cmd_bitrate).decode().strip()
        bitrate = int(bitrate_output) if bitrate_output.isdigit() else None
    except:
        bitrate = None

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise ValueError("Não foi possível ler o primeiro frame do vídeo")

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(frame_rgb)
    pil_img.thumbnail((320, 320))

    thumb_bytes_io = io.BytesIO()
    pil_img.save(thumb_bytes_io, format="JPEG")
    thumb_bytes_io.seek(0)
    thumb_bytes = thumb_bytes_io.read()

    resolutions = {
        "1080p": "1920:1080",
        "720p":  "1280:720",
        "480p":  "854:480"
    }
    output_versions = {}

    for name, size in resolutions.items():
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_out:
            out_path = temp_out.name

        cmd_resize = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"scale={size}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            out_path
        ]
        subprocess.run(cmd_resize, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        with open(out_path, "rb") as f:
            output_versions[name] = f.read()
        os.remove(out_path)

    os.remove(video_path)

    info = {
        "duracao_segundos": duracao,
        "largura": largura,
        "altura": altura,
        "resolucao": f"{largura}x{altura}",
        "fps": fps,
        "codec_video": codec.strip(),
        "bitrate": bitrate
    }

    return info, thumb_bytes, output_versions
