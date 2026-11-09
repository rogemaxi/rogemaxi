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
