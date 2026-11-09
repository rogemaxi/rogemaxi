"""Isolated headless-browser interaction tests for Power Tools (milestone C).

Isolation model (uploaded JS is untrusted):
  * runs inside Chromium's renderer sandbox, never in Python/Node with OS access;
  * EVERY request is intercepted: only file:// URLs inside the product's working
    directory are served; all network and outside-file requests are aborted and
    reported;
  * downloads disabled, service workers blocked, dialogs auto-dismissed,
    per-page time limit and click limit.
If Playwright/Chromium is not installed, returns available=False (the quality
gate then reports NOT VERIFIED rather than passing).
"""
import os, time
from pathlib import Path

FALLBACK_CHROMIUM = ['/opt/pw-browsers/chromium']

CLICK_SELECTOR = ('button, input[type=button], input[type=submit], [onclick], '
                  'a[href^="#"], [role=button], summary')


def playwright_available():
    try:
        import playwright.sync_api  # noqa
        return True
    except ImportError:
        return False


def _launch(p, chromium_path=''):
    errors = []
    paths = [chromium_path] if chromium_path else []
    paths += [os.environ.get('BYRDWAY_CHROMIUM_PATH', '')]
    attempts = [None] + [x for x in paths + FALLBACK_CHROMIUM if x and Path(x).exists()]
    for exe in attempts:
        try:
            return p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        except Exception as e:
            errors.append(f'{exe or "default"}: {str(e).splitlines()[0][:160]}')
    raise RuntimeError('Chromium could not be launched: ' + ' | '.join(errors))


def run_browser_tests(site_dir, entry, shots_dir, label='run', timeout_ms=15000, max_clicks=80,
                      chromium_path=''):
    site_dir = Path(site_dir).resolve()
    shots_dir = Path(shots_dir)
    shots_dir.mkdir(parents=True, exist_ok=True)
    report = {'available': False, 'entry': entry, 'label': label, 'load_ok': False, 'errors': [],
              'console_errors': [], 'blocked_requests': [], 'broken_images': [], 'clicks': 0,
              'click_targets': 0, 'mobile_overflow_px': None, 'screenshots': {}, 'duration_s': None}
    if not playwright_available():
        report['unavailable_reason'] = ('Python Playwright not installed. Install with: pip install playwright '
                                        'then: python -m playwright install chromium (downloads ~150 MB; '
                                        'requires owner approval).')
        return report
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    entry_path = (site_dir / entry).resolve()
    if not entry_path.is_relative_to(site_dir) or not entry_path.exists():
        report['unavailable_reason'] = 'Entry page not inside working copy'
        return report
    try:
        with sync_playwright() as p:
            browser = _launch(p, chromium_path)
            report['available'] = True
            try:
                ctx = browser.new_context(accept_downloads=False, service_workers='block',
                                          viewport={'width': 1280, 'height': 800})
                ctx.set_default_timeout(timeout_ms)

                def route(r):
                    url = r.request.url
                    if url.startswith('file://'):
                        from urllib.parse import urlsplit, unquote
                        raw = unquote(urlsplit(url).path)
                        if os.name == 'nt':
                            raw = raw.lstrip('/')
                        path = Path(raw).resolve()
                        if path.is_relative_to(site_dir):
                            return r.continue_()
                    if url.startswith(('data:', 'blob:', 'about:')):
                        return r.continue_()
                    report['blocked_requests'].append(url[:200])
                    return r.abort()
                ctx.route('**/*', route)
                page = ctx.new_page()
                current = {'action': 'page load'}
                page.on('pageerror', lambda e: report['errors'].append(
                    {'message': str(e)[:300], 'after': current['action']}))
                page.on('console', lambda m: report['console_errors'].append(m.text[:300])
                        if m.type == 'error' else None)
                page.on('dialog', lambda d: d.dismiss())
                resp = page.goto(entry_path.as_uri(), wait_until='load')
                report['load_ok'] = True
                page.wait_for_timeout(300)
                report['title'] = page.title()
                report['broken_images'] = page.evaluate(
                    "() => Array.from(document.images).filter(i => i.complete && i.naturalWidth === 0)"
                    ".map(i => i.getAttribute('src'))")
                shot = shots_dir / f'{label}_desktop.png'
                page.screenshot(path=str(shot), full_page=True)
                report['screenshots']['desktop'] = str(shot)
                # interaction sweep
                handles = page.query_selector_all(CLICK_SELECTOR)
                report['click_targets'] = len(handles)
                for i in range(min(len(handles), max_clicks)):
                    els = page.query_selector_all(CLICK_SELECTOR)
                    if i >= len(els):
                        break
                    el = els[i]
                    try:
                        if not el.is_visible():
                            continue
                        desc = el.evaluate("e => (e.tagName + ' ' + (e.id ? '#' + e.id + ' ' : '') + "
                                           "(e.innerText || e.value || e.getAttribute('aria-label') || '')"
                                           ".trim().slice(0, 40))")
                        current['action'] = f'click {desc}'
                        el.click(timeout=2000, no_wait_after=True)
                        report['clicks'] += 1
                        page.wait_for_timeout(80)
                        if page.url.split('#')[0] != entry_path.as_uri():
                            page.goto(entry_path.as_uri(), wait_until='load')
                    except Exception as e:
                        report.setdefault('click_failures', []).append(f'{current["action"]}: {str(e).splitlines()[0][:120]}')
                current['action'] = 'mobile render'
                page.set_viewport_size({'width': 375, 'height': 740})
                page.goto(entry_path.as_uri(), wait_until='load')
                page.wait_for_timeout(200)
                report['mobile_overflow_px'] = page.evaluate(
                    "() => Math.max(0, document.documentElement.scrollWidth - window.innerWidth)")
                shot = shots_dir / f'{label}_mobile.png'
                page.screenshot(path=str(shot), full_page=True)
                report['screenshots']['mobile'] = str(shot)
            finally:
                browser.close()
    except Exception as e:
        report.setdefault('harness_errors', []).append(f'{type(e).__name__}: {str(e)[:300]}')
    report['duration_s'] = round(time.time() - t0, 2)
    return report


