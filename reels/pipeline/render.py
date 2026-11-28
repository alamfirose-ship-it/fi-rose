#!/usr/bin/env python3
"""Render a 1080x1920 informative reel (Mayajaal-style layout).
Layout: black frame; top band = white rounded hook box (title + optional emoji, whole video);
middle band = slow-panning image; lower band = word-synced Bengali subtitles; small "Fi-rose" brand.
Usage: render.py spec.json
spec: {
  "images": [paths...], "voice": path, "music": path, "out": path,
  "title": str, "captions": [{"s":float,"e":float,"t":str}], "tail": 1.5,
  "font": path, "music_vol": 0.16, "emoji": "😱" (optional, drawn after title),
  "emoji_font": path (default NotoColorEmoji)
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


def hook_png(path, text, font_path, emoji=None, emoji_font=None, size=62, maxw=860):
    font = ImageFont.truetype(font_path, size, layout_engine=ImageFont.Layout.RAQM)
    tmp = Image.new("RGBA", (W, 10)); d = ImageDraw.Draw(tmp)
    em = None
    if emoji:
        ef = ImageFont.truetype(emoji_font or "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)
        ei = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(ei).text((10, 10), emoji, font=ef, embedded_color=True)
        ei = ei.crop(ei.getbbox()); es = int(size * 1.1)
        em = ei.resize((int(ei.width * es / ei.height), es), Image.LANCZOS)
    ew = (em.width + 14) if em else 0
    lines = wrap(d, text, font, maxw - ew)
    lh = int(size * 1.4)
    widths = [d.textlength(l, font=font) for l in lines]
    widths[-1] += ew
    bw = int(max(widths)) + 2 * 44
    bh = lh * len(lines) + 2 * 30
    img = Image.new("RGBA", (W, bh + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x0 = (W - bw) // 2
    d.rounded_rectangle([x0, 0, x0 + bw, bh], radius=34, fill=(255, 255, 255, 255))
    for i, l in enumerate(lines):
        tw = widths[i]
        x = (W - tw) / 2; y = 30 + i * lh - int(size * 0.08)
        d.text((x, y), l, font=font, fill=(10, 10, 10, 255))
        if em and i == len(lines) - 1:
            img.alpha_composite(em, (int(x + d.textlength(l, font=font) + 14), int(30 + i * lh + (lh - em.height) / 2)))
    img.save(path)
    return bh


def main():
    spec = json.load(open(sys.argv[1]))
    tmp = spec.get("tmp", "/tmp/reel")
    os.makedirs(tmp, exist_ok=True)
    font = spec["font"]
    vdur = dur(spec["voice"])
    total = vdur + spec.get("tail", 1.5) + 0.4
    lead = 0.4  # voice starts after this

    # overlays: title bar (whole video) + captions
    title_h = hook_png(f"{tmp}/title.png", spec["title"], font, spec.get("emoji"), spec.get("emoji_font"))
    TOP, MID_H = 560, 780  # middle image band: y=TOP..TOP+MID_H
    title_y = max(40, (TOP - title_h) // 2 + 20)
    brand_h = text_png(f"{tmp}/brand.png", spec.get("brand", "Fi-rose"), spec.get("brand_font", font), 38, (255, 255, 255, 230), 3)
    caps = []
    for i, c in enumerate(spec["captions"]):
        p = f"{tmp}/cap{i:03d}.png"
        h = text_png(p, c["t"].replace("...", ""), font, 70, (255, 255, 255, 255), 5, maxw=960)
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
        vf = (f"[0:v]scale=-2:{int(MID_H * 1.12)}:flags=lanczos,crop={W}:{MID_H}:x='{x}':y='(ih-{MID_H})/2',"
              f"eq=contrast=1.06:saturation=0.92,vignette=PI/6,format=yuva420p[img];"
              f"color=c=black:s={W}x{H}:r={FPS}:d={d:.3f}[base];[base][img]overlay=0:{TOP}:shortest=1[bg]")
        inputs = ["-framerate", str(FPS), "-loop", "1", "-t", f"{d:.3f}", "-i", ip,
                  "-i", f"{tmp}/title.png", "-i", f"{tmp}/brand.png"]
        chain = vf + f";[bg][1:v]overlay=(W-w)/2:{title_y}[v1];[v1][2:v]overlay=(W-w)/2:{H - 130}[v2]"
        last = "v2"
        idx = 3
        for (s, e, p, h) in caps:
            if e <= t0 or s >= t1:
                continue
            inputs += ["-i", p]
            chain += (f";[{last}][{idx}:v]overlay=(W-w)/2:{TOP + MID_H + 70}:enable='between(t,{s - t0:.3f},{e - t0:.3f})'[o{idx}]")
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
