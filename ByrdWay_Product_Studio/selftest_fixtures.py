"""Controlled test fixtures with KNOWN, deliberately planted defects.

broken_power_tool_zip  - a Power Tool with:
    1. wrong answer key           (7 x 8 = "54")                      CRITICAL academic
    2. wrong multiple-choice key  (6 x 7 -> index 0 = "36")           CRITICAL academic
    3. misspelled onclick handler chekAnswer() -> JS exception        CRITICAL functional
    4. image path case mismatch   Images/logo.png vs images/logo.png  CRITICAL asset
    5. broken in-page link        #practise vs id="practice"          MAJOR navigation
    6. missing <html lang>                                            MINOR accessibility
explainer_pdf          - 3-page explainer whose page 2 states 7 x 8 = 54
"""
import io, zipfile
from pathlib import Path

BROKEN_INDEX = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ByrdWay Multiplication Power Tool (TEST FIXTURE)</title>
<style>body{font-family:sans-serif;max-width:800px;margin:auto;padding:12px} img{max-width:120px}</style></head>
<body>
<img src="Images/logo.png" alt="ByrdWay logo">
<nav><a href="#practise">Go to practice</a> <a href="#concepts">Concepts</a></nav>
<section id="concepts"><h2>Concepts</h2><p>Multiplication is repeated addition.</p></section>
<section id="practice"><h2>Practice</h2>
<div id="quiz"></div>
<button onclick="chekAnswer()">Check my answers</button>
<p id="result" aria-live="polite"></p>
</section>
<script src="quiz.js"></script>
</body></html>
"""

QUIZ_JS = """const items = [
  {q: "What is 7 × 8?", answer: "54"},
  {q: "Solve 2x + 3 = 11", answer: "x = 4"},
  {question: "What is 6 × 7?", choices: ["36", "42", "48"], correct: 0}
];
function render(){
  var html = '';
  items.forEach(function(it, i){ html += '<p>' + (it.q || it.question) + '</p>'; });
  document.getElementById('quiz').innerHTML = html;
}
function checkAnswer(){ document.getElementById('result').textContent = 'Checked ' + items.length + ' items'; }
render();
"""


def png_bytes(color=(30, 90, 200)):
    from PIL import Image
    b = io.BytesIO()
    Image.new('RGB', (40, 40), color).save(b, 'PNG')
    return b.getvalue()


def broken_power_tool_zip(path):
    path = Path(path)
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('index.html', BROKEN_INDEX)
        z.writestr('quiz.js', QUIZ_JS)
        z.writestr('images/logo.png', png_bytes())
    return path


def fixed_power_tool_zip(path):
    """Same product with all defects corrected by hand (for comparison tests)."""
    idx = (BROKEN_INDEX.replace('<html>', '<html lang="en">').replace('Images/logo.png', 'images/logo.png')
           .replace('#practise', '#practice').replace('chekAnswer()', 'checkAnswer()'))
    js = QUIZ_JS.replace('answer: "54"', 'answer: "56"').replace('correct: 0', 'correct: 1')
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('index.html', idx)
        z.writestr('quiz.js', js)
        z.writestr('images/logo.png', png_bytes())
    return Path(path)


def explainer_pdf(path, wrong=True, image_only=False):
    import pymupdf as fitz
    doc = fitz.open()
    for i in range(3):
        p = doc.new_page()
        if image_only:
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 100), False)
            pix.clear_with(200 + i)
            p.insert_image(fitz.Rect(72, 72, 472, 272), pixmap=pix)
        else:
            p.insert_text((72, 100), f'Chapter {i + 1}: Multiplication facts', fontsize=16)
            claim = '7 × 8 = 54' if (wrong and i == 1) else ('7 × 8 = 56' if i == 1 else f'{i + 5} × 2 = {(i + 5) * 2}')
            p.insert_text((72, 140), f'Worked example: {claim}', fontsize=12)
        p.insert_text((300, 800), str(i + 1), fontsize=10)
    doc.save(str(path))
    return Path(path)


def representative_explainer_pdf(path, worked_example_error=True, answer_key_error=False):
    """A representative Explainer-style PDF (TEST FIXTURE - not ByrdWay content):
    title page with an embedded illustration, clickable table of contents (PDF outline),
    two chapters with worked examples, an answer key with Q/A pairs, printed page numbers.
    Planted defects: worked example '7 × 8 = 54' (auto-correctable statement on a text page) and,
    optionally, a wrong answer-key entry 'A: 64' for 9 × 7 (detected; NOT auto-correctable)."""
    import pymupdf as fitz
    doc = fitz.open()

    def page(lines, pno):
        p = doc.new_page()
        y = 90
        for text, size in lines:
            p.insert_text((72, y), text, fontsize=size)
            y += size + 12
        p.insert_text((300, 805), str(pno), fontsize=10)
        return p
    p1 = page([('TEST FIXTURE Explainer: Multiplication and Area', 20),
               ('(not ByrdWay content - representative structure only)', 10),
               ('Contents', 14), ('Chapter 1  Multiplication facts ........ 2', 11),
               ('Chapter 2  Area of rectangles ........... 3', 11), ('Answer key ............................ 4', 11)], 1)
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 120, 80), False)
    pix.clear_with(180)
    p1.insert_image(fitz.Rect(72, 330, 312, 490), pixmap=pix)          # protected illustration
    page([('Chapter 1: Multiplication facts', 16),
          ('Multiplication is repeated addition: 3 groups of 4 is 4 + 4 + 4.', 11),
          ('Worked example 1: 7 × 8 = 54' if worked_example_error else 'Worked example 1: 7 × 8 = 56', 12),
          ('Worked example 2: 6 × 9 = 54', 12),
          ('Tip: check by skip-counting.', 11)], 2)
    page([('Chapter 2: Area of rectangles', 16),
          ('Area = length × width, measured in square units.', 11),
          ('Worked example 3: 5 × 4 = 20', 12),
          ('Worked example 4: 12 ÷ 3 = 4', 12)], 3)
    page([('Answer key', 16),
          ('Q1: What is 9 × 7?', 12), ('A: 64' if answer_key_error else 'A: 63', 12),
          ('Q2: What is 8 × 8?', 12), ('A: 64', 12)], 4)
    doc.set_toc([[1, 'Chapter 1  Multiplication facts', 2], [1, 'Chapter 2  Area of rectangles', 3],
                 [1, 'Answer key', 4]])
    doc.save(str(path))
    return Path(path)
