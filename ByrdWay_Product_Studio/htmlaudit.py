"""Power Tool static auditor + deterministic minimal fixers (Agent 2 core).

Every finding: {id, check, severity, category, file, line, detail, evidence, fix}
`fix` is either None (human/AI needed) or an exact-once text patch
{file, find, replace, reason}. Fixes are applied only to working copies.

Severity policy (see QUALITY_SCORING.md):
  CRITICAL - broken function a student will hit (missing asset, undefined
             handler, wrong answer), or security issue
  MAJOR    - broken navigation, accessibility barrier, duplicate ids
  MINOR    - best-practice / responsive meta
  INFO     - informational, not scored
"""
import difflib, re
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urlsplit, unquote

JS_KEYWORDS = set('''if for while switch return function typeof new void delete catch try do in of
instanceof with yield await async case throw else var let const class super this'''.split())
JS_GLOBALS = set('''alert confirm prompt console setTimeout setInterval clearTimeout clearInterval
parseInt parseFloat isNaN isFinite Number String Boolean Math Date JSON Array Object RegExp Promise
encodeURIComponent decodeURIComponent encodeURI decodeURI requestAnimationFrame fetch Event
CustomEvent print open close scrollTo scroll focus blur history location window document
navigator localStorage sessionStorage Symbol Map Set Error eval structuredClone'''.split())


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []          # (tag, attrs dict, line)
        self.scripts = []           # inline script text
        self._in_script = False
        self._in_button = None
        self.button_text = {}
        self.title_text = ''
        self._in_title = False
        self._buf = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v if v is not None else '') for k, v in attrs}
        line = self.getpos()[0]
        self.elements.append((tag, a, line))
        if tag == 'script' and 'src' not in a:
            self._in_script = True
            self._buf = []
        if tag == 'button':
            self._in_button = len(self.elements) - 1
            self.button_text[self._in_button] = ''
        if tag == 'title':
            self._in_title = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == 'script' and self._in_script:
            self.scripts.append(''.join(self._buf))
            self._in_script = False
        if tag == 'button':
            self._in_button = None
        if tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_script:
            self._buf.append(data)
        if self._in_button is not None:
            self.button_text[self._in_button] += data
        if self._in_title:
            self.title_text += data


def parse_html(text):
    c = _Collector()
    c.feed(text)
    c.close()
    return c


