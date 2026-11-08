"""Draw the prop library: flat ink-outlined SVG objects in the same style as the cast.

    python scripts/make_props.py            # (re)writes assets/props/*.svg, never touches existing files unless --force

A line of narration that mentions an object should be able to SHOW it ("Her phone buzzed" -> phone).
Five props were not enough, so every story ended up with the same envelope. These are the everyday
objects the three topics keep talking about: money, work, time, ideas, evidence.
Each prop is centred, about 200 px wide, thick ink outline, 2-3 flat colours, no text or logos.
"""
import argparse
import pathlib

INK = "#241726"
S = f'stroke="{INK}" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"'
T = f'stroke="{INK}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"'

PROPS = {
    "phone": ('0 0 120 200', f'<rect x="12" y="8" width="96" height="184" rx="18" fill="#2c2f3d" {S}/>'
              f'<rect x="22" y="30" width="76" height="134" rx="6" fill="#8fd3ff"/>'
              f'<rect x="34" y="48" width="52" height="10" rx="5" fill="#ffffff" opacity=".85"/>'
              f'<rect x="34" y="66" width="36" height="10" rx="5" fill="#ffffff" opacity=".7"/>'
              f'<circle cx="60" cy="178" r="6" fill="#5a5f74"/>'),
    "laptop": ('0 0 240 170', f'<rect x="38" y="10" width="164" height="110" rx="10" fill="#3a3f52" {S}/>'
               f'<rect x="50" y="22" width="140" height="86" rx="4" fill="#9ed8ff"/>'
               f'<path d="M14 128 L226 128 L210 156 L30 156 Z" fill="#c9ccd6" {S}/>'),
    "coffee": ('0 0 180 200', f'<path d="M30 60 L150 60 L136 186 L44 186 Z" fill="#f4efe6" {S}/>'
               f'<path d="M36 96 L144 96 L140 130 L40 130 Z" fill="#b5523a"/>'
               f'<rect x="22" y="44" width="136" height="22" rx="8" fill="#6b3f2a" {S}/>'
               f'<path d="M70 32 Q60 18 72 6 M100 32 Q90 18 102 6" fill="none" stroke="#a9a3b3" stroke-width="5" stroke-linecap="round"/>'),
    "cash": ('0 0 240 150', f'<rect x="26" y="34" width="190" height="96" rx="8" fill="#7cbf73" {S} transform="rotate(-8 120 82)"/>'
             f'<rect x="20" y="26" width="190" height="96" rx="8" fill="#93d18a" {S}/>'
             f'<circle cx="115" cy="74" r="26" fill="#c9ecc2" {T}/>'
             f'<rect x="36" y="42" width="22" height="64" rx="4" fill="#c9ecc2"/>'
             f'<rect x="172" y="42" width="22" height="64" rx="4" fill="#c9ecc2"/>'),
    "coins": ('0 0 200 180', f'<ellipse cx="70" cy="140" rx="54" ry="20" fill="#e3b341" {S}/>'
              f'<rect x="16" y="110" width="108" height="30" fill="#e3b341"/><ellipse cx="70" cy="110" rx="54" ry="20" fill="#f2cd5c" {S}/>'
              f'<ellipse cx="136" cy="128" rx="54" ry="20" fill="#e3b341" {S}/>'
              f'<rect x="82" y="70" width="108" height="58" fill="#e3b341"/><ellipse cx="136" cy="70" rx="54" ry="20" fill="#f2cd5c" {S}/>'
              f'<path d="M82 70 L82 128 M190 70 L190 128" {S}/>'),
    "card": ('0 0 230 150', f'<rect x="12" y="14" width="206" height="124" rx="16" fill="#4f6bd8" {S}/>'
             f'<rect x="12" y="40" width="206" height="22" fill="#26306b"/>'
             f'<rect x="32" y="84" width="40" height="30" rx="6" fill="#f2cd5c" {T}/>'
             f'<rect x="96" y="96" width="96" height="10" rx="5" fill="#c9d3ff"/>'),
    "piggybank": ('0 0 230 180', f'<ellipse cx="112" cy="98" rx="86" ry="62" fill="#f4a7b9" {S}/>'
                  f'<circle cx="190" cy="94" r="24" fill="#f19aaf" {S}/><circle cx="184" cy="90" r="4" fill="{INK}"/><circle cx="196" cy="90" r="4" fill="{INK}"/>'
                  f'<path d="M74 148 L70 172 M150 148 L154 172" {S}/><path d="M74 46 L88 22 L104 44" fill="#f19aaf" {S}/>'
                  f'<rect x="96" y="34" width="40" height="9" rx="4" fill="{INK}"/><circle cx="150" cy="80" r="6" fill="{INK}"/>'),
    "receipt": ('0 0 150 220', f'<path d="M20 10 L130 10 L130 206 L112 194 L94 206 L76 194 L58 206 L40 194 L20 206 Z" fill="#fbf8f1" {S}/>'
                + "".join(f'<rect x="36" y="{y}" width="{w}" height="9" rx="4" fill="#b9b2c4"/>' for y, w in ((36, 78), (60, 60), (84, 70), (108, 50), (132, 74)))
                + f'<rect x="36" y="160" width="78" height="12" rx="5" fill="{INK}"/>'),
    "chart_up": ('0 0 230 180', f'<rect x="10" y="10" width="210" height="160" rx="12" fill="#fbf8f1" {S}/>'
                 f'<path d="M30 140 L80 104 L118 120 L190 46" fill="none" stroke="#3aa65a" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>'
                 f'<path d="M160 40 L196 40 L196 76" fill="none" stroke="#3aa65a" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>'),
    "chart_down": ('0 0 230 180', f'<rect x="10" y="10" width="210" height="160" rx="12" fill="#fbf8f1" {S}/>'
                   f'<path d="M30 46 L84 84 L120 66 L190 136" fill="none" stroke="#d8473d" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>'
                   f'<path d="M158 140 L196 140 L196 102" fill="none" stroke="#d8473d" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>'),
    "clock": ('0 0 200 200', f'<circle cx="100" cy="100" r="86" fill="#fbf8f1" {S}/>'
              + "".join(f'<rect x="96" y="22" width="8" height="18" rx="3" fill="{INK}" transform="rotate({a} 100 100)"/>' for a in range(0, 360, 30))
              + f'<path d="M100 100 L100 52 M100 100 L136 118" {S}/><circle cx="100" cy="100" r="8" fill="{INK}"/>'),
    "calendar": ('0 0 200 200', f'<rect x="16" y="28" width="168" height="160" rx="14" fill="#fbf8f1" {S}/>'
                 f'<rect x="16" y="28" width="168" height="44" rx="14" fill="#d8473d" {S}/>'
                 f'<path d="M56 14 L56 44 M144 14 L144 44" {S}/>'
                 + "".join(f'<rect x="{34 + 34 * (k % 4)}" y="{88 + 30 * (k // 4)}" width="22" height="18" rx="4" fill="#cfc8da"/>' for k in range(12))),
    "lightbulb": ('0 0 160 210', f'<path d="M80 12 C130 12 150 52 140 86 C132 112 108 122 106 150 L54 150 C52 122 28 112 20 86 C10 52 30 12 80 12 Z" fill="#ffe27a" {S}/>'
                  f'<rect x="52" y="150" width="56" height="20" rx="5" fill="#b9b2c4" {T}/><rect x="56" y="170" width="48" height="18" rx="5" fill="#9a93a8" {T}/>'
                  f'<path d="M64 120 L72 84 L88 84 L96 120" fill="none" stroke="#e0a43a" stroke-width="6" stroke-linecap="round"/>'),
    "question": ('0 0 150 210', f'<path d="M30 66 C30 24 120 18 122 66 C124 104 78 106 78 140" fill="none" stroke="{INK}" stroke-width="30" stroke-linecap="round"/>'
                 f'<path d="M30 66 C30 24 120 18 122 66 C124 104 78 106 78 140" fill="none" stroke="#ffcf4a" stroke-width="16" stroke-linecap="round"/>'
                 f'<circle cx="78" cy="184" r="17" fill="#ffcf4a" {S}/>'),
    "exclaim": ('0 0 110 210', f'<path d="M55 20 L55 132" stroke="{INK}" stroke-width="34" stroke-linecap="round"/>'
                f'<path d="M55 20 L55 132" stroke="#ff6b4a" stroke-width="20" stroke-linecap="round"/>'
                f'<circle cx="55" cy="182" r="18" fill="#ff6b4a" {S}/>'),
    "document": ('0 0 170 210', f'<path d="M16 10 L118 10 L154 46 L154 200 L16 200 Z" fill="#fbf8f1" {S}/>'
                 f'<path d="M118 10 L118 46 L154 46" fill="#e8e2ef" {S}/>'
                 + "".join(f'<rect x="36" y="{y}" width="{w}" height="10" rx="5" fill="#b9b2c4"/>' for y, w in ((70, 96), (94, 82), (118, 96), (142, 64), (166, 88)))),
    "briefcase": ('0 0 230 180', f'<rect x="14" y="48" width="202" height="122" rx="14" fill="#7a4e32" {S}/>'
                  f'<path d="M80 48 L80 26 Q80 16 90 16 L140 16 Q150 16 150 26 L150 48" fill="none" {S}/>'
                  f'<rect x="14" y="90" width="202" height="12" fill="#5c3922"/><rect x="100" y="84" width="30" height="26" rx="5" fill="#f2cd5c" {T}/>'),
    "shopping_bag": ('0 0 180 210', f'<path d="M24 64 L156 64 L146 200 L34 200 Z" fill="#f08a5d" {S}/>'
                     f'<path d="M60 76 L60 50 Q60 18 90 18 Q120 18 120 50 L120 76" fill="none" {S}/>'),
    "gift": ('0 0 200 200', f'<rect x="20" y="78" width="160" height="110" rx="8" fill="#e05a6b" {S}/>'
             f'<rect x="12" y="56" width="176" height="32" rx="8" fill="#ec7686" {S}/>'
             f'<rect x="88" y="56" width="24" height="132" fill="#ffd166"/>'
             f'<path d="M100 56 C70 20 40 40 70 56 M100 56 C130 20 160 40 130 56" fill="none" {S}/>'),
    "lock": ('0 0 170 210', f'<path d="M44 92 L44 62 Q44 18 85 18 Q126 18 126 62 L126 92" fill="none" stroke="{INK}" stroke-width="22"/>'
             f'<path d="M44 92 L44 62 Q44 18 85 18 Q126 18 126 62 L126 92" fill="none" stroke="#b9b2c4" stroke-width="9"/>'
             f'<rect x="20" y="88" width="130" height="110" rx="14" fill="#f2cd5c" {S}/>'
             f'<circle cx="85" cy="134" r="14" fill="{INK}"/><rect x="79" y="140" width="12" height="30" rx="4" fill="{INK}"/>'),
    "newspaper": ('0 0 230 180', f'<rect x="14" y="14" width="202" height="152" rx="8" fill="#f4f0e6" {S}/>'
                  f'<rect x="32" y="32" width="166" height="22" rx="4" fill="{INK}"/>'
                  f'<rect x="32" y="68" width="76" height="76" rx="4" fill="#cfc8da"/>'
                  + "".join(f'<rect x="122" y="{y}" width="76" height="9" rx="4" fill="#b9b2c4"/>' for y in (70, 90, 110, 130))),
    "camera": ('0 0 230 170', f'<rect x="14" y="40" width="202" height="118" rx="16" fill="#3a3f52" {S}/>'
               f'<path d="M70 40 L86 16 L144 16 L160 40" fill="#2c2f3d" {S}/>'
               f'<circle cx="115" cy="98" r="40" fill="#9ed8ff" {S}/><circle cx="115" cy="98" r="18" fill="#2c2f3d"/>'
               f'<rect x="170" y="56" width="26" height="14" rx="4" fill="#ffd166"/>'),
    "moneybag": ('0 0 200 220', f'<path d="M70 52 C20 90 14 206 100 206 C186 206 180 90 130 52 Z" fill="#d2b06a" {S}/>'
                 f'<path d="M70 52 L60 22 L100 34 L140 22 L130 52 Z" fill="#c09a52" {S}/>'
                 f'<path d="M100 96 L100 176 M124 112 Q100 96 82 112 Q74 132 100 138 Q126 144 118 164 Q100 180 76 162" fill="none" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>'),
    "wallet": ('0 0 230 170', f'<rect x="14" y="34" width="202" height="122" rx="16" fill="#8a5a3c" {S}/>'
               f'<path d="M14 64 L190 18 L200 50" fill="#a46e4b" {S}/>'
               f'<rect x="150" y="80" width="66" height="44" rx="10" fill="#6e452c" {S}/><circle cx="174" cy="102" r="7" fill="#f2cd5c"/>'),
    "heart": ('0 0 200 180', f'<path d="M100 166 C30 120 10 86 20 54 C30 20 76 14 100 46 C124 14 170 20 180 54 C190 86 170 120 100 166 Z" fill="#ef5a6f" {S}/>'),
    "warning": ('0 0 220 200', f'<path d="M110 14 L206 184 L14 184 Z" fill="#ffcf4a" {S}/>'
                f'<path d="M110 70 L110 128" stroke="{INK}" stroke-width="16" stroke-linecap="round"/><circle cx="110" cy="158" r="10" fill="{INK}"/>'),
    "pizza": ('0 0 210 200', f'<path d="M20 30 L190 30 L105 190 Z" fill="#f2c25c" {S}/>'
              f'<path d="M20 30 L190 30" stroke="#c9873a" stroke-width="20" stroke-linecap="round"/>'
              f'<circle cx="86" cy="70" r="14" fill="#d8473d"/><circle cx="128" cy="78" r="12" fill="#d8473d"/><circle cx="104" cy="120" r="11" fill="#d8473d"/>'),
    "pill_bottle": None,   # deliberately absent: no medical props (channel avoids health advice)
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(__file__).resolve().parent.parent / "assets" / "props"
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for name, spec in PROPS.items():
        if spec is None:
            continue
        p = out / f"{name}.svg"
        if p.exists() and not a.force:
            continue
        vb, body = spec
        w, h = vb.split()[2:]
        p.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="{w}" height="{h}">{body}</svg>\n', encoding="utf-8")
        made.append(name)
    print(f"props written: {len(made)} ({', '.join(made)})")
    print(f"library now: {', '.join(sorted(x.stem for x in out.glob('*.svg')))}")


if __name__ == "__main__":
    main()
