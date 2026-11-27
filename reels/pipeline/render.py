#!/usr/bin/env python3
"""Render a 1080x1920 informative reel.
Usage: render.py spec.json
spec: {
  "images": [paths...], "voice": path, "music": path, "out": path,
  "title": str, "captions": [{"s":float,"e":float,"t":str}], "tail": 1.5,
  "font": path, "music_vol": 0.16
}
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit(f"failed: {' '.join(cmd[:6])}")
    return r


def dur(p):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p])
    return float(r.stdout.strip())


def wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def text_png(path, text, font_path, size, fill, stroke, box=None, maxw=940, spacing=1.25):
    font = ImageFont.truetype(font_path, size, layout_engine=ImageFont.Layout.RAQM)
    img = Image.new("RGBA", (W, 700), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lines = wrap(d, text, font, maxw)
    lh = int(size * spacing)
    total = lh * len(lines)
    y0 = 20
    if box:
        widest = max(d.textlength(l, font=font) for l in lines)
        pad = 28
        d.rounded_rectangle([(W - widest) / 2 - pad, y0 - 10, (W + widest) / 2 + pad, y0 + total + 18],
                            radius=22, fill=box)
    for i, l in enumerate(lines):
        tw = d.textlength(l, font=font)
        d.text(((W - tw) / 2, y0 + i * lh), l, font=font, fill=fill,
               stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    bbox = img.getbbox() or (0, 0, W, 10)
    img = img.crop((0, 0, W, bbox[3] + 10))
    img.save(path)
    return img.size[1]


def main():
    spec = json.load(open(sys.argv[1]))
    tmp = spec.get("tmp", "/tmp/reel")
    os.makedirs(tmp, exist_ok=True)
    font = spec["font"]
    vdur = dur(spec["voice"])
    total = vdur + spec.get("tail", 1.5) + 0.4
    lead = 0.4  # voice starts after this

    # overlays: title bar (whole video) + captions
    title_h = text_png(f"{tmp}/title.png", spec["title"], font, 50, (20, 20, 20, 255), 0,
                       box=(255, 204, 0, 235), maxw=900)
    brand_h = text_png(f"{tmp}/brand.png", spec.get("brand", "Fi-rose"), spec.get("brand_font", font), 38, (255, 255, 255, 230), 3)
    caps = []
    for i, c in enumerate(spec["captions"]):
        p = f"{tmp}/cap{i:03d}.png"
        h = text_png(p, c["t"].replace("...", ""), font, 68, (255, 255, 255, 255), 6, maxw=920)
        caps.append((c["s"] + lead, c["e"] + lead, p, h))

    scenes = spec["scenes"]
    n = len(scenes)
    parts = []
    for k, sc in enumerate(scenes):
        ip = sc["img"]
        t0 = 0.0 if k == 0 else sc["s"] + lead
        t1 = total if k == n - 1 else scenes[k + 1]["s"] + lead
        d = t1 - t0
        direction = 1 if k % 2 == 0 else -1
        x = f"(iw-{W})*(0.5{'-' if direction > 0 else '+'}0.18+{0.36 * direction}*t/{d:.3f})"
        vf = (f"[0:v]scale=-2:1980:flags=lanczos,crop={W}:{H}:x='{x}':y='(ih-{H})/2',"
              f"eq=contrast=1.06:saturation=0.9,vignette=PI/5,format=yuva420p[bg]")
        inputs = ["-framerate", str(FPS), "-loop", "1", "-t", f"{d:.3f}", "-i", ip,
                  "-i", f"{tmp}/title.png", "-i", f"{tmp}/brand.png"]
        chain = vf + f";[bg][1:v]overlay=(W-w)/2:150[v1];[v1][2:v]overlay=(W-w)/2:{H - 260}[v2]"
        last = "v2"
        idx = 3
        for (s, e, p, h) in caps:
            if e <= t0 or s >= t1:
                continue
            inputs += ["-i", p]
            chain += (f";[{last}][{idx}:v]overlay=(W-w)/2:{1220}:enable='between(t,{s - t0:.3f},{e - t0:.3f})'[o{idx}]")
            last = f"o{idx}"; idx += 1
        fade = ""
        if k == 0:
            fade = ",fade=t=in:st=0:d=0.3"
        if k == n - 1:
            fade += f",fade=t=out:st={d - 0.6:.3f}:d=0.6"
        chain += f";[{last}]format=yuv420p{fade}[out]"
        outp = f"{tmp}/part{k:02d}.mp4"
        run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", chain, "-map", "[out]",
             "-r", str(FPS), "-t", f"{d:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-pix_fmt", "yuv420p", f"{outp}.tmp.mp4"])
        os.rename(f"{outp}.tmp.mp4", outp)
        parts.append(outp)

    with open(f"{tmp}/list.txt", "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/list.txt",
         "-c", "copy", f"{tmp}/video.mp4"])
    mv = spec.get("music_vol", 0.16)
    af = (f"[1:a]adelay={int(lead * 1000)}|{int(lead * 1000)},volume=1.0[vo];"
          f"[2:a]volume={mv},afade=t=out:st={total - 2.5:.2f}:d=2.5[mu];"
          f"[vo][mu]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    out = spec["out"]
    run(["ffmpeg", "-y", "-v", "error", "-i", f"{tmp}/video.mp4", "-i", spec["voice"],
         "-stream_loop", "-1", "-i", spec["music"], "-filter_complex", af,
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-ar", "48000", "-t", f"{total:.3f}", "-movflags", "+faststart", f"{out}.tmp.mp4"])
    os.rename(f"{out}.tmp.mp4", out)
    print("OK", out, round(total, 2))


if __name__ == "__main__":
    main()
