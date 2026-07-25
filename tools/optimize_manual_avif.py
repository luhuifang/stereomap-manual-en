#!/usr/bin/env python3
"""Optimize the StereoMap offline manual (built GitBook site) for distribution.

What it does, in-place on a ``docs/`` directory:
  1. Classify every raster image (png/jpg/jpeg) as referenced / unreferenced by
     parsing all HTML/CSS/JS/JSON (URL-decode + HTML-unescape + case-fold).
  2. Convert referenced images to AVIF (lossy, 4:4:4 chroma). Per image, if the
     AVIF is NOT smaller than the original, the original is kept untouched.
  3. Rewrite every reference (.png/.jpg/.jpeg -> .avif) for converted images,
     handling spaces / & / parentheses / CJK via URL-encoding and HTML-entity forms.
  4. Delete unreferenced images.
  5. Gates: index.html exists, no broken image references, size within budget.

Usage:
  python optimize_manual_avif.py --docs <docs_dir> [--dry-run] [--quality 85]
      [--subsampling 4:4:4] [--speed 6] [--budget-mib 80] [--delete-unreferenced]

Requires: Pillow >= 10 and pillow-avif-plugin.
"""
import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, unquote

from PIL import Image

try:
    import pillow_avif  # noqa: F401  (registers AVIF with Pillow)
    AVIF_OK = True
except Exception:
    AVIF_OK = False

TEXT_EXTS = {".html", ".css", ".js", ".json", ".svg", ".xml", ".md", ".txt", ".map"}
RASTER_EXTS = {".png", ".jpg", ".jpeg"}
IMG_ANCHOR = "assets/"  # all manual images live under img/assets/


# ---------------------------------------------------------------------------
# reference detection
# ---------------------------------------------------------------------------
def load_text_files(docs):
    files = [p for p in docs.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTS]
    return files


def build_corpus(text_files, text_overrides=None):
    """Lowercased corpus (url-decoded + html-unescaped + raw) for detection."""
    text_overrides = text_overrides or {}
    parts = []
    for p in text_files:
        v = text_overrides.get(p)
        if v is None:
            try:
                v = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
        parts.append(html.unescape(unquote(v)).replace("\\", "/").lower())
        parts.append(v.replace("\\", "/").lower())
    return "\n".join(parts)


def detect_forms(rel_docs, rel_img):
    return {
        rel_docs, rel_img,
        quote(rel_docs), quote(rel_img),
        rel_docs.replace(" ", "%20"), rel_img.replace(" ", "%20"),
    }


def classify(docs, corpus):
    images = [p for p in (docs / "img").rglob("*")
              if p.is_file() and p.suffix.lower() in RASTER_EXTS]
    referenced, unreferenced = [], []
    for a in images:
        rel_docs = a.relative_to(docs).as_posix().lower()
        rel_img = a.relative_to(docs / "img").as_posix().lower()
        if any(c and c in corpus for c in detect_forms(rel_docs, rel_img)):
            referenced.append(a)
        else:
            unreferenced.append(a)
    return referenced, unreferenced


MALFORMED_ASSET_AMP_RX = re.compile(
    r'(?P<prefix>(?:\.\.?/)*(?:img/)?assets/[^"\'<>\r\n/]*?)/'
    r'(?P<suffix>&(?:amp;)?[^"\'<>\r\n/]*\.(?:png|jpe?g))',
    re.IGNORECASE,
)
MALFORMED_PAREN_ASSET_RX = re.compile(
    r'(?P<a_open><a\b[^>]*\bhref=")'
    r'(?P<href>(?:\.\.?/)*(?:img/)?assets/[^"]*\([^"]*)'
    r'(?P<a_middle>"[^>]*>\s*<img\b[^>]*\bsrc=")'
    r'(?P<src>(?:\.\.?/)*(?:img/)?assets/[^"]*\([^"]*)'
    r'(?P<a_close>"[^>]*>\s*</a>)'
    r'\.(?P<ext>png|jpe?g|avif|svg|gif)&gt;\)',
    re.IGNORECASE,
)


