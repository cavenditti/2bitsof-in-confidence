#!/usr/bin/env python3
"""
fetch_memes.py — download meme templates with meaningful filenames + a manifest.

Source: Imgflip public API (https://api.imgflip.com/get_memes), ~100 top templates.
No third-party deps (urllib/json from stdlib). Idempotent: re-running skips files
already present. Writes ./memes/<slug>.<ext> and ./memes/manifest.json (+ index.md).

The manifest is the thing you feed your agent. Each entry:
  { file, name, slug, width, height, text_boxes, source_url }
text_boxes = how many caption slots the template has (1 = one-liner, 2 = top/bottom,
3+ = multi-panel) — use it to match a template to the structure of the joke.

Usage:
  python3 fetch_memes.py                  # imgflip top ~100 -> ./memes
  python3 fetch_memes.py -o slides_memes  # custom output dir
  python3 fetch_memes.py --from memes.json  # offline: read an imgflip-shaped json
"""

import argparse, json, os, re, sys, time, urllib.request, urllib.error

API = "https://api.imgflip.com/get_memes"
UA = "meme-fetcher/1.0 (personal presentation use)"


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[''\"]", "", s)  # drop apostrophes/quotes
    s = re.sub(r"[^a-z0-9]+", "-", s)  # everything else -> hyphen
    return re.sub(r"-{2,}", "-", s).strip("-") or "meme"


def ext_of(url: str) -> str:
    m = re.search(r"\.(jpg|jpeg|png|gif|webp)(?:\?|$)", url, re.I)
    return ("." + m.group(1).lower()) if m else ".jpg"


def get_json(url_or_path: str) -> dict:
    if os.path.exists(url_or_path):
        with open(url_or_path) as f:
            return json.load(f)
    req = urllib.request.Request(url_or_path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def download(url: str, dest: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--outdir", default="memes")
    ap.add_argument(
        "--from",
        dest="src",
        default=API,
        help="API URL or a local imgflip-shaped JSON file",
    )
    ap.add_argument("--sleep", type=float, default=0.2, help="politeness delay (s)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    payload = get_json(args.src)
    memes = (
        payload.get("data", {}).get("memes")
        if "data" in payload
        else payload.get("memes", [])
    )
    if not memes:
        sys.exit("No memes in payload. Check the source.")

    manifest, seen = [], {}
    for m in memes:
        name = m["name"]
        slug = slugify(name)
        slug = (lambda s: s if seen.setdefault(s, 0) == 0 else f"{s}-{seen[s]}")(slug)
        seen[slug] = seen.get(slug, 0) + 1
        fname = slug + ext_of(m["url"])
        dest = os.path.join(args.outdir, fname)
        try:
            if os.path.exists(dest) and os.path.getsize(dest) > 0:
                print(f"skip  {fname}")
            else:
                n = download(m["url"], dest)
                print(f"ok    {fname:42s} {n:>7d} B")
                time.sleep(args.sleep)
        except (urllib.error.URLError, OSError) as e:
            print(f"FAIL  {fname}: {e}", file=sys.stderr)
            continue
        manifest.append(
            {
                "file": fname,
                "name": name,
                "slug": slug,
                "width": int(m.get("width", 0)),
                "height": int(m.get("height", 0)),
                "text_boxes": int(m.get("box_count", 0)),
                "source_url": m["url"],
            }
        )

    with open(os.path.join(args.outdir, "manifest.json"), "w") as f:
        json.dump({"count": len(manifest), "memes": manifest}, f, indent=2)
    with open(os.path.join(args.outdir, "index.md"), "w") as f:
        f.write(f"# {len(manifest)} meme templates\n\n")
        f.write("| file | name | text_boxes | w×h |\n|---|---|---|---|\n")
        for x in manifest:
            f.write(
                f"| `{x['file']}` | {x['name']} | {x['text_boxes']} | {x['width']}×{x['height']} |\n"
            )

    print(
        f"\n{len(manifest)} files -> {args.outdir}/  (manifest.json, index.md written)"
    )


if __name__ == "__main__":
    main()