def browser_checks(report):
    """Convert a browser report into scored checks (check_id, category, severity, passed, evidence)."""
    if not report.get('available'):
        return [('browser.available', 'browser_runtime', 'CRITICAL', None,
                 report.get('unavailable_reason') or '; '.join(report.get('harness_errors', [])))]
    return [
        ('browser.load', 'browser_runtime', 'CRITICAL', bool(report['load_ok']),
         '; '.join(report.get('harness_errors', [])) or 'loaded'),
        ('browser.no_js_exceptions', 'browser_runtime', 'CRITICAL', report['load_ok'] and not report['errors'],
         '; '.join(f"{e['message']} (after {e['after']})" for e in report['errors'][:5]) or 'none'),
        ('browser.images_load', 'assets', 'MAJOR', report['load_ok'] and not report['broken_images'],
         ', '.join(map(str, report['broken_images'][:5])) or 'all images loaded'),
        ('browser.interactions_exercised', 'browser_runtime', 'MAJOR',
         report['load_ok'] and (report['click_targets'] == 0 or report['clicks'] > 0),
         f"{report['clicks']} clicks of {report['click_targets']} targets"),
        ('browser.mobile_no_overflow', 'responsive', 'MINOR',
         report['mobile_overflow_px'] is not None and report['mobile_overflow_px'] <= 2,
         f"horizontal overflow {report['mobile_overflow_px']}px at 375px width"),
    ]


def compare_images(a, b, diff_out=None):
    """Fraction of pixels that differ between two screenshots (render comparison)."""
    from PIL import Image, ImageChops
    ia, ib = Image.open(a).convert('RGB'), Image.open(b).convert('RGB')
    if ia.size != ib.size:
        w, h = max(ia.width, ib.width), max(ia.height, ib.height)
        ca, cb = Image.new('RGB', (w, h), 'white'), Image.new('RGB', (w, h), 'white')
        ca.paste(ia, (0, 0))
        cb.paste(ib, (0, 0))
        ia, ib = ca, cb
    diff = ImageChops.difference(ia, ib).convert('L').point(lambda v: 255 if v > 24 else 0)
    hist = diff.histogram()
    changed = hist[255]
    total = ia.width * ia.height
    bbox = diff.getbbox()
    if diff_out:
        diff.save(diff_out)
    return {'changed_fraction': round(changed / total, 6) if total else 0.0, 'bbox': bbox,
            'size': ia.size}