def repair_malformed_asset_refs(text_files, docs, dry_run):
    """Repair known GitBook asset truncations only when the target exists."""
    overrides = {}
    repaired_files = 0
    repaired_refs = 0
    for p in text_files:
        try:
            value = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        file_repairs = 0

        def repl(match):
            nonlocal file_repairs
            corrected = match.group("prefix") + match.group("suffix")
            target = resolve_ref(corrected, p, docs)
            if target is None or not target.exists():
                return match.group(0)
            file_repairs += 1
            return corrected

        normalized = MALFORMED_ASSET_AMP_RX.sub(repl, value)

        def repl_parenthesized(match):
            nonlocal file_repairs
            suffix = ")." + match.group("ext")
            href = match.group("href") + suffix
            src = match.group("src") + suffix
            target = resolve_ref(src, p, docs)
            if target is None or not target.exists():
                return match.group(0)
            file_repairs += 1
            return "".join((
                match.group("a_open"), href,
                match.group("a_middle"), src,
                match.group("a_close"),
            ))

        normalized = MALFORMED_PAREN_ASSET_RX.sub(repl_parenthesized, normalized)
        if not file_repairs:
            continue
        overrides[p] = normalized
        repaired_files += 1
        repaired_refs += file_repairs
        if not dry_run:
            p.write_text(normalized, encoding="utf-8")
    return overrides, repaired_files, repaired_refs


# ---------------------------------------------------------------------------
# reference rewrite
# ---------------------------------------------------------------------------
def _html_numeric_escape(s):
    """GitBook-style HTML escape: & < > -> entities, non-ASCII -> &#xNNNN;."""
    out = []
    for ch in s:
        o = ord(ch)
        if ch == "&":
            out.append("&amp;")
        elif ch == "<":
            out.append("&lt;")
        elif ch == ">":
            out.append("&gt;")
        elif o > 127:
            out.append("&#x%X;" % o)
        else:
            out.append(ch)
    return "".join(out)


def rewrite_forms(rel_img):
    """Literal reference forms (as they may appear in raw text) for rewriting.

    Anchored on assets/ (all manual refs include the assets/ path) to avoid
    substring collisions. GitBook encodes refs as: space -> %20, & -> &amp;,
    non-ASCII -> &#xNNNN;, parens/hyphens literal. We cover raw / space-only /
    fully-urlencoded / html-entity / gitbook-html forms.
    """
    b = rel_img
    return {
        b,                                              # raw: assets/foo bar&x.png
        b.replace(" ", "%20"),                          # space-only: assets/foo%20bar&x.png
        quote(b),                                       # full url-encode: assets/foo%20bar%26x.png
        html.escape(b),                                 # html-entity (ASCII): assets/foo bar&amp;x.png
        _html_numeric_escape(b.replace(" ", "%20")),    # GitBook: assets/foo%20bar&amp;x.png / &#x9875;
    }


def build_rewriter(converted_rel_imgs):
    forms = set()
    for rel in converted_rel_imgs:
        forms |= rewrite_forms(rel)
    # longest-first so "a (1).png" matches before "a.png"
    pats = sorted((re.escape(f) for f in forms if f), key=len, reverse=True)
    if not pats:
        return None, None
    # lookbehind: not preceded by word char / hyphen / dot (avoid substring hits)
    rx = re.compile(r"(?<![\w\-.])(" + "|".join(pats) + r")", re.IGNORECASE)

    def repl(m):
        return re.sub(r"\.(png|jpe?g)$", ".avif", m.group(0), flags=re.IGNORECASE)

    def rewrite(text):
        return rx.sub(repl, text)

    return rx, rewrite


# ---------------------------------------------------------------------------
# gates
# ---------------------------------------------------------------------------
# Include '#' and ';' so GitBook numeric entities such as &#x9875; remain
# part of the reference and are decoded before the existence check.
GATE_RX = re.compile(r"[\w\-. /%()&#;]*assets/[\w\-. /%()&#;]+\.(?:png|jpe?g|avif|svg|gif)",
                     re.IGNORECASE)


