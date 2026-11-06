"""Voice-over for the project: script.srt -> assets/audio/voiceover.wav (48 kHz mono), every line fitted into its SRT window.
python tts.py <project_dir> [--spec spec.json] [--voices '{"Lan":"vi-VN-HoaiMyNeural"}']
Voices: spec["voices"] = {"<speaker name as in script.srt>": "<edge-tts voice>"}; default narrator/male = vi-VN-NamMinhNeural, female names listed in spec["female"].
Engine: edge-tts (free, no key). If edge-tts keeps failing (some cloud IPs are blocked) it falls back to gTTS (pip install gTTS).
"""
import argparse, asyncio, json, pathlib, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import srt_tools

GAP = 0.15
def run(cmd): subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).decode())

VOICES = {"vi": ("vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural"), "en": ("en-US-GuyNeural", "en-US-JennyNeural"), "es": ("es-ES-AlvaroNeural", "es-ES-ElviraNeural"),
          "fr": ("fr-FR-HenriNeural", "fr-FR-DeniseNeural"), "de": ("de-DE-ConradNeural", "de-DE-KatjaNeural"), "pt": ("pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"),
          "it": ("it-IT-DiegoNeural", "it-IT-ElsaNeural"), "id": ("id-ID-ArdiNeural", "id-ID-GadisNeural"), "ja": ("ja-JP-KeitaNeural", "ja-JP-NanamiNeural"),
          "ko": ("ko-KR-InJoonNeural", "ko-KR-SunHiNeural"), "zh": ("zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural"), "th": ("th-TH-NiwatNeural", "th-TH-PremwadeeNeural"),
          "ru": ("ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural"), "hi": ("hi-IN-MadhurNeural", "hi-IN-SwaraNeural")}

async def edge(text, voice, out):
    import edge_tts
    for attempt in range(8):
        try:
            await edge_tts.Communicate(text, voice).save(str(out)); return True
        except Exception:
            await asyncio.sleep(2 + attempt)
    return False

def gtts(text, lang, out):
    from gtts import gTTS
    gTTS(text=text, lang=lang).save(str(out)); return True

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--spec"); ap.add_argument("--voices")
    a = ap.parse_args(); proj = pathlib.Path(a.project)
    spec = json.load(open(a.spec, encoding="utf-8")) if a.spec else {}
    voices = {**spec.get("voices", {}), **(json.loads(a.voices) if a.voices else {})}
    female = set(spec.get("female", [])); lang = spec.get("lang", "vi")
    cues = srt_tools.parse_srt(proj / "script.srt"); total = cues[-1]["endMs"] / 1000.0
    work = pathlib.Path(tempfile.mkdtemp(prefix="tts_")); parts = []
    for i, c in enumerate(cues, 1):
        win = (c["endMs"] - c["startMs"]) / 1000.0
        dm, df = VOICES.get(lang, VOICES["en"])
        fem = c.get("gender") == "f" or (c.get("gender") is None and c["speaker"] in female)   # gender tag of script.srt wins
        voice = voices.get(c["speaker"]) or (df if fem else dm)
        mp3 = work / f"c{i:03d}.mp3"
        ok = asyncio.run(edge(c["text"], voice, mp3))
        if not ok:
            print(f"cue {i}: edge-tts failed, using gTTS"); gtts(c["text"], lang, mp3)
        wav = work / f"c{i:03d}.wav"; run(["ffmpeg", "-y", "-i", str(mp3), "-ar", "48000", "-ac", "1", str(wav)])
        d = dur(wav); fit = win - GAP; flt = []
        if d > fit:                                           # too long: speed up (max x1.5), then trim
            flt.append(f"atempo={min(d / fit, 1.5):.4f}")
        fin = work / f"f{i:03d}.wav"
        run(["ffmpeg", "-y", "-i", str(wav), "-af", ",".join(flt + [f"apad=whole_dur={win:.4f}", f"atrim=0:{win:.4f}"]), "-ar", "48000", "-ac", "1", str(fin)])
        parts.append(fin)
        if i % 20 == 0: print(f"tts {i}/{len(cues)}")
    lst = work / "list.txt"; lst.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts))
    out = proj / "assets" / "audio" / "voiceover.wav"; out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "pcm_s16le", str(out)])
    print(f"voiceover.wav {dur(out):.2f}s (script.srt {total:.2f}s)")

if __name__ == "__main__":
    main()