def defined_js_functions(js):
    names = set(re.findall(r'\bfunction\s+([A-Za-z_$][\w$]*)', js))
    names |= set(re.findall(r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\(|[A-Za-z_$][\w$]*\s*=>)', js))
    names |= set(re.findall(r'\bwindow\.([A-Za-z_$][\w$]*)\s*=', js))
    names |= set(re.findall(r'\b(?:const|let|var|class)\s+([A-Za-z_$][\w$]*)', js))
    return names


def handler_calls(code):
    """Global function identifiers called in an inline handler."""
    calls = re.findall(r'(?<![\w.$])([A-Za-z_$][\w$]*)\s*\(', code)
    return [c for c in calls if c not in JS_KEYWORDS and c not in JS_GLOBALS]


def _line_of(text, needle):
    i = text.find(needle)
    return text[:i].count('\n') + 1 if i >= 0 else None


def _is_local_ref(url):
    if not url or url.startswith(('#', 'data:', 'javascript:', 'mailto:', 'tel:', 'about:', 'blob:')):
        return False
    parts = urlsplit(url)
    return not parts.scheme and not parts.netloc


def _close(name, options, cutoff=0.75):
    lowered = {o.lower(): o for o in options}
    if name.lower() in lowered and lowered[name.lower()] != name:
        return lowered[name.lower()]          # case-only mismatch (classic Windows -> web bug)
    m = difflib.get_close_matches(name, list(options), n=2, cutoff=cutoff)
    return m[0] if len(m) == 1 or (m and difflib.SequenceMatcher(None, name, m[0]).ratio() >= 0.85) else None


def audit_files(files):
    """files: {relpath: text} for every text file in the product, plus
    binary file names as keys with value None. Returns (findings, checks_run)."""
    findings = []
    checks = []           # (check_id, category, severity, passed, evidence)
    all_paths = set(files)
    html_files = [p for p in files if p.lower().endswith(('.html', '.htm')) and files[p] is not None]
    js_files = [p for p in files if p.lower().endswith('.js') and files[p] is not None]
    parsed = {p: parse_html(files[p]) for p in html_files}
    all_js = '\n'.join(files[p] for p in js_files)
    for p in html_files:
        all_js += '\n' + '\n'.join(parsed[p].scripts)
    funcs = defined_js_functions(all_js)
    n = [0]

    def add(check, severity, category, file, detail, evidence='', line=None, fix=None):
        n[0] += 1
        findings.append({'id': f'H{n[0]:03d}', 'check': check, 'severity': severity,
                         'category': category, 'file': file, 'line': line, 'detail': detail,
                         'evidence': evidence[:300], 'fix': fix})

    if not html_files:
        add('html.present', 'CRITICAL', 'structure', '', 'No HTML entry page found in product')
        checks.append(('html.present', 'structure', 'CRITICAL', False, 'no html'))
        return findings, checks
    checks.append(('html.present', 'structure', 'CRITICAL', True, f'{len(html_files)} html file(s)'))

    all_ids = set()
    for p in html_files:
        for tag, a, _ in parsed[p].elements:
            if a.get('id'):
                all_ids.add(a['id'])

    for p in html_files:
        text, c = files[p], parsed[p]
        base = PurePosixPath(p).parent
        before = len(findings)
        # --- document-level accessibility / responsive
        html_tags = [(a, l) for t, a, l in c.elements if t == 'html']
        if html_tags and not html_tags[0][0].get('lang'):
            m = re.search(r'<html(?=[\s>])[^>]*>', text, re.I)
            fix = None
            if m and text.count(m.group(0)) == 1:
                fix = {'file': p, 'find': m.group(0), 'replace': m.group(0)[:5] + ' lang="en"' + m.group(0)[5:],
                       'reason': 'Declare document language for screen readers (WCAG 3.1.1)'}
            add('a11y.lang', 'MINOR', 'accessibility', p, '<html> has no lang attribute', m.group(0) if m else '',
                html_tags[0][1], fix)
        checks.append((f'a11y.lang:{p}', 'accessibility', 'MINOR', not (html_tags and not html_tags[0][0].get('lang')), ''))

        has_viewport = any(t == 'meta' and a.get('name', '').lower() == 'viewport' for t, a, _ in c.elements)
        if not has_viewport:
            m = re.search(r'<head(?=[\s>])[^>]*>', text, re.I)
            fix = None
            if m and text.count(m.group(0)) == 1:
                fix = {'file': p, 'find': m.group(0),
                       'replace': m.group(0) + '\n<meta name="viewport" content="width=device-width, initial-scale=1">',
                       'reason': 'Enable responsive layout on phones/tablets'}
            add('responsive.viewport', 'MINOR', 'responsive', p, 'No viewport meta tag', '', None, fix)
        checks.append((f'responsive.viewport:{p}', 'responsive', 'MINOR', has_viewport, ''))

        if not c.title_text.strip():
            add('structure.title', 'MINOR', 'structure', p, 'Missing or empty <title>')
        checks.append((f'structure.title:{p}', 'structure', 'MINOR', bool(c.title_text.strip()), ''))

        # --- ids
        seen = {}
        for t, a, line in c.elements:
            i = a.get('id')
            if i:
                if i in seen:
                    add('structure.duplicate_id', 'MAJOR', 'structure', p, f'Duplicate id "{i}"',
                        f'lines {seen[i]} and {line}', line)
                seen[i] = line
        # --- images
        for t, a, line in c.elements:
            if t == 'img' and 'alt' not in a:
                add('a11y.img_alt', 'MAJOR', 'accessibility', p, 'Image without alt text (needs human-written alt)',
                    a.get('src', ''), line)
        # --- buttons
        for idx, (t, a, line) in enumerate(c.elements):
            if t == 'button':
                label = c.button_text.get(idx, '').strip() or a.get('aria-label') or a.get('title') or a.get('aria-labelledby')
                if not label:
                    add('a11y.button_name', 'MAJOR', 'accessibility', p, 'Button has no accessible name', '', line)
        # --- internal anchors
        for t, a, line in c.elements:
            href = a.get('href', '')
            if t == 'a' and href.startswith('#') and len(href) > 1:
                target = unquote(href[1:])
                if target not in all_ids:
                    cand = _close(target, all_ids)
                    fix = None
                    needle = f'href="{href}"'
                    if cand and text.count(needle) == 1:
                        fix = {'file': p, 'find': needle, 'replace': f'href="#{cand}"',
                               'reason': f'Broken in-page link; nearest existing section id is "{cand}"'}
                    add('nav.anchor', 'MAJOR', 'navigation', p, f'Link to missing section #{target}', needle, line, fix)
        # --- local assets & page links
        for t, a, line in c.elements:
            for attr in ('src', 'href'):
                url = a.get(attr, '')
                if attr == 'href' and t not in ('a', 'link'):
                    continue
                if not _is_local_ref(url):
                    if attr == 'src' and url.startswith(('http://', 'https://', '//')):
                        add('deps.external', 'INFO', 'dependencies', p,
                            'External resource: blocked in offline isolation, required network at runtime', url, line)
                    continue
                path = unquote(urlsplit(url).path)
                if not path:
                    continue
                resolved = (base / path).as_posix()
                # resolve '..' safely inside package
                stack = []
                ok = True
                for part in PurePosixPath(resolved).parts:
                    if part == '..':
                        if not stack:
                            ok = False
                            break
                        stack.pop()
                    elif part != '.':
                        stack.append(part)
                norm = '/'.join(stack)
                if not ok:
                    add('assets.escape', 'CRITICAL', 'security', p, 'Reference points outside the product package', url, line)
                    continue
                if norm not in all_paths:
                    cand = _close(norm, all_paths, cutoff=0.8)
                    fix = None
                    needle = f'{attr}="{url}"'
                    if cand and text.count(needle) == 1:
                        rel_new = cand
                        if str(base) not in ('', '.'):
                            prefix = str(base) + '/'
                            rel_new = cand[len(prefix):] if cand.startswith(prefix) else None
                        if rel_new:
                            fix = {'file': p, 'find': needle, 'replace': f'{attr}="{rel_new}"',
                                   'reason': f'Referenced file missing; package contains "{cand}"'}
                    add('assets.missing', 'CRITICAL', 'assets', p, f'Missing referenced file: {norm}', needle, line, fix)
        # --- inline handlers -> defined functions
        for t, a, line in c.elements:
            for attr, code in a.items():
                if not attr.startswith('on') or not code:
                    continue
                for fn in handler_calls(code):
                    if fn not in funcs:
                        cand = _close(fn, funcs, cutoff=0.7)
                        fix = None
                        needle = f'{attr}="{code}"'
                        if cand and text.count(needle) == 1:
                            fixed_code = re.sub(r'(?<![\w.$])' + re.escape(fn) + r'(?=\s*\()', cand, code)
                            fix = {'file': p, 'find': needle, 'replace': f'{attr}="{fixed_code}"',
                                   'reason': f'Handler calls undefined function {fn}(); defined function is {cand}()'}
                        add('js.undefined_handler', 'CRITICAL', 'functionality', p,
                            f'{t} {attr} calls undefined function {fn}()', needle, line, fix)
        checks.append((f'static.html:{p}', 'html_structure', 'MAJOR',
                       not any(f['severity'] in ('CRITICAL', 'MAJOR') for f in findings[before:]),
                       f'{len(findings) - before} findings'))

    # --- JS getElementById targets
    ids_in_js_assign = set(re.findall(r'''\.id\s*=\s*['"`]([\w\-:.]+)['"`]''', all_js)) | \
        set(re.findall(r'''id\s*=\s*\\?['"]([\w\-:.]+)\\?['"]''', all_js))
    for p in js_files + html_files:
        src = files[p] if p in js_files else '\n'.join(parsed[p].scripts)
        for m in re.finditer(r'''getElementById\(\s*['"]([^'"]+)['"]\s*\)''', src):
            i = m.group(1)
            if i not in all_ids and i not in ids_in_js_assign:
                cand = _close(i, all_ids, cutoff=0.8)
                fix = None
                full = files[p]
                if cand and full.count(m.group(0)) == 1:
                    fix = {'file': p, 'find': m.group(0), 'replace': m.group(0).replace(i, cand),
                           'reason': f'Script looks up missing element id "{i}"; page defines "{cand}"'}
                add('js.missing_element', 'MAJOR', 'functionality', p,
                    f'getElementById("{i}") but no element has that id', m.group(0), _line_of(full, m.group(0)), fix)
    checks.append(('static.js_ids', 'html_structure', 'MAJOR',
                   not any(f['check'] == 'js.missing_element' for f in findings), ''))
    checks.append(('static.handlers', 'functionality', 'CRITICAL',
                   not any(f['check'] == 'js.undefined_handler' for f in findings), ''))
    checks.append(('static.assets', 'assets', 'CRITICAL',
                   not any(f['check'] in ('assets.missing', 'assets.escape') for f in findings), ''))
    return findings, checks


def entry_page(paths):
    html = sorted(p for p in paths if p.lower().endswith(('.html', '.htm')))
    if not html:
        return None
    for pref in ('index.html', 'index.htm'):
        for p in sorted(html, key=lambda x: x.count('/')):
            if PurePosixPath(p).name.lower() == pref:
                return p
    return sorted(html, key=lambda x: (x.count('/'), x))[0]