class AssetAttributeParser(HTMLParser):
    """Collect local asset references even when GitBook truncated the suffix."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []

    def handle_starttag(self, _tag, attrs):
        self._collect(attrs)

    def handle_startendtag(self, _tag, attrs):
        self._collect(attrs)

    def _collect(self, attrs):
        for name, value in attrs:
            if name.lower() not in {"href", "src"} or not value:
                continue
            normalized = html.unescape(unquote(value)).replace("\\", "/").lower()
            if "assets/" in normalized:
                self.refs.append(value)


def resolve_ref(ref, src_file, docs):
    ref = html.unescape(ref)
    ref = ref.split("?", 1)[0].split("#", 1)[0]
    ref = unquote(ref).replace("\\", "/")
    if ref.startswith("data:") or "://" in ref:
        return None
    cand = (src_file.parent / ref)
    try:
        cand = cand.resolve()
        cand.relative_to(docs.resolve())
    except (ValueError, OSError):
        return None
    return cand


def gate_refs(text_files, docs):
    """Return list of (file, ref) that point to a non-existent file."""
    broken = []
    for p in text_files:
        try:
            v = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        refs = {m.group(0) for m in GATE_RX.finditer(v)}
        if p.suffix.lower() in {".html", ".htm"}:
            parser = AssetAttributeParser()
            parser.feed(v)
            refs.update(parser.refs)
        for ref in sorted(refs):
            target = resolve_ref(ref, p, docs)
            if target is not None and not target.exists():
                broken.append((p.relative_to(docs).as_posix(), ref))
    return broken


def gate_avif_decode(docs):
    """Decode every generated AVIF and return (checked_count, failures)."""
    avif_files = sorted(docs.rglob("*.avif"))
    failures = []
    for path in avif_files:
        try:
            with Image.open(path) as image:
                image.load()
        except Exception as exc:
            failures.append((path.relative_to(docs).as_posix(), str(exc)))
    return len(avif_files), failures


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def mib(n):
    return n / 2 ** 20


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--docs", required=True, type=Path)
    ap.add_argument("--quality", type=int, default=85)
    ap.add_argument("--subsampling", default="4:4:4")
    ap.add_argument("--speed", type=int, default=6)
    ap.add_argument("--budget-mib", type=float, default=80.0)
    ap.add_argument("--delete-unreferenced", action="store_true",
                    help="actually delete unreferenced images (default: report only)")
    ap.add_argument("--dry-run", action="store_true",
                    help="no writes; report what would happen")
    ap.add_argument("--limit", type=int, default=0, help="process only first N referenced images")
    args = ap.parse_args()

    docs = args.docs.resolve()
    if not (docs / "index.html").exists():
        sys.exit(f"error: {docs} does not look like a manual docs dir (no index.html)")
    if not AVIF_OK and not args.dry_run:
        sys.exit("error: pillow-avif-plugin not available (pip install pillow-avif-plugin)")

    text_files = load_text_files(docs)
    text_overrides, repaired_files, repaired_refs = repair_malformed_asset_refs(
        text_files, docs, args.dry_run
    )
    if repaired_refs:
        action = "would fix" if args.dry_run else "fixed"
        print(f"[repair] malformed asset refs {action}={repaired_refs} "
              f"files={repaired_files}")
    corpus = build_corpus(text_files, text_overrides)
    referenced, unreferenced = classify(docs, corpus)

    def total(paths):
        return sum(p.stat().st_size for p in paths)

    before_tree = sum(p.stat().st_size for p in docs.rglob("*") if p.is_file())
    print(f"[scan] text files={len(text_files)}  images referenced={len(referenced)} "
          f"({mib(total(referenced)):.1f} MiB)  unreferenced={len(unreferenced)} "
          f"({mib(total(unreferenced)):.1f} MiB)  tree={mib(before_tree):.1f} MiB")

    # ---- convert referenced ----
    to_process = referenced[: args.limit] if args.limit else referenced
    converted_rel = []        # img-rel posix that became .avif
    kept_png = []             # referenced but avif not smaller
    src_bytes = avif_bytes = 0
    for i, img_path in enumerate(to_process, 1):
        rel_img = img_path.relative_to(docs / "img").as_posix()
        ob = img_path.stat().st_size
        src_bytes += ob
        try:
            im = Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"  [skip] {rel_img}: unreadable ({e})")
            kept_png.append(img_path)
            avif_bytes += ob
            continue
        buf = BytesIO()
        im.save(buf, "AVIF", quality=args.quality, speed=args.speed,
                subsampling=args.subsampling)
        nb = buf.tell()
        if nb < ob:
            converted_rel.append(rel_img)
            avif_bytes += nb
            if not args.dry_run:
                out = img_path.with_suffix(".avif")
                out.write_bytes(buf.getvalue())
                img_path.unlink()
        else:
            kept_png.append(img_path)
            avif_bytes += ob
        if i % 50 == 0:
            print(f"  ... {i}/{len(to_process)} encoded")

    print(f"[convert] referenced processed={len(to_process)}  ->avif={len(converted_rel)} "
          f"({mib(src_bytes):.1f}->{mib(avif_bytes - sum(p.stat().st_size for p in kept_png)):.1f} MiB)  "
          f"kept-png={len(kept_png)}")

    # ---- rewrite references ----
    rx, rewrite = build_rewriter(converted_rel)
    rewritten_files = 0
    total_repl = 0
    if rewrite and not args.dry_run:
        for p in text_files:
            try:
                v = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            nv, n = rx.subn(lambda m: re.sub(r"\.(png|jpe?g)$", ".avif", m.group(0),
                                             flags=re.IGNORECASE), v)
            if n:
                p.write_text(nv, encoding="utf-8")
                rewritten_files += 1
                total_repl += n
        print(f"[rewrite] files updated={rewritten_files}  refs rewritten={total_repl}")
    elif rewrite and args.dry_run:
        for p in text_files:
            v = text_overrides.get(p)
            if v is None:
                try:
                    v = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
            n = len(rx.findall(v))
            if n:
                rewritten_files += 1
                total_repl += n
        print(f"[rewrite][dry] files that would change={rewritten_files}  refs={total_repl}")

    # ---- delete unreferenced ----
    del_bytes = total(unreferenced)
    if args.delete_unreferenced and not args.dry_run:
        for p in unreferenced:
            p.unlink()
    print(f"[unreferenced] {len(unreferenced)} files ({mib(del_bytes):.1f} MiB) "
          f"{'deleted' if (args.delete_unreferenced and not args.dry_run) else 'reported (use --delete-unreferenced)'}")

    # ---- gates + report ----
    if not args.dry_run:
        after_tree = sum(p.stat().st_size for p in docs.rglob("*") if p.is_file())
        text_files_after = load_text_files(docs)
        broken = gate_refs(text_files_after, docs)
        avif_checked, avif_failures = gate_avif_decode(docs)
        print(f"\n[result] tree {mib(before_tree):.1f} -> {mib(after_tree):.1f} MiB "
              f"(saved {mib(before_tree - after_tree):.1f} MiB, "
              f"{(1 - after_tree / before_tree) * 100:.0f}%)")
        print(f"[gate] index.html={'ok' if (docs / 'index.html').exists() else 'MISSING'}  "
              f"broken_refs={len(broken)}  budget={args.budget_mib} MiB -> "
              f"{'ok' if mib(after_tree) <= args.budget_mib else 'OVER'}")
        print(f"[gate] avif_decode={avif_checked - len(avif_failures)}/{avif_checked} -> "
              f"{'ok' if not avif_failures else 'FAILED'}")
        if broken:
            print("[gate] first broken refs:")
            for f, r in broken[:20]:
                print(f"    {f} -> {r}")
        if avif_failures:
            print("[gate] first AVIF decode failures:")
            for path, error in avif_failures[:20]:
                print(f"    {path} -> {error}")
        report = {
            "before_mib": round(mib(before_tree), 2),
            "after_mib": round(mib(after_tree), 2),
            "referenced": len(referenced), "converted": len(converted_rel),
            "kept_png": len(kept_png), "unreferenced_deleted": len(unreferenced),
            "refs_rewritten": total_repl, "broken_refs": len(broken),
            "avif_checked": avif_checked,
            "avif_decode_failures": len(avif_failures),
            "quality": args.quality, "subsampling": args.subsampling,
        }
        # write report OUTSIDE docs/ (docs/ is shipped inside the installer)
        report_path = docs.parent / "_avif_report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print(f"[report] wrote {report_path}")
        if broken:
            sys.exit("gate FAILED: broken image references remain")
        if avif_failures:
            sys.exit("gate FAILED: generated AVIF files failed to decode")
        if mib(after_tree) > args.budget_mib:
            sys.exit(f"gate FAILED: tree {mib(after_tree):.1f} MiB over budget {args.budget_mib}")
    else:
        est = mib(before_tree) - mib(del_bytes) - (mib(src_bytes) * 0.81)  # ~81% saving on converted
        print(f"\n[dry] estimated tree after ~{est:.0f} MiB (rough, Q85-444 ~ -81% on converted)")

    print("done")


if __name__ == "__main__":
    main()
