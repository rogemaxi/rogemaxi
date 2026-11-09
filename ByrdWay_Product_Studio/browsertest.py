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
import os, sys, time
from pathlib import Path

FALLBACK_CHROMIUM = ['/opt/pw-browsers/chromium']

CLICK_SELECTOR = ('button, input[type=button], input[type=submit], [onclick], '
                  'a[href^="#"], [role=button], summary')


def _default_browsers_path():
    if os.name == 'nt':
        return str(Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'ms-playwright')
    if sys.platform == 'darwin':
        return str(Path.home() / 'Library' / 'Caches' / 'ms-playwright')
    return str(Path.home() / '.cache' / 'ms-playwright')


def configure_frozen():
    """In a PyInstaller build, Playwright otherwise looks for Chromium only INSIDE the
    package (PLAYWRIGHT_BROWSERS_PATH=0). Point it at the normal per-user install made by
    `python -m playwright install chromium` / install_windows.bat."""
    if getattr(sys, 'frozen', False) and 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ:
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = _default_browsers_path()


configure_frozen()


def install_chromium(timeout=1800):
    """Download Chromium using the Playwright driver bundled with the app (works inside the .exe,
    no Python needed). Returns (ok, message). Network: Playwright's download CDN only."""
    import subprocess
    try:
        from playwright._impl._driver import compute_driver_executable, get_driver_env
    except ImportError:
        return False, 'Playwright is not installed in this build.'
    node, cli = compute_driver_executable()
    if not Path(node).exists() or not Path(cli).exists():
        return False, f'Browser installer not found in this build ({node}).'
    env = get_driver_env()
    flags = {'creationflags': 0x08000000} if os.name == 'nt' else {}     # no console window on Windows
    try:
        r = subprocess.run([node, cli, 'install', 'chromium'], env=env, capture_output=True, text=True,
                           timeout=timeout, **flags)
    except subprocess.TimeoutExpired:
        return False, 'Browser download timed out. Check the internet connection and try again.'
    if r.returncode != 0:
        return False, ('Browser download failed: ' + (r.stderr or r.stdout).strip()[-400:])
    return True, f'Browser engine installed in {os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or _default_browsers_path()}.'


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
    # Playwright disables Chromium's OS-level sandbox by default; enable it where it works
    # (Windows desktop users). Containers running as root cannot use it, so fall back.
    sandbox_modes = [True, False] if os.name == 'nt' or os.environ.get('BYRDWAY_CHROMIUM_SANDBOX') == '1' else [False]
    for sandbox in sandbox_modes:
        for exe in attempts:
            try:
                kw = {'chromium_sandbox': sandbox}
                if exe:
                    kw['executable_path'] = exe
                b = p.chromium.launch(**kw)
                b._byrdway_sandbox = sandbox
                return b
            except Exception as e:
                errors.append(f'{exe or "default"} sandbox={sandbox}: {str(e).splitlines()[0][:160]}')
    raise RuntimeError('Chromium could not be launched: ' + ' | '.join(errors))


def run_browser_tests(site_dir, entry, shots_dir, label='run', timeout_ms=15000, max_clicks=80,
                      chromium_path='', max_routes=150, sweep_seconds=240):
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
            report['os_sandbox'] = getattr(browser, '_byrdway_sandbox', None)
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
                # interaction sweep over every in-app screen. Single-page tools switch screens by changing
                # the #fragment; each discovered #route is visited and swept (bounded by routes, clicks, time).
                base = entry_path.as_uri()
                start_hash = page.evaluate('() => location.hash')
                queue, seen = [start_hash], {start_hash}
                report['routes_visited'] = []
                t_end = time.time() + sweep_seconds

                def discover():
                    for h in page.evaluate("() => { const out = new Set(); if (location.hash) out.add(location.hash);"
                                           " document.querySelectorAll('a[href^=\"#\"]').forEach(a => {"
                                           " const h = a.getAttribute('href'); if (h && h.length > 1) out.add(h); });"
                                           " return Array.from(out); }"):
                        if h not in seen and len(seen) < max_routes:
                            seen.add(h)
                            queue.append(h)
                        elif h not in seen:
                            report['routes_capped'] = True

                while queue and time.time() < t_end:
                    route = queue.pop(0)
                    current['action'] = f'open screen {route or "(start)"}'
                    page.goto(base + route, wait_until='load')
                    page.wait_for_timeout(120)
                    report['routes_visited'].append(route or '(start)')
                    discover()
                    n = len(page.query_selector_all(CLICK_SELECTOR))
                    report['click_targets'] += n
                    for i in range(min(n, max_clicks)):
                        if time.time() > t_end:
                            break
                        els = page.query_selector_all(CLICK_SELECTOR)
                        if i >= len(els):
                            break
                        el = els[i]
                        try:
                            if not el.is_visible():
                                continue
                            href = el.get_attribute('href') or ''
                            if href.startswith('#') and len(href) > 1:
                                continue                      # navigation links are covered by visiting their route
                            desc = el.evaluate("e => (e.tagName + ' ' + (e.id ? '#' + e.id + ' ' : '') + "
                                               "(e.innerText || e.value || e.getAttribute('aria-label') || '')"
                                               ".trim().slice(0, 40))")
                            current['action'] = f'click {desc} on {route or "(start)"}'
                            el.click(timeout=2000, no_wait_after=True)
                            report['clicks'] += 1
                            page.wait_for_timeout(60)
                            if page.url.split('#')[0] != base:
                                page.goto(base + route, wait_until='load')
                            elif page.evaluate('() => location.hash') != route:
                                discover()
                                page.goto(base + route, wait_until='load')
                                page.wait_for_timeout(80)
                        except Exception as e:
                            report.setdefault('click_failures', []).append(f'{current["action"]}: {str(e).splitlines()[0][:120]}')
                report['routes_discovered'] = len(seen)
                report['routes_not_visited'] = len(queue)
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
         f"{report['clicks']} clicks over {len(report.get('routes_visited', []))} screen(s), {report['click_targets']} targets"),
        ('browser.all_screens_visited', 'browser_runtime', 'MAJOR',
         report['load_ok'] and not report.get('routes_not_visited') and not report.get('routes_capped'),
         f"{len(report.get('routes_visited', []))} of {report.get('routes_discovered', 0)} screens visited"
         + (' - time/route limit reached' if report.get('routes_not_visited') else '')),
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
