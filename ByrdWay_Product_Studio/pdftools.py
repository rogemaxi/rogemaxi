"""PDF / Explainer inspection, rendering and comparison (Agent 3 core, milestone E).

Truthfulness rules:
  * a flattened PDF can NOT be edited losslessly. The only in-PDF correction
    offered is a region text replacement on pages that HAVE a text layer; it is
    labelled RECONSTRUCTED_REGION, renders a before/after visual diff, verifies
    nothing outside the replaced rectangle changed, and requires owner approval;
  * image-only pages are refused (approved editable source or re-typesetting
    required);
  * editable sources (docx/pptx/tex/html/md/indd...) are detected and preferred.
"""
import hashlib, re
from pathlib import Path, PurePosixPath

EDITABLE_SOURCE_EXT = {'.docx', '.pptx', '.tex', '.html', '.htm', '.md', '.indd', '.idml', '.odt',
                       '.key', '.pages', '.ai', '.psd', '.afdesign', '.afpub', '.svg', '.canva'}


def _fitz():
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    return fitz


def available():
    try:
        _fitz()
        return True
    except ImportError:
        return False


def inspect_pdf(path, render_dir=None, dpi=60):
    """Structural audit. Returns (report, findings, checks)."""
    fitz = _fitz()
    findings, checks = [], []
    n = [0]

    def add(check, severity, category, page, detail, fix=None):
        n[0] += 1
        findings.append({'id': f'P{n[0]:03d}', 'check': check, 'severity': severity, 'category': category,
                         'file': Path(path).name, 'page': page, 'detail': detail, 'fix': fix, 'evidence': ''})
    try:
        doc = fitz.open(path)
    except Exception as e:
        add('pdf.open', 'CRITICAL', 'pdf_structure', None, f'PDF cannot be opened: {e}')
        checks.append(('pdf.open', 'pdf_structure', 'CRITICAL', False, str(e)))
        return {'pages': 0}, findings, checks
    with doc:
        checks.append(('pdf.open', 'pdf_structure', 'CRITICAL', True, f'{doc.page_count} pages'))
        if doc.needs_pass:
            add('pdf.encrypted', 'CRITICAL', 'pdf_structure', None, 'PDF is password protected')
        report = {'pages': doc.page_count, 'metadata': {k: v for k, v in (doc.metadata or {}).items() if v},
                  'page_info': [], 'renders': []}
        text_hashes, render_hashes = {}, {}
        sizes = set()
        printed_numbers = []
        for i, page in enumerate(doc):
            pno = i + 1
            text = page.get_text()
            imgs = page.get_images(full=True)
            sizes.add((round(page.rect.width), round(page.rect.height)))
            info = {'page': pno, 'chars': len(text.strip()), 'images': len(imgs),
                    'text_layer': bool(text.strip())}
            if len(re.sub(r'\s+', '', text)) <= 12 and imgs:   # only a page number/folio
                info['image_only'] = True
            elif not text.strip() and not imgs and not page.get_drawings():
                add('pdf.blank_page', 'MAJOR', 'pdf_structure', pno, 'Blank page')
            norm = re.sub(r'\s+', ' ', text).strip()
            if len(norm) > 80:
                h = hashlib.sha256(norm.encode()).hexdigest()
                if h in text_hashes:
                    add('pdf.duplicate_page', 'MAJOR', 'pdf_structure', pno,
                        f'Page {pno} duplicates the text of page {text_hashes[h]}')
                text_hashes.setdefault(h, pno)
            pix = page.get_pixmap(dpi=dpi)
            rh = hashlib.sha256(pix.samples).hexdigest()
            if rh in render_hashes and len(norm) <= 80 and (imgs or norm):
                add('pdf.duplicate_page', 'MAJOR', 'pdf_structure', pno,
                    f'Page {pno} renders identically to page {render_hashes[rh]}')
            render_hashes.setdefault(rh, pno)
            if render_dir:
                Path(render_dir).mkdir(parents=True, exist_ok=True)
                out = Path(render_dir) / f'page_{pno:03d}.png'
                pix.save(str(out))
                report['renders'].append(str(out))
            # printed page number: last short numeric line in bottom 12% of page
            words = page.get_text('words')
            bottom = [w for w in words if w[1] > page.rect.height * 0.88 and re.fullmatch(r'\d{1,4}', w[4])]
            printed_numbers.append((pno, int(bottom[-1][4]) if bottom else None))
            for link in page.get_links():
                if link.get('kind') == fitz.LINK_GOTO and not (0 <= link.get('page', -1) < doc.page_count):
                    add('pdf.broken_link', 'MAJOR', 'navigation', pno, 'Internal link points to a missing page')
            report['page_info'].append(info)
        image_only = [p['page'] for p in report['page_info'] if p.get('image_only')]
        report['image_only_pages'] = image_only
        report['text_layer'] = len(image_only) < doc.page_count
        if image_only:
            add('pdf.image_only', 'INFO', 'pdf_structure', None,
                f'{len(image_only)} image-only page(s): text cannot be machine-verified; '
                f'needs editable source or approved OCR + human review', None)
        if len(sizes) > 1:
            add('pdf.page_sizes', 'MINOR', 'layout', None, f'Mixed page sizes: {sorted(sizes)}')
        # page-number sequence
        nums = [(p, v) for p, v in printed_numbers if v is not None]
        if len(nums) >= 3:
            offset = nums[0][1] - nums[0][0]
            bad = [p for p, v in nums if v - p != offset]
            if bad:
                add('pdf.page_numbering', 'MAJOR', 'pdf_structure', bad[0],
                    f'Printed page numbers out of sequence at page(s) {bad[:8]} (missing or duplicated page?)')
        report['printed_page_numbers'] = printed_numbers
        # table of contents
        toc = doc.get_toc()
        report['toc_entries'] = len(toc)
        for lvl, title, pg in toc:
            if not (1 <= pg <= doc.page_count):
                add('pdf.toc_target', 'MAJOR', 'navigation', None, f'TOC entry "{title}" points to missing page {pg}')
        # fonts
        unembedded = set()
        for i in range(doc.page_count):
            for f in doc.get_page_fonts(i):
                ext, name = f[1], f[3]
                base = name.split('+')[-1]
                if (ext == 'n/a' or not ext) and base not in BASE14:
                    unembedded.add(name)
        if unembedded:
            add('pdf.fonts_unembedded', 'MINOR', 'typography', None, f'Fonts not embedded: {sorted(unembedded)[:6]}')
        checks.append(('pdf.fonts_embedded', 'typography', 'MINOR', not unembedded,
                       f'unembedded: {sorted(unembedded)[:6]}' if unembedded else 'all fonts embedded or standard base-14'))
        sev_fail = lambda cats: not any(f['severity'] in ('CRITICAL', 'MAJOR') and f['check'] in cats for f in findings)
        checks += [
            ('pdf.no_blank_pages', 'pdf_structure', 'MAJOR', sev_fail({'pdf.blank_page'}), ''),
            ('pdf.no_duplicate_pages', 'pdf_structure', 'MAJOR', sev_fail({'pdf.duplicate_page'}), ''),
            ('pdf.page_numbering', 'pdf_structure', 'MAJOR', sev_fail({'pdf.page_numbering'}) if len(nums) >= 3 else None,
             'not enough printed page numbers to test' if len(nums) < 3 else ''),
            ('pdf.navigation', 'navigation', 'MAJOR', sev_fail({'pdf.broken_link', 'pdf.toc_target'}), ''),
            ('pdf.not_encrypted', 'pdf_structure', 'CRITICAL', not doc.needs_pass, ''),
            ('pdf.text_layer', 'pdf_structure', 'MAJOR', True if report['text_layer'] else None,
             'image-only document: academic content unverifiable' if not report['text_layer'] else ''),
        ]
        return report, findings, checks


