from faster_whisper.vad import VadOptions, get_speech_timestamps


def is_speaking(data):
    vad_options = VadOptions(min_silence_duration_ms=2000, speech_pad_ms=0)
    timestamps = get_speech_timestamps(data, vad_options)
    return len(timestamps) > 0
