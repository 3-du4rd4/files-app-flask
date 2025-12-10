import io
import tempfile
import subprocess
from pydub import AudioSegment


def processar_audio(file):
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_input.write(file.read())
    temp_input.close()
    audio_path = temp_input.name

    audio = AudioSegment.from_file(audio_path)

    duracao_seg = len(audio) / 1000.0        
    taxa_amostragem = audio.frame_rate      
    canais = audio.channels                   

    cmd_bitrate = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=bit_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]

    try:
        bitrate_output = subprocess.check_output(cmd_bitrate).decode().strip()
        bitrate = int(bitrate_output) if bitrate_output.isdigit() else None
    except:
        bitrate = None

    info = {
        "duracao_segundos": duracao_seg,
        "bitrate": bitrate,
        "sample_rate": taxa_amostragem,
        "channels": canais
    }

    return info
