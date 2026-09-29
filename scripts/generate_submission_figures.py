from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
ART = ROOT / "artifacts" / "prospective"
FIG.mkdir(parents=True, exist_ok=True)


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def svg_start(w: int, h: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        '<style>text{font-family:Arial,Helvetica,sans-serif;font-size:28px;fill:currentColor}.small{font-size:24px}.title{font-size:36px;font-weight:700}.label{font-weight:700}.axis{stroke:currentColor;stroke-width:2}.ci{stroke:currentColor;stroke-width:4}.box{fill:none;stroke:currentColor;stroke-width:2.5}.thin{fill:none;stroke:currentColor;stroke-width:2}.dot{fill:currentColor}.mean{fill:none;stroke:currentColor;stroke-width:4}</style>'
    ]


def write_svg(name: str, lines: list[str], extract: dict) -> None:
    lines.append("</svg>")
    svg = "\n".join(lines) + "\n"
    p = FIG / name
    p.write_text(svg, encoding="utf-8")
    ep = p.with_suffix(".extract.json")
    ep.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {
        "schema": "paper-a-figure-receipt-v1",
        "figure": p.name,
        "figure_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "extract": ep.name,
        "extract_sha256": hashlib.sha256(ep.read_bytes()).hexdigest(),
        "q0_read": False,
        "oos_read": False,
    }
    p.with_suffix(".receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fig1() -> None:
    w, h = 1040, 240
    s = svg_start(w, h)
    labels = [
        ("Formulation", 20),
        ("Local search", 180),
        ("Evidence", 340),
        ("Policy", 500),
        ("Successor", 660),
        ("Evaluator", 845),
    ]
    bw, y = 135, 85
    for lab, x in labels:
        s.append(f'<rect x="{x}" y="{y}" width="{bw}" height="72" rx="10" class="box"/>')
        s.append(f'<text x="{x+bw/2}" y="{y+46}" text-anchor="middle">{esc(lab)}</text>')
    for x1, x2 in [(155,180),(315,340),(475,500),(635,660),(795,845)]:
        s += [f'<line x1="{x1}" y1="121" x2="{x2-10}" y2="121" class="axis"/>',
              f'<polyline points="{x2-19},113 {x2-10},121 {x2-19},129" class="thin"/>']
    s.append('<text x="520" y="205" text-anchor="middle" class="small">Shared scientific authority remains outside controller control</text>')
    write_svg("F1_intervention_authority.svg", s, {"type":"design_schematic","source":"MANUSCRIPT/MAIN.md","q0_read":False,"oos_read":False})


def fig2() -> None:
    w, h = 1000, 560
    s = svg_start(w, h)
    s.append('<rect x="35" y="230" width="150" height="84" rx="10" class="box"/>')
    s.append('<text x="110" y="265" text-anchor="middle">Matched</text><text x="110" y="295" text-anchor="middle">replicate</text>')
    arms = [
        ("F","Fixed","baseline"),
        ("P","Periodic","P-F"),
        ("R","Rule + CEM","R-F / R-P"),
        ("L","LLM + CEM","L-R"),
        ("L0","LLM + proposals","L-L0"),
    ]
    for i,(arm,desc,contrast) in enumerate(arms):
        y=45+i*100
        s.append(f'<line x1="185" y1="272" x2="255" y2="{y+38}" class="thin"/>')
        s.append(f'<rect x="255" y="{y}" width="360" height="78" rx="10" class="box"/>')
        s.append(f'<text x="280" y="{y+34}" class="label">{arm}</text>')
        s.append(f'<text x="330" y="{y+34}">{esc(desc)}</text>')
        s.append(f'<text x="330" y="{y+65}" class="small">{esc(contrast)}</text>')
        s.append(f'<line x1="615" y1="{y+39}" x2="700" y2="{y+39}" class="axis"/>')
    s.append('<rect x="700" y="205" width="260" height="135" rx="10" class="box"/>')
    s.append('<text x="830" y="252" text-anchor="middle">Common evaluator</text>')
    s.append('<text x="830" y="287" text-anchor="middle">and court</text>')
    s.append('<text x="830" y="320" text-anchor="middle" class="small">same budget / firewall</text>')
    write_svg("F2_five_arm_design.svg", s, {"type":"design_schematic","arms":[a[0] for a in arms],"q0_read":False,"oos_read":False})


def fig3() -> None:
    w, h = 1180, 300
    s = svg_start(w, h)
    stages = [
        "Hypothesis",
        "Economic\nbasin",
        "Replicated\nbasin",
        "Net-positive\nrealization",
        "Formal\nadmission",
        "Scoped-new\nadmission",
    ]
    widths = [120,140,145,170,140,160]
    xs=[]; x=25
    for bw in widths:
        xs.append(x); x += bw + 42
    for i,(stage,bw,x) in enumerate(zip(stages,widths,xs)):
        s.append(f'<rect x="{x}" y="100" width="{bw}" height="92" rx="8" class="box"/>')
        lines=stage.split("\n")
        y0 = 133 if len(lines) == 1 else 126
        for j,line in enumerate(lines):
            s.append(f'<text x="{x+bw/2}" y="{y0+j*30}" text-anchor="middle">{esc(line)}</text>')
        if i < len(stages)-1:
            nx=xs[i+1]
            s.append(f'<line x1="{x+bw}" y1="146" x2="{nx-8}" y2="146" class="axis"/>')
            s.append(f'<polyline points="{nx-14},138 {nx-8},146 {nx-14},154" class="thin"/>')
    write_svg("F3_discovery_funnel.svg", s, {"type":"frozen_funnel_schematic","stages":stages,"authority":["V1_PROTOCOL.md","PV1M-016"],"q0_read":False,"oos_read":False})


def fig4() -> None:
    inf = json.loads((ART / "PAPER_V1_MAIN_V2_INFERENCE_RESULT.json").read_text(encoding="utf-8-sig"))
    rows = inf["frozen_inference_result"]["endpoint_results"]["primary_scoped_new_rate_per_1000_calls"]
    order = ["R-F","P-F","R-P","L-R","L-L0","L-F","L-P"]
    data = [{"contrast":k,"mean":rows[k]["mean_paired_difference"],"lo":rows[k]["ci_lower"],"hi":rows[k]["ci_upper"],"holm_p":rows[k]["holm_adjusted_p_value_within_endpoint_family"]} for k in order]
    xmin=min(x["lo"] for x in data); xmax=max(x["hi"] for x in data); span=xmax-xmin; xmin-=.08*span; xmax+=.08*span
    w,h=920,520; left,right,top,bottom=140,45,65,70; pw=w-left-right; ph=h-top-bottom
    sx=lambda x:left+(x-xmin)/(xmax-xmin)*pw
    s=svg_start(w,h)
    s.append('<text x="460" y="42" text-anchor="middle" class="small">Scoped-new admissions / 1,000 calls; 95% paired CI</text>')
    if xmin<=0<=xmax: s.append(f'<line x1="{sx(0):.1f}" y1="{top-5}" x2="{sx(0):.1f}" y2="{h-bottom}" class="thin"/>')
    for i,d in enumerate(data):
        y=top+35+i*(ph-45)/(len(data)-1)
        s.append(f'<text x="{left-18}" y="{y+5:.1f}" text-anchor="end" class="label">{d["contrast"]}</text>')
        s.append(f'<line x1="{sx(d["lo"]):.1f}" y1="{y:.1f}" x2="{sx(d["hi"]):.1f}" y2="{y:.1f}" class="ci"/>')
        s.append(f'<line x1="{sx(d["lo"]):.1f}" y1="{y-6:.1f}" x2="{sx(d["lo"]):.1f}" y2="{y+6:.1f}" class="axis"/>')
        s.append(f'<line x1="{sx(d["hi"]):.1f}" y1="{y-6:.1f}" x2="{sx(d["hi"]):.1f}" y2="{y+6:.1f}" class="axis"/>')
        s.append(f'<circle cx="{sx(d["mean"]):.1f}" cy="{y:.1f}" r="5" class="dot"/>')
    s.append(f'<line x1="{left}" y1="{h-bottom}" x2="{w-right}" y2="{h-bottom}" class="axis"/>')
    for t in [xmin,0,xmax]:
        if xmin<=t<=xmax:
            x=sx(t);s.append(f'<line x1="{x:.1f}" y1="{h-bottom}" x2="{x:.1f}" y2="{h-bottom+7}" class="axis"/>');s.append(f'<text x="{x:.1f}" y="{h-bottom+25}" text-anchor="middle" class="small">{t:.2f}</text>')
    s.append(f'<text x="{left+pw/2}" y="{h-18}" text-anchor="middle" class="small">Matched difference</text>')
    write_svg("F4_primary_contrast_intervals.svg", s, {"type":"forest_plot","endpoint":"primary_scoped_new_rate_per_1000_calls","rows":data,"authority":"PV1M-017","q0_read":False,"oos_read":False})


def fig5() -> None:
    mat=json.loads((ART/"PAPER_V1_MAIN_V2_FINAL_MATCHED_MATRIX.json").read_text(encoding="utf-8-sig"))
    arms=["F","P","R","L","L0"]; rows=mat["arm_rows"]
    vals={a:[r["scoped_new_admissions_per_1000_calls"] for r in rows if r["arm"]==a] for a in arms}
    ymax=max(max(v) for v in vals.values()); ymax=max(1.0,ymax*1.12)
    w,h=920,560; left,right,top,bottom=90,40,60,70; pw=w-left-right; ph=h-top-bottom
    sy=lambda y:top+(1-y/ymax)*ph
    xpos={a:left+(i+.5)*pw/len(arms) for i,a in enumerate(arms)}
    s=svg_start(w,h)
    s.append('<text x="460" y="42" text-anchor="middle" class="small">Ten matched replicates per arm</text>')
    for frac in [0,.25,.5,.75,1]:
        yv=ymax*frac; y=sy(yv); s.append(f'<line x1="{left}" y1="{y:.1f}" x2="{w-right}" y2="{y:.1f}" class="thin"/>'); s.append(f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" class="small">{yv:.2f}</text>')
    jit=[-24,-18,-12,-6,-2,2,6,12,18,24]
    extract=[]
    for a in arms:
        x=xpos[a]; vs=vals[a]; mean=sum(vs)/len(vs)
        for j,v in enumerate(vs):
            s.append(f'<circle cx="{x+jit[j]:.1f}" cy="{sy(v):.1f}" r="4" class="dot"/>')
            extract.append({"arm":a,"replicate":f"M{j+1:02d}","value":v})
        ym=sy(mean)
        s.append(f'<line x1="{x-32:.1f}" y1="{ym:.1f}" x2="{x+32:.1f}" y2="{ym:.1f}" class="ci"/>')
        s.append(f'<text x="{x:.1f}" y="{h-bottom+28}" text-anchor="middle" class="label">{a}</text>')
    s.append(f'<text x="22" y="{top+ph/2}" transform="rotate(-90 22 {top+ph/2})" text-anchor="middle" class="small">Scoped-new / 1,000 calls</text>')
    write_svg("F5_replicate_primary_outcomes.svg", s, {"type":"replicate_dot_plot","endpoint":"scoped_new_admissions_per_1000_calls","values":extract,"authority":"PV1M-016","q0_read":False,"oos_read":False})


def fig9() -> None:
    f=json.loads((ART/"PAPER_LG_FOLLOWUP_FINAL_RESULT.json").read_text(encoding="utf-8-sig"))
    diffs=f["paired_differences"]; reps=[x["replicate_id"] for x in f["replicates"]]
    ymin=min(-3,min(diffs)-1); ymax=max(8,max(diffs)+1)
    w,h=1050,520; plot_left=390; right=55; top=70; bottom=70; pw=w-plot_left-right; ph=h-top-bottom
    sx=lambda i:plot_left+(i+.5)*pw/len(diffs); sy=lambda y:top+(ymax-y)/(ymax-ymin)*ph
    s=svg_start(w,h)
    s.append('<rect x="35" y="95" width="300" height="250" rx="10" class="box"/>')
    s.append('<text x="185" y="125" text-anchor="middle" class="label">Development-only diagnostic</text>')
    s.append('<text x="185" y="165" text-anchor="middle" class="title">15 / 15</text>')
    s.append('<text x="185" y="205" text-anchor="middle">Representation change</text>')
    s.append('<text x="185" y="240" text-anchor="middle">→ next SCREEN8</text>')
    s.append('<text x="185" y="295" text-anchor="middle" class="small">development only</text>')
    s.append(f'<line x1="{plot_left}" y1="{sy(0):.1f}" x2="{w-right}" y2="{sy(0):.1f}" class="axis"/>')
    pts=[]
    for i,(rep,d) in enumerate(zip(reps,diffs)):
        x=sx(i); y=sy(d); pts.append(f"{x:.1f},{y:.1f}")
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" class="dot"/>')
        s.append(f'<text x="{x:.1f}" y="{h-bottom+25}" text-anchor="middle" class="small">{rep}</text>')
        s.append(f'<text x="{x:.1f}" y="{y-12:.1f}" text-anchor="middle" class="small">{d:+d}</text>')
    s.append(f'<polyline points="{" ".join(pts)}" class="thin"/>')
    mean=f["mean_paired_difference"]; lo,hi=f["paired_t_95ci"]; xm=w-80
    s.append(f'<line x1="{xm}" y1="{sy(lo):.1f}" x2="{xm}" y2="{sy(hi):.1f}" class="ci"/>')
    s.append(f'<circle cx="{xm}" cy="{sy(mean):.1f}" r="6" class="mean"/>')
    s.append(f'<text x="{plot_left+pw/2}" y="{h-18}" text-anchor="middle" class="small">Fresh LG-L SCREEN8 difference (lower is better)</text>')
    s.append(f'<text x="{plot_left+pw/2}" y="45" text-anchor="middle" class="small">mean {mean:+.3f}; p={f["exact_two_sided_signflip_p"]:.4f}; gate FAIL</text>')
    write_svg("F9_diagnostic_guard_followup.svg", s, {"type":"followup_paired_difference","development_association":{"representation_change_next_screen8":[15,15],"evidence_role":"development_only"},"replicates":reps,"paired_differences":diffs,"mean":mean,"ci":[lo,hi],"exact_signflip_p":f["exact_two_sided_signflip_p"],"positive_gate":f["positive_claim_gate"],"authority":["PV1F-002","PV1F-006"],"q0_read":False,"oos_read":False})


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5(); fig9()
    print("generated", sorted(p.name for p in FIG.glob("F*.svg")))
