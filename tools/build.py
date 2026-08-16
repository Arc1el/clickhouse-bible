#!/usr/bin/env python3
"""bible/*.md → docs/ 멀티 페이지 정적 사이트 빌더 (GitHub Pages용).

사용법 (저장소 루트에서):
    python3 tools/build.py

생성물:
    docs/index.html          랜딩 페이지 (목차)
    docs/<슬러그>.html       장별 페이지 21개
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIBLE = ROOT / 'bible'
TOOLS = Path(__file__).resolve().parent
DOCS = ROOT / 'docs'

ORDER = [
    '00-exam-guide.md', '01-database-basics.md', '02-setup.md', '03-sql-first-steps.md',
    '04-data-types.md', '05-mergetree.md', '06-table-design.md', '07-dictionary.md',
    '08-inserting-data.md', '09-select-deep-dive.md', '10-functions.md',
    '11-aggregation-window.md', '12-materialized-views.md', '13-projections-skipping-indexes.md',
    '14-dedup-mutations.md', '15-other-engines-kafka.md', '16-performance.md',
    '17-replication-scaling.md', '18-exam-strategy.md', '19-mock-exam.md', '20-cheatsheet.md',
]
GROUPS = [
    ('시작하기', ORDER[0:4]),
    ('영역 1 · 데이터 모델링', ORDER[4:8]),
    ('영역 2 · 데이터 삽입', ORDER[8:9]),
    ('영역 3 · 데이터 분석', ORDER[9:12]),
    ('영역 4 · 성능 최적화', ORDER[12:14]),
    ('영역 5 · 중복 제거', ORDER[14:15]),
    ('심화 · 실무', ORDER[15:18]),
    ('마무리', ORDER[18:21]),
]

def slug(fname):
    return fname.replace('.md', '')

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'`([^`]+)`', lambda m: '<code>%s</code>' % m.group(1), s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
    return s

def convert(md):
    """마크다운 본문 → HTML (h1은 건너뛰고 별도 처리)"""
    out = []
    lines = md.split('\n')
    i = 0
    in_ul = in_ol = in_bq = False
    sec_n = 0

    def close_lists():
        nonlocal in_ul, in_ol, in_bq
        if in_ul: out.append('</ul>'); in_ul = False
        if in_ol: out.append('</ol>'); in_ol = False
        if in_bq: out.append('</blockquote>'); in_bq = False

    while i < len(lines):
        ln = lines[i]
        if ln.startswith('```'):
            close_lists()
            lang = ln[3:].strip() or 'text'
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                buf.append(lines[i]); i += 1
            out.append('<pre class="code" data-lang="%s"><code>%s</code></pre>'
                       % (html.escape(lang), html.escape('\n'.join(buf))))
            i += 1
            continue
        if ln.strip().startswith('<details>') or ln.strip().startswith('</details>') \
           or ln.strip().startswith('<summary>'):
            close_lists()
            out.append(ln.strip())
            i += 1
            continue
        if ln.strip().startswith('|') and i + 1 < len(lines) and re.match(r'^\s*\|[\s:|-]+\|\s*$', lines[i+1]):
            close_lists()
            header = [c.strip() for c in ln.strip().strip('|').split('|')]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            t = ['<div class="tablewrap"><table><thead><tr>']
            t += ['<th>%s</th>' % inline(h) for h in header]
            t.append('</tr></thead><tbody>')
            for r in rows:
                t.append('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in r) + '</tr>')
            t.append('</tbody></table></div>')
            out.append(''.join(t))
            continue
        m = re.match(r'^(#{1,4})\s+(.*)$', ln)
        if m:
            close_lists()
            level = len(m.group(1))
            text = m.group(2)
            if level == 1:
                out.append('<h1>%s</h1>' % inline(text))
            else:
                sec_n += 1
                out.append('<h%d id="s%d">%s</h%d>' % (level, sec_n, inline(text), level))
            i += 1
            continue
        if re.match(r'^\s*---\s*$', ln):
            close_lists()
            out.append('<hr>')
            i += 1
            continue
        if ln.startswith('>'):
            if not in_bq:
                close_lists()
                out.append('<blockquote>')
                in_bq = True
            content = ln[1:].strip()
            if content:
                out.append('<p>%s</p>' % inline(content))
            i += 1
            continue
        elif in_bq and ln.strip() == '':
            if i + 1 < len(lines) and lines[i+1].startswith('>'):
                i += 1
                continue
            out.append('</blockquote>'); in_bq = False
            i += 1
            continue
        m = re.match(r'^(\s*)-\s+(.*)$', ln)
        if m:
            if in_ol: out.append('</ol>'); in_ol = False
            if not in_ul:
                out.append('<ul>'); in_ul = True
            out.append('<li>%s</li>' % inline(m.group(2)))
            i += 1
            continue
        m = re.match(r'^\s*(\d+)\.\s+(.*)$', ln)
        if m:
            if in_ul: out.append('</ul>'); in_ul = False
            if not in_ol:
                out.append('<ol>'); in_ol = True
            out.append('<li>%s</li>' % inline(m.group(2)))
            i += 1
            continue
        if ln.strip() == '':
            close_lists()
            i += 1
            continue
        if (in_ul or in_ol) and ln.startswith('  '):
            out[-1] = out[-1][:-5] + ' ' + inline(ln.strip()) + '</li>'
            i += 1
            continue
        buf = [ln]
        i += 1
        while i < len(lines) and lines[i].strip() != '' and not re.match(r'^(#{1,4})\s|^\s*-\s|^\s*\d+\.\s|^>|^```|^\s*\||^\s*---\s*$', lines[i]):
            buf.append(lines[i]); i += 1
        close_lists()
        out.append('<p>%s</p>' % inline(' '.join(b.strip() for b in buf)))
    close_lists()
    return '\n'.join(out)

def check_tags(body, name):
    for tag in ['pre', 'table', 'ul', 'ol', 'blockquote', 'details']:
        o = len(re.findall(r'<%s[ >]' % tag, body))
        c = len(re.findall(r'</%s>' % tag, body))
        if o != c:
            print('TAG MISMATCH in %s: %s open=%d close=%d' % (name, tag, o, c))
            sys.exit(1)

def parse_title(md):
    """'# 4장. 데이터 타입 대전 — 부제' → (short='4장 · 데이터 타입 대전', sub='부제', full)"""
    first = next(l for l in md.split('\n') if l.startswith('# '))
    full = first[2:].strip()
    mm = re.match(r'^(\d+)장\.\s*(.+?)(?:\s+—\s*(.*))?$', full)
    if mm:
        short = '%s장 · %s' % (mm.group(1), mm.group(2).strip())
        sub = mm.group(3) or ''
    else:
        short, sub = full, ''
    return short, sub, full

def build_nav(chapters, active_slug):
    parts = []
    for group, files in GROUPS:
        parts.append('<div class="navgroup"><div class="navlabel">%s</div>' % html.escape(group))
        for f in files:
            s = slug(f)
            cls = ' class="active"' if s == active_slug else ''
            parts.append('<a%s href="%s.html">%s</a>' % (cls, s, html.escape(chapters[s]['short'])))
        parts.append('</div>')
    return '\n'.join(parts)

def main():
    shell = (TOOLS / 'shell.html').read_text(encoding='utf-8')
    DOCS.mkdir(parents=True, exist_ok=True)

    # 1) 전체 장 메타 수집
    chapters = {}
    for f in ORDER:
        md = (BIBLE / f).read_text(encoding='utf-8')
        short, sub, full = parse_title(md)
        chapters[slug(f)] = {'md': md, 'short': short, 'sub': sub, 'full': full}

    # 2) 장별 페이지
    slugs = [slug(f) for f in ORDER]
    for idx, s in enumerate(slugs):
        ch = chapters[s]
        body = convert(ch['md'])
        check_tags(body, s)
        nav = build_nav(chapters, s)

        prev_html = next_html = '<span></span>'
        if idx > 0:
            p = chapters[slugs[idx - 1]]
            prev_html = ('<a class="pn prev" href="%s.html"><span class="pn-label">← 이전</span>'
                         '<span class="pn-title">%s</span></a>'
                         % (slugs[idx - 1], html.escape(p['short'])))
        if idx < len(slugs) - 1:
            n = chapters[slugs[idx + 1]]
            next_html = ('<a class="pn next" href="%s.html"><span class="pn-label">다음 →</span>'
                         '<span class="pn-title">%s</span></a>'
                         % (slugs[idx + 1], html.escape(n['short'])))

        content = ('<article class="chapter">\n%s\n</article>\n'
                   '<nav class="pagenav" aria-label="장 이동">%s%s</nav>' % (body, prev_html, next_html))
        page = (shell
                .replace('<!--TITLE-->', html.escape(ch['short']) + ' — ClickHouse Bible')
                .replace('<!--NAV-->', nav)
                .replace('<!--NAV2-->', nav)
                .replace('<!--CONTENT-->', content))
        (DOCS / (s + '.html')).write_text(page, encoding='utf-8')

    # 3) 랜딩 페이지 (index.html)
    cards = []
    for group, files in GROUPS:
        cards.append('<section class="tocgroup"><h2>%s</h2><div class="cards">' % html.escape(group))
        for f in files:
            s = slug(f)
            ch = chapters[s]
            num = re.match(r'^(\d+)', s.split('-')[0])
            cards.append(
                '<a class="card" href="%s.html">'
                '<span class="card-num">%s</span>'
                '<span class="card-title">%s</span>'
                '<span class="card-sub">%s</span></a>'
                % (s, s.split('-')[0].lstrip('0') or '0',
                   html.escape(re.sub(r'^\d+장 · ', '', ch['short'])),
                   html.escape(ch['sub'])))
        cards.append('</div></section>')

    hero = '''<header class="hero">
  <p class="eyebrow">ClickHouse Certified Developer · 2026</p>
  <h1>지식 0에서 <span class="hl">자격증 합격</span>까지, 검증된 한 권</h1>
  <p class="lede">데이터베이스를 한 번도 다뤄본 적 없는 사람을 위한 ClickHouse 학습서.
  시험의 5개 영역 전체를 다루며, 모든 SQL 예제는 ClickHouse 26.8에서 직접 실행해 검증했다.</p>
  <div class="chips">
    <span class="chip">실기 <b>10–12과제</b> · 2시간</span>
    <span class="chip">합격선 <b>70%</b></span>
    <span class="chip">응시료 <b>$200</b></span>
    <span class="chip">예제 검증 <b>ClickHouse 26.8</b></span>
    <span class="chip">기준일 <b>2026-08-16</b></span>
  </div>
  <p class="lede" style="margin-top:1.6rem">
    <a class="cta" href="00-exam-guide.html">0장 · 시험 안내부터 시작 →</a>
  </p>
</header>'''
    index_content = hero + '\n' + '\n'.join(cards)
    nav = build_nav(chapters, None)
    page = (shell
            .replace('<!--TITLE-->', 'ClickHouse Bible — 자격증 취득 완전 정복')
            .replace('<!--NAV-->', nav)
            .replace('<!--NAV2-->', nav)
            .replace('<!--CONTENT-->', index_content))
    (DOCS / 'index.html').write_text(page, encoding='utf-8')

    total = sum((DOCS / (s + '.html')).stat().st_size for s in slugs)
    print('OK: index.html + %d chapter pages -> %s (본문 총 %d KB)'
          % (len(slugs), DOCS, total // 1024))

if __name__ == '__main__':
    main()
