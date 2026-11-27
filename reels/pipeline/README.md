# Fi-rose informative reels pipeline

Style: আদ্যোপান্ত-like 60-70s true-story reels. Bengali voiceover (ElevenLabs eleven_v4, voice "Rahat" 2jEx4hVYePE2ZcBrZfqj), 12 cinematic 16:9 images (gpt-image-2.5-sunburst, 3 prompts x 4 variations) panned to 9:16, dark cinematic music (eleven_music_v2_5), yellow title bar, big white Bengali captions timed from Scribe word timestamps, "Fi-rose" brand, closing question for comments.

- render.py SPEC.json — renders 1080x1920 30fps mp4. Spec: scenes [{img, s}], captions [{s,e,t}], title, voice, music, out, tmp, font (Bengali TTF, needs Pillow with raqm), brand_font.
- build_example.py — how captions/scene times are built from transcript words.
- reel1_spec.json / reel2_spec.json — specs of the first two reels; file names are ElevenLabs generation ids (flow miQ7c7IT9jn2BaSJxF4B).
- topics.md — topics already used (never repeat).