def page_texts(path):
    fitz = _fitz()
    with fitz.open(path) as doc:
        return [p.get_text() for p in doc]


def render_pages(path, out_dir, dpi=80, pages=None):
    fitz = _fitz()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outs = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc):
            if pages and (i + 1) not in pages:
                continue
            o = out_dir / f'page_{i + 1:03d}.png'
            page.get_pixmap(dpi=dpi).save(str(o))
            outs.append(str(o))
    return outs


def compare_pdfs(a, b, out_dir, dpi=80):
    """Render-based before/after comparison of every page."""
    from browsertest import compare_images
    ra = render_pages(a, Path(out_dir) / 'before', dpi)
    rb = render_pages(b, Path(out_dir) / 'after', dpi)
    pages = []
    for i in range(max(len(ra), len(rb))):
        if i >= len(ra) or i >= len(rb):
            pages.append({'page': i + 1, 'status': 'ADDED' if i >= len(ra) else 'REMOVED'})
            continue
        d = compare_images(ra[i], rb[i], Path(out_dir) / f'diff_{i + 1:03d}.png')
        pages.append({'page': i + 1, 'changed_fraction': d['changed_fraction'], 'bbox': d['bbox'],
                      'status': 'CHANGED' if d['changed_fraction'] > 0 else 'IDENTICAL'})
    return {'before_pages': len(ra), 'after_pages': len(rb), 'pages': pages,
            'changed_pages': [p['page'] for p in pages if p['status'] != 'IDENTICAL']}


def editable_sources(paths):
    """Given a list of package paths, return the ones that are editable sources."""
    return [p for p in paths if PurePosixPath(p).suffix.lower() in EDITABLE_SOURCE_EXT]


BASE14 = {'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique', 'Helvetica-BoldOblique', 'Times-Roman',
          'Times-Bold', 'Times-Italic', 'Times-BoldItalic', 'Courier', 'Courier-Bold', 'Courier-Oblique',
          'Courier-BoldOblique', 'Symbol', 'ZapfDingbats'}


class FlattenedPageError(ValueError):
    pass


def propose_text_correction(src_pdf, out_pdf, page_no, old_text, new_text, work_dir):
    """Replace one exact text occurrence on a text-layer page. Returns evidence dict.

    Font fidelity is NOT guaranteed (base-14 Helvetica substitution): the result
    is marked RECONSTRUCTED_REGION and must be visually approved by the owner.
    """
    fitz = _fitz()
    with fitz.open(src_pdf) as doc:
        if not 1 <= page_no <= doc.page_count:
            raise ValueError('Page out of range')
        page = doc[page_no - 1]
        if len(re.sub(r'\s+', '', page.get_text())) <= 12:
            raise FlattenedPageError('Page has no text layer (flattened/image-only). Refusing to rewrite; '
                                     'approved editable source required.')
        hits = page.search_for(old_text)
        if not hits and page.get_images():
            raise FlattenedPageError('Text not present in the text layer (likely flattened artwork). Refusing to '
                                     'rewrite; approved editable source required.')
        if len(hits) != 1:
            raise ValueError(f'Text must occur exactly once on page {page_no}; found {len(hits)}')
        rect = hits[0]
        spans = [s for b in page.get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans']
                 if fitz.Rect(s['bbox']).intersects(rect)]
        size = spans[0]['size'] if spans else 11
        color = spans[0]['color'] if spans else 0
        rgb = tuple(((color >> s) & 255) / 255 for s in (16, 8, 0))
        page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
        grow = fitz.Rect(rect.x0, rect.y0 - 1, max(rect.x1, rect.x0 + fitz.get_text_length(new_text, 'helv', size)) + 2, rect.y1 + 2)
        page.insert_text(fitz.Point(rect.x0, rect.y1 - size * 0.22), new_text, fontsize=size, fontname='helv', color=rgb)
        doc.save(out_pdf, garbage=3, deflate=True)
    cmp = compare_pdfs(src_pdf, out_pdf, work_dir)
    changed = cmp['changed_pages']
    confined = changed == [page_no] or changed == []
    # check diff bbox lies inside the replaced rectangle (with margin), at render scale
    page_cmp = next(p for p in cmp['pages'] if p['page'] == page_no)
    scale = 80 / 72
    inside = True
    if page_cmp.get('bbox'):
        x0, y0, x1, y1 = page_cmp['bbox']
        m = 6
        inside = (x0 >= grow.x0 * scale - m and y0 >= grow.y0 * scale - m and
                  x1 <= grow.x1 * scale + m and y1 <= grow.y1 * scale + m)
    return {'status': 'RECONSTRUCTED_REGION_AWAITING_VISUAL_APPROVAL', 'page': page_no, 'old': old_text,
            'new': new_text, 'rect': list(rect), 'changed_pages': changed,
            'change_confined_to_region': bool(confined and inside), 'comparison': cmp,
            'fidelity_note': 'Replacement text uses Helvetica; original font may differ. Owner must approve visually.'}
