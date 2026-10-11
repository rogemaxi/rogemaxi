/* BYRDWAY MASTERY ADD-ON — content (math only; all wording lives in i18n keys)
   Rule: math strings are language-neutral and never translated.
   Each question: id, a (area id), s (stem key), m (math, optional, "\n" = new line),
   o (options; o[0] is ALWAYS the correct answer — display order is shuffled
   deterministically; an option starting with "@" is a wording key), w (solution steps, math). */
const BWM_DIAGNOSTIC = [
  {id:'d1', a:'solving-equations', s:'s_solvex', m:'3(x + 5) = 2x − 4', o:['x = −19','x = −9','x = 19','x = −1'], w:['3x + 15 = 2x − 4','x + 15 = −4','x = −19']},
  {id:'d2', a:'solving-equations', s:'s_solveineq', m:'−2x + 7 > 15', o:['x < −4','x > −4','x < 4','x > 4'], w:['−2x > 8','x < −4   (÷ −2 ⇒ flip)']},
  {id:'d3', a:'solving-equations', s:'s_solve', m:'|x − 3| = 7', o:['x = 10 or x = −4','x = 10','x = −10 or x = 4','@tok_nosol'], w:['x − 3 = 7  ⇒  x = 10','x − 3 = −7  ⇒  x = −4']},
  {id:'d4', a:'linear-equations', s:'s_slope2', m:'(−2, 5)   (4, −7)', o:['−2','2','−1/2','1/2'], w:['m = (−7 − 5) / (4 − (−2))','m = −12 / 6 = −2']},
  {id:'d5', a:'linear-equations', s:'d5', m:'m = 3   (2, −1)', o:['y = 3x − 7','y = 3x + 5','y = 3x − 5','y = 3x + 7'], w:['y − (−1) = 3(x − 2)','y + 1 = 3x − 6','y = 3x − 7']},
  {id:'d6', a:'linear-equations', s:'d6', m:'y = −½x + 4   (6, 3)', o:['y = −½x + 6','y = 2x − 9','y = −½x + 3','y = −2x + 15'], w:['m = −½','3 = −½(6) + b','b = 6','y = −½x + 6']},
  {id:'d7', a:'linear-absvalue-functions', s:'s_vertex', m:'f(x) = |x − 4| + 2', o:['(4, 2)','(−4, 2)','(2, 4)','(4, −2)'], w:['f(x) = |x − h| + k','h = 4, k = 2','(4, 2)']},
  {id:'d8', a:'linear-absvalue-functions', s:'s_evalf', m:'f(x) = 2x − 5      f(−3) = ?', o:['−11','−1','1','11'], w:['f(−3) = 2(−3) − 5','= −6 − 5 = −11']},
  {id:'d9', a:'systems-equations', s:'s_system', m:'y = 2x + 1\n3x + y = 16', o:['(3, 7)','(7, 3)','(−3, −5)','(5, 11)'], w:['3x + (2x + 1) = 16','5x = 15  ⇒  x = 3','y = 2(3) + 1 = 7']},
  {id:'d10', a:'systems-equations', s:'s_howmany', m:'2x + 3y = 6\n4x + 6y = 12', o:['@tok_inf','@tok_nosol','@tok_one','@tok_two'], w:['2(2x + 3y) = 2(6)','4x + 6y = 12  ⇒  same line']},
  {id:'d11', a:'systems-equations', s:'d11', m:'y > x + 1\ny ≤ −x + 5', o:['(1, 3)','(3, 1)','(0, 1)','(2, 4)'], w:['(1, 3):  3 > 1 + 1 ✓','3 ≤ −1 + 5 ✓']},
  {id:'d12', a:'exponents-exponential', s:'s_simplify', m:'(2x³)² · x⁻⁴', o:['4x²','2x²','4x¹⁰','4x⁻²'], w:['(2x³)² = 4x⁶','4x⁶ · x⁻⁴ = 4x⁶⁻⁴','= 4x²']},
  {id:'d13', a:'exponents-exponential', s:'d13', m:'', o:['P(t) = 500(1.06)ᵗ','P(t) = 500(0.06)ᵗ','P(t) = 500(1.6)ᵗ','P(t) = 500 + 1.06t'], w:['100% + 6% = 1.06','P(t) = 500(1.06)ᵗ']},
  {id:'d14', a:'exponents-exponential', s:'s_evaluate', m:'27^(2/3)', o:['9','18','3','81'], w:['27^(2/3) = (∛27)²','= 3² = 9']},
  {id:'d15', a:'polynomials-factoring', s:'s_factor', m:'x² − 5x − 24', o:['(x − 8)(x + 3)','(x + 8)(x − 3)','(x − 6)(x + 4)','(x − 12)(x + 2)'], w:['−8 · 3 = −24','−8 + 3 = −5','(x − 8)(x + 3)']},
  {id:'d16', a:'polynomials-factoring', s:'s_multiply', m:'(2x − 3)(x + 4)', o:['2x² + 5x − 12','2x² − 12','2x² + 11x − 12','2x² − 5x − 12'], w:['2x² + 8x − 3x − 12','= 2x² + 5x − 12']},
  {id:'d17', a:'quadratic-functions', s:'s_vertex', m:'y = x² − 6x + 5', o:['(3, −4)','(−3, −4)','(3, 4)','(6, 5)'], w:['x = −b/(2a) = 6/2 = 3','y = 9 − 18 + 5 = −4','(3, −4)']},
  {id:'d18', a:'quadratic-functions', s:'s_maxval', m:'f(x) = −2(x + 1)² + 8', o:['8','−1','−2','6'], w:['a = −2 < 0  ⇒  max at vertex','vertex (−1, 8)','max = 8']},
  {id:'d19', a:'quadratic-functions', s:'s_axis', m:'y = 2x² + 8x − 1', o:['x = −2','x = 2','x = −4','x = 4'], w:['x = −b/(2a)','x = −8/(2·2) = −2']},
  {id:'d20', a:'solving-quadratics', s:'s_solve', m:'x² + 2x − 15 = 0', o:['x = −5 or x = 3','x = 5 or x = −3','x = −5 or x = −3','x = 15 or x = −2'], w:['(x + 5)(x − 3) = 0','x = −5 or x = 3']},
  {id:'d21', a:'solving-quadratics', s:'s_howmanyreal', m:'3x² − 4x + 2 = 0', o:['@tok_noreal','@tok_onereal','@tok_tworeal','@tok_inf'], w:['b² − 4ac = 16 − 24','= −8 < 0']},
  {id:'d22', a:'working-with-functions', s:'s_fog2', m:'f(x) = x² − 3\ng(x) = 2x + 1', o:['22','3','5','10'], w:['g(2) = 5','f(5) = 25 − 3 = 22']},
  {id:'d23', a:'working-with-functions', s:'d23', m:'', o:['{(1, 4), (2, 4), (3, 5)}','{(1, 4), (1, 5), (2, 6)}','{(3, 1), (3, 2), (3, 3)}','{(0, 0), (2, 1), (2, −1)}'], w:['x = 1, 2, 3 → one y each ✓']},
  {id:'d24', a:'analyzing-data', s:'s_mean', m:'4, 7, 7, 9, 13', o:['8','7','9','10'], w:['4 + 7 + 7 + 9 + 13 = 40','40 ÷ 5 = 8']},
  {id:'d25', a:'analyzing-data', s:'d25', m:'r = −0.92', o:['@tok_strongneg','@tok_weakneg','@tok_strongpos','@tok_noassoc'], w:['r < 0  ⇒  negative','|r| ≈ 1  ⇒  strong']}
];

const BWM_CHECKOUTS = [
 {n:1, dok:'DOK 2.5', items:[
  {id:'c1_1', a:'solving-equations', s:'s_solvex', m:'(2/3)(x − 6) = x + 4', o:['x = −24','x = 24','x = −6','x = −18'], w:['2(x − 6) = 3(x + 4)','2x − 12 = 3x + 12','x = −24']},
  {id:'c1_2', a:'solving-equations', s:'s_solveineq', m:'−3 ≤ 2x + 5 < 11', o:['−4 ≤ x < 3','−4 < x ≤ 3','x ≤ −4 or x > 3','−1 ≤ x < 8'], w:['−8 ≤ 2x < 6','−4 ≤ x < 3']},
  {id:'c1_3', a:'linear-equations', s:'c1_3', m:'', o:['C = 60h + 50','C = 85h','C = 50h + 60','C = 60h + 170'], w:['m = (350 − 170)/(5 − 2) = 60','170 = 60(2) + b  ⇒  b = 50','C = 60h + 50']},
  {id:'c1_4', a:'linear-equations', s:'c1_4', m:'3x − 4y = 8   (3, −2)', o:['y = −(4/3)x + 2','y = (3/4)x − 17/4','y = (4/3)x − 6','y = −(3/4)x + 1/4'], w:['y = (3/4)x − 2  ⇒  m = 3/4','m⊥ = −4/3','−2 = −(4/3)(3) + b  ⇒  b = 2']},
  {id:'c1_5', a:'linear-absvalue-functions', s:'c1_5', m:'f(x) = |x|', o:['g(x) = −|x − 3| − 2','g(x) = −|x + 3| − 2','g(x) = |x − 3| − 2','g(x) = −|x − 3| + 2'], w:['−|x|','−|x − 3|','−|x − 3| − 2']},
  {id:'c1_6', a:'linear-absvalue-functions', s:'s_xints', m:'f(x) = −2|x + 1| + 6', o:['x = 2, x = −4','x = −2, x = 4','x = 3, x = −3','x = 1, x = −3'], w:['−2|x + 1| + 6 = 0','|x + 1| = 3','x = 2 or x = −4']},
  {id:'c1_7', a:'systems-equations', s:'c1_7', m:'', o:['80','70','75','85'], w:['a + s = 150','12a + 8s = 1480','12(150 − s) + 8s = 1480','1800 − 4s = 1480  ⇒  s = 80']},
  {id:'c1_8', a:'systems-equations', s:'s_system', m:'3x − 2y = 16\n5x + 4y = 12', o:['(4, −2)','(−2, 4)','(4, 2)','(2, −5)'], w:['6x − 4y = 32','+ 5x + 4y = 12','11x = 44  ⇒  x = 4','3(4) − 2y = 16  ⇒  y = −2']},
  {id:'c1_9', a:'exponents-exponential', s:'c1_9', m:'', o:['$14,739','$13,200','$20,400','$10,800'], w:['V(t) = 24000(0.85)ᵗ','V(3) = 24000(0.614125)','≈ 14,739']},
  {id:'c1_10', a:'polynomials-factoring', s:'s_factor', m:'3x³ − 12x', o:['3x(x − 2)(x + 2)','3x(x − 2)²','3x(x² − 4)','3x(x − 4)(x + 1)'], w:['3x(x² − 4)','x² − 4 = (x − 2)(x + 2)','3x(x − 2)(x + 2)']},
  {id:'c1_11', a:'polynomials-factoring', s:'s_factor', m:'6x² + 7x − 3', o:['(3x − 1)(2x + 3)','(3x + 1)(2x − 3)','(6x − 1)(x + 3)','(2x − 1)(3x + 3)'], w:['ac = −18 → 9 · (−2)','6x² + 9x − 2x − 3','3x(2x + 3) − 1(2x + 3)','(3x − 1)(2x + 3)']},
  {id:'c1_12', a:'quadratic-functions', s:'c1_12', m:'h(t) = −16t² + 64t + 5', o:['69 ft','64 ft','2 ft','133 ft'], w:['t = −64/(2·(−16)) = 2','h(2) = −64 + 128 + 5 = 69']},
  {id:'c1_13', a:'solving-quadratics', s:'s_complsq', m:'x² + 8x − 5 = 0', o:['x = −4 ± √21','x = 4 ± √21','x = −4 ± √11','x = −8 ± √21'], w:['x² + 8x + 16 = 5 + 16','(x + 4)² = 21','x = −4 ± √21']},
  {id:'c1_14', a:'working-with-functions', s:'s_finv', m:'f(x) = 3x − 4      f⁻¹(11) = ?', o:['5','29','7/3','−5'], w:['3x − 4 = 11','3x = 15  ⇒  x = 5']},
  {id:'c1_15', a:'analyzing-data', s:'c1_15', m:'ŷ = 4.5x + 62   x = 6   y = 85', o:['−4','4','23','89'], w:['ŷ = 4.5(6) + 62 = 89','residual = y − ŷ = 85 − 89 = −4']}
 ]},
 {n:2, dok:'DOK 3', items:[
  {id:'c2_1', a:'solving-equations', s:'c2_1', m:'4 − 3(x − 2) = 13\n① 4 − 3x − 6 = 13\n② −3x − 2 = 13\n③ −3x = 15\n④ x = −5', o:['①','②','③','④'], w:['−3(x − 2) = −3x + 6','4 − 3x + 6 = 13','−3x = 3  ⇒  x = −1']},
  {id:'c2_2', a:'solving-equations', s:'c2_2', m:'5(x − 2) + kx = 3x + 7', o:['k = −2','k = 2','k = 3','k = −5'], w:['(5 + k)x − 10 = 3x + 7','5 + k = 3  ⇒  k = −2','−10 = 7  ✗  ⇒  ∅']},
  {id:'c2_3', a:'linear-equations', s:'c2_3', m:'(−1, 4)   (3, −4)', o:['(5, −8)','(5, −6)','(−2, 4)','(2, 0)'], w:['m = −8/4 = −2','y = −2x + 2','−2(5) + 2 = −8 ✓']},
  {id:'c2_4', a:'linear-equations', s:'c2_4', m:'x:  −2,  1,  4,  10\ny:  11,  5,  −1,  ?', o:['−13','−7','−11','−19'], w:['m = (5 − 11)/(1 − (−2)) = −2','Δx = 10 − 4 = 6','−1 + 6(−2) = −13']},
  {id:'c2_5', a:'linear-absvalue-functions', s:'c2_5', m:'g(x) = 3|x − 2| − 6', o:['h(x) = x² − 4x','h(x) = x² − 4','h(x) = |x − 4| − 2','h(x) = 2x − 4'], w:['3|x − 2| = 6  ⇒  |x − 2| = 2','x = 0 or x = 4','x² − 4x = x(x − 4)  ⇒  0, 4']},
  {id:'c2_6', a:'systems-equations', s:'c2_6', m:'2x − 5y = 10\n6x + ay = b', o:['a = −15, b = 30','a = 15, b = 30','a = −15, b = 10','a = −5, b = 10'], w:['3(2x − 5y) = 3(10)','6x − 15y = 30']},
  {id:'c2_7', a:'systems-equations', s:'c2_7', m:'', o:['3 mph','15 mph','6 mph','5 mph'], w:['b + c = 36/2 = 18','b − c = 36/3 = 12','2c = 6  ⇒  c = 3']},
  {id:'c2_8', a:'exponents-exponential', s:'c2_8', m:'A(t) = 1000 + 50t\nB(t) = 1000(1.04)ᵗ', o:['12','11','13','@tok_never'], w:['t = 11:  A = 1550,  B ≈ 1539.45','t = 12:  A = 1600,  B ≈ 1601.03 ✓']},
  {id:'c2_9', a:'exponents-exponential', s:'c2_9', m:'f(t) = 400(0.5)^(t/3)', o:['≈ 20.6%','50%','≈ 16.7%','≈ 79.4%'], w:['(0.5)^(t/3) = (0.5^(1/3))ᵗ','0.5^(1/3) ≈ 0.7937','1 − 0.7937 ≈ 0.206']},
  {id:'c2_10', a:'polynomials-factoring', s:'c2_10', m:'2x³ + kx² − 5x − 6', o:['k = 5','k = −5','k = 3','k = 9'], w:['p(−3) = 0','−54 + 9k + 15 − 6 = 0','9k = 45  ⇒  k = 5']},
  {id:'c2_11', a:'quadratic-functions', s:'c2_11', m:'(−2, 5)   (0, −3)', o:['y = −2(x + 2)² + 5','y = −2(x − 2)² + 5','y = 2(x + 2)² − 3','y = −½(x + 2)² + 5'], w:['y = a(x + 2)² + 5','−3 = 4a + 5  ⇒  a = −2']},
  {id:'c2_12', a:'solving-quadratics', s:'c2_12', m:'', o:['5','13','6.5','10'], w:['w(2w + 3) = 65','2w² + 3w − 65 = 0','(2w + 13)(w − 5) = 0','w = 5  (w > 0)']},
  {id:'c2_13', a:'working-with-functions', s:'c2_13', m:'f(x) = 2x + 3\ng(x) = x² − 1\nf(g(x)) = g(f(x))', o:['x = (−6 ± √22)/2','x = −3 ± √22','x = (−12 ± √22)/4','@tok_nosol'], w:['f(g(x)) = 2x² + 1','g(f(x)) = 4x² + 12x + 8','2x² + 12x + 7 = 0','x = (−12 ± √88)/4 = (−6 ± √22)/2']},
  {id:'c2_14', a:'analyzing-data', s:'c2_14', m:'12, 15, 15, 18, 20, 22, 60', o:['≈ 6.14','1.5','43','≈ 8.57'], w:['x̄ = 162/7 ≈ 23.14','x̄ = 102/6 = 17','23.14 − 17 ≈ 6.14']},
  {id:'c2_15', a:'polynomials-factoring', s:'c2_15', m:'A = 4x² − 9\nw = 2x − 3\nP = 48', o:['x = 6','x = 12','x = 4.5','x = 3'], w:['4x² − 9 = (2x − 3)(2x + 3)','ℓ = 2x + 3','P = 2(2x − 3) + 2(2x + 3) = 8x','8x = 48  ⇒  x = 6']}
 ]},
 {n:3, dok:'DOK 3.5', items:[
  {id:'c3_1', a:'solving-equations', s:'c3_1', m:'a(x − 2) > 3x + 1\nx < (2a + 1)/(a − 3)', o:['a < 3','a > 3','a ≠ 3','a < 0'], w:['(a − 3)x > 2a + 1','÷ (a − 3) flips  ⇔  a − 3 < 0','a < 3']},
  {id:'c3_2', a:'solving-equations', s:'c3_2', m:'|2x − 5| ≤ 9', o:['10','9','8','7'], w:['−9 ≤ 2x − 5 ≤ 9','−2 ≤ x ≤ 7','−2, −1, 0, …, 7  →  10']},
  {id:'c3_3', a:'linear-equations', s:'c3_3', m:'A(1, 2)   B(5, 4)   C(k, 10)', o:['k = 17','k = 13','k = 9','k = 21'], w:['m(AB) = 2/4 = 1/2','(10 − 2)/(k − 1) = 1/2','k − 1 = 16  ⇒  k = 17']},
  {id:'c3_4', a:'linear-absvalue-functions', s:'c3_4', m:'y = |x − 1|\ny = ½x + 2', o:['16/3','6','20/3','4'], w:['x ≥ 1:  x − 1 = ½x + 2  ⇒  x = 6','x < 1:  1 − x = ½x + 2  ⇒  x = −2/3','6 + (−2/3) = 16/3']},
  {id:'c3_5', a:'linear-absvalue-functions', s:'c3_5', m:'f(x) = −|x − 4| + 3', o:['5','7','6','3'], w:['−|x − 4| + 3 > 0','|x − 4| < 3  ⇒  1 < x < 7','2, 3, 4, 5, 6  →  5']},
  {id:'c3_6', a:'systems-equations', s:'c3_6', m:'kx + 2y = 5\n3x + 6y = 8', o:['k = 1','k = 3','k = −1','k = 6'], w:['k/3 = 2/6  ⇒  k = 1','x + 2y = 5   vs   x + 2y = 8/3','5 ≠ 8/3  ⇒  ∅']},
  {id:'c3_7', a:'systems-equations', s:'c3_7', m:'y ≥ |x| − 2\ny ≤ 2', o:['16','8','32','12'], w:['|x| − 2 = 2  ⇒  x = ±4','base = 8,  height = 2 − (−2) = 4','A = ½ · 8 · 4 = 16']},
  {id:'c3_8', a:'exponents-exponential', s:'s_solve', m:'2ˣ · 4^(x + 1) = 8^(x − 1)', o:['@tok_nosol','x = 5','x = −5','@tok_allreal'], w:['2ˣ · 2^(2x + 2) = 2^(3x − 3)','3x + 2 = 3x − 3','2 = −3  ✗  ⇒  ∅']},
  {id:'c3_9', a:'exponents-exponential', s:'c3_9', m:'', o:['2 h','6 h','4 h','3 h'], w:['9600 ÷ 150 = 64 = 2⁶','6 × 20 min = 120 min','= 2 h']},
  {id:'c3_10', a:'polynomials-factoring', s:'c3_10', m:'x² − y² = 48\nx + y = 12', o:['x = 8','x = 4','x = 6','x = 10'], w:['(x + y)(x − y) = 48','x − y = 4','2x = 16  ⇒  x = 8']},
  {id:'c3_11', a:'polynomials-factoring', s:'s_whichfactor', m:'x⁴ − 13x² + 36', o:['x + 3','x − 4','x + 9','x − 6'], w:['(x² − 4)(x² − 9)','(x − 2)(x + 2)(x − 3)(x + 3)']},
  {id:'c3_12', a:'quadratic-functions', s:'c3_12', m:'x = −1,  x = 5   (2, −18)', o:['−10','−5','10','−18'], w:['y = a(x + 1)(x − 5)','−18 = a(3)(−3)  ⇒  a = 2','y(0) = 2(1)(−5) = −10']},
  {id:'c3_13', a:'solving-quadratics', s:'c3_13', m:'x² − 6x + c = 0', o:['c < 9','c > 9','c = 9','c < 36'], w:['b² − 4ac > 0','36 − 4c > 0','c < 9']},
  {id:'c3_14', a:'working-with-functions', s:'s_evalexpr', m:'f(x) = 2x − 1\ng(x) = (x + 1)/2\nf(g(5)) + g(f(−3)) = ?', o:['2','8','0','−2'], w:['f(g(x)) = x,  g(f(x)) = x','5 + (−3) = 2']},
  {id:'c3_15', a:'analyzing-data', s:'c3_15', m:'', o:['40%','20%','≈ 30.8%','≈ 16.7%'], w:['120 − 70 = 50','20 / 50 = 0.40']}
 ]},
 {n:4, dok:'DOK 4', items:[
  {id:'c4_1', a:'solving-equations', s:'c4_1', m:'k(x + 3) − 2x = 4x + 12', o:['@tok_noval','k = 6','k = 4','@tok_everyk'], w:['(k − 6)x + (3k − 12) = 0','∞ ⇔ k − 6 = 0 and 3k − 12 = 0','k = 6 and k = 4  ✗']},
  {id:'c4_2', a:'linear-equations', s:'c4_2', m:'(2, 3)', o:['10','5','6','12'], w:['x/a + y/a = 1  ⇒  x + y = a','2 + 3 = a = 5','a + b = 10']},
  {id:'c4_3', a:'linear-absvalue-functions', s:'c4_3', m:'y = mx\ny = |x| − 3', o:['−1 < m < 1','m > 1','m < −1 or m > 1','m ∈ ℝ'], w:['x ≥ 0:  x = 3/(1 − m) ≥ 0  ⇔  m < 1','x < 0:  x = −3/(m + 1) < 0  ⇔  m > −1','−1 < m < 1']},
  {id:'c4_4', a:'systems-equations', s:'c4_4', m:'', o:['40 L','20 L','30 L','36 L'], w:['x + y = 60','0.2x + 0.5y = 0.3(60) = 18','0.2x + 30 − 0.5x = 18','x = 40']},
  {id:'c4_5', a:'exponents-exponential', s:'c4_5', m:'', o:['375 mg','800 mg','400 mg','325 mg'], w:['200 + 100 + 50 + 25','= 375']},
  {id:'c4_6', a:'exponents-exponential', s:'c4_6', m:'f(t) = 1000 + 250t\ng(t) = 1000(1.15)ᵗ', o:['t = 8','t = 7','t = 5','@tok_never'], w:['t = 7:  f = 2750,  g ≈ 2660.02','t = 8:  f = 3000,  g ≈ 3059.02 ✓']},
  {id:'c4_7', a:'polynomials-factoring', s:'s_evalexpr', m:'x + 1/x = 5\nx² + 1/x² = ?', o:['23','25','27','10'], w:['(x + 1/x)² = x² + 2 + 1/x²','25 = x² + 1/x² + 2','x² + 1/x² = 23']},
  {id:'c4_8', a:'polynomials-factoring', s:'c4_8', m:'p(x) = x³ − 4x² + ax + 12', o:['2,  1 ± √7','2,  −1 ± √7','2,  3,  −2','2,  1 ± √5'], w:['p(2) = 2a + 4 = 0  ⇒  a = −2','p(x) = (x − 2)(x² − 2x − 6)','x = 1 ± √7']},
  {id:'c4_9', a:'quadratic-functions', s:'c4_9', m:'y = x² − 2kx + k² + 2k − 3', o:['y = 2x − 3','y = 2x + 3','y = −2x − 3','y = x² − 3'], w:['y = (x − k)² + 2k − 3','vertex (k, 2k − 3)','y = 2x − 3']},
  {id:'c4_10', a:'solving-quadratics', s:'c4_10', m:'2x² − 7x + c = 0     x = 3', o:['x = 1/2','x = 4','x = −1/2','x = 7/2'], w:['2(9) − 21 + c = 0  ⇒  c = 3','2x² − 7x + 3 = (2x − 1)(x − 3)','x = 1/2']},
  {id:'c4_11', a:'working-with-functions', s:'c4_11', m:'f(x) = ax + b\nf(f(x)) = 9x − 8,   a > 0\nf(2) = ?', o:['4','10','−8','1'], w:['f(f(x)) = a²x + ab + b','a² = 9  ⇒  a = 3','4b = −8  ⇒  b = −2','f(2) = 6 − 2 = 4']},
  {id:'c4_12', a:'working-with-functions', s:'c4_12', m:'h(x) = (x + 1)²,   x ≥ −1', o:['h⁻¹(x) = √x − 1','h⁻¹(x) = −√x − 1','h⁻¹(x) = √(x − 1)','h⁻¹(x) = √x + 1'], w:['x = (y + 1)²,  y ≥ −1','√x = y + 1','y = √x − 1']},
  {id:'c4_13', a:'analyzing-data', s:'c4_13', m:'x̄ = 12,   σ = 4\nx → 3x + 5', o:['x̄ = 41,  σ = 12','x̄ = 41,  σ = 17','x̄ = 36,  σ = 12','x̄ = 41,  σ = 4'], w:['3(12) + 5 = 41','3(4) = 12   (+5 ⇏ σ)']},
  {id:'c4_14', a:'analyzing-data', s:'c4_14', m:'n = 5,  x̄ = 10\n+ 22', o:['12','16','11','10.5'], w:['5 · 10 = 50','50 + 22 = 72','72 ÷ 6 = 12']},
  {id:'c4_15', a:'solving-equations', s:'c4_15', m:'A = 3.50 + 2.25d\nB = 6 + 1.75d', o:['d < 5','d > 5','d < 2.5','d > 2.5'], w:['3.50 + 2.25d < 6 + 1.75d','0.5d < 2.5','d < 5']}
 ]},
 {n:5, dok:'@co5_l', items:[
  {id:'c5_1', a:'solving-equations', s:'s_howmanyreal', m:'|x − 1| + |x + 3| = 6', o:['2','0','1','@tok_inf'], w:['x ≥ 1:  2x + 2 = 6  ⇒  x = 2','x ≤ −3:  −2x − 2 = 6  ⇒  x = −4','−3 < x < 1:  4 = 6  ✗']},
  {id:'c5_2', a:'solving-equations', s:'s_solve', m:'|x − 2| > x', o:['x < 1','x > 1','x < 2','@tok_allreal'], w:['x < 0:  |x − 2| ≥ 0 > x ✓','0 ≤ x < 2:  2 − x > x  ⇒  x < 1','x ≥ 2:  x − 2 > x  ✗']},
  {id:'c5_3', a:'linear-equations', s:'c5_3', m:'3x + ky = 7\nkx + 12y = 5', o:['k = 0','k = 2','k = −2','@tok_noval'], w:['A₁A₂ + B₁B₂ = 0','3k + 12k = 0','k = 0:  3x = 7 ⊥ 12y = 5']},
  {id:'c5_4', a:'linear-absvalue-functions', s:'c5_4', m:'y = |x − 3|\ny = 5 − |x − 3|', o:['12.5','25','6.25','10'], w:['|x − 3| = 2.5','d₁ = 5,  d₂ = 5','A = ½ · 5 · 5 = 12.5']},
  {id:'c5_5', a:'systems-equations', s:'c5_5', m:'x + ay = 1\nax + y = 1', o:['a = −1','a = 1','a = ±1','a = 0'], w:['1 − a² = 0  ⇒  a = ±1','a = 1:  x + y = 1 (×2)  ⇒  ∞','a = −1:  x − y = 1,  x − y = −1  ⇒  ∅']},
  {id:'c5_6', a:'exponents-exponential', s:'s_evalexpr', m:'4ˣ = 3\n8ˣ · 2⁻ˣ = ?', o:['3','9','√3','6'], w:['8ˣ · 2⁻ˣ = 2³ˣ · 2⁻ˣ','= 2²ˣ = 4ˣ','= 3']},
  {id:'c5_7', a:'exponents-exponential', s:'s_solve', m:'9ˣ − 4 · 3ˣ + 3 = 0', o:['x = 0 or x = 1','x = 1 or x = 3','x = 1','@tok_nosol'], w:['u = 3ˣ:  u² − 4u + 3 = 0','u = 1 or u = 3','x = 0 or x = 1']},
  {id:'c5_8', a:'polynomials-factoring', s:'c5_8', m:'(x³ + 2x² − 5x + k) ÷ (x − 2)\nR = 7', o:['k = 1','k = 13','k = −1','k = 7'], w:['p(2) = 8 + 8 − 10 + k','6 + k = 7  ⇒  k = 1']},
  {id:'c5_9', a:'polynomials-factoring', s:'s_evalexpr', m:'a + b = 7,   ab = 10\na³ + b³ = ?', o:['133','343','153','113'], w:['a³ + b³ = (a + b)³ − 3ab(a + b)','= 343 − 210 = 133']},
  {id:'c5_10', a:'quadratic-functions', s:'c5_10', m:'', o:['1800 m²','900 m²','3600 m²','1600 m²'], w:['L + 2W = 120','A = W(120 − 2W)','W = 30,  L = 60','A = 1800']},
  {id:'c5_11', a:'solving-quadratics', s:'c5_11', m:'x² + (k − 2)x + 1 = 0', o:['k = 0 or k = 4','k = 4','k = 2','k = −4 or k = 0'], w:['(k − 2)² − 4 = 0','k − 2 = ±2','k = 0 or k = 4']},
  {id:'c5_12', a:'solving-quadratics', s:'c5_12', m:'x⁴ − 5x² + 4 = 0', o:['10','5','0','4'], w:['(x² − 1)(x² − 4) = 0','x = ±1, ±2','1 + 1 + 4 + 4 = 10']},
  {id:'c5_13', a:'working-with-functions', s:'s_finv', m:'f(x) = (2x + 3)/(x − 1)      f⁻¹(5) = ?', o:['8/3','13/4','3/8','4'], w:['(2x + 3)/(x − 1) = 5','2x + 3 = 5x − 5','x = 8/3']},
  {id:'c5_14', a:'working-with-functions', s:'c5_14', m:'f(x + 1) = x² + 3x\nf(4) = ?', o:['18','28','16','21'], w:['x + 1 = 4  ⇒  x = 3','9 + 9 = 18']},
  {id:'c5_15', a:'analyzing-data', s:'c5_15', m:'', o:['56','60','74','6'], w:['5 · 80 = 400','4 · 86 = 344','400 − 344 = 56']}
 ]}
];

/* First-principles lessons. p/w = wording keys; steps = [labelKey, math]. */
const BWM_LESSONS = {
  'solving-equations': {ex:'4(x − 2) + 3 = 2x + 15', steps:[['op_distribute','4x − 8 + 3 = 2x + 15'],['op_combine','4x − 5 = 2x + 15'],['op_subboth','4x − 2x − 5 = 2x − 2x + 15  →  2x − 5 = 15'],['op_addboth','2x − 5 + 5 = 15 + 5  →  2x = 20'],['op_divboth','2x ÷ 2 = 20 ÷ 2  →  x = 10']], check:'4(10 − 2) + 3 = 35   ✓   2(10) + 15 = 35', tq:'5(x + 1) − 2 = 3x + 11', ta:'x = 4', tw:['5x + 3 = 3x + 11','2x = 8','x = 4']},
  'linear-equations': {ex:'(1, 4)   (3, 10)', steps:[['op_slope','m = (10 − 4)/(3 − 1) = 6/2 = 3'],['op_pointslope','y − 4 = 3(x − 1)'],['op_distribute','y − 4 = 3x − 3'],['op_solvey','y = 3x + 1']], check:'3(3) + 1 = 10   ✓', tq:'(2, 1)   (6, 9)', ta:'y = 2x − 3', tw:['m = 8/4 = 2','y − 1 = 2(x − 2)','y = 2x − 3']},
  'linear-absvalue-functions': {ex:'y = 2|x − 3| − 4', steps:[['op_vertex','y = a|x − h| + k  →  h = 3, k = −4  →  (3, −4)'],['op_direction','a = 2 > 0  →  ∨,  m = ±2'],['op_setzero','2|x − 3| − 4 = 0  →  |x − 3| = 2'],['op_twocases','x − 3 = 2  or  x − 3 = −2  →  x = 5  or  x = 1']], check:'2|5 − 3| − 4 = 0   ✓   2|1 − 3| − 4 = 0   ✓', tq:'y = −|x + 1| + 3', ta:'(−1, 3);   x = 2,  x = −4', tw:['h = −1, k = 3','|x + 1| = 3','x = 2 or x = −4']},
  'systems-equations': {ex:'x + y = 10\n2x − y = 5', steps:[['op_addeq','3x = 15'],['op_divboth','x = 5'],['op_substitute','5 + y = 10  →  y = 5']], check:'2(5) − 5 = 5   ✓   →   (5, 5)', tq:'y = 3x − 2\nx + y = 14', ta:'(4, 10)', tw:['x + (3x − 2) = 14','4x = 16  →  x = 4','y = 3(4) − 2 = 10']},
  'exponents-exponential': {ex:'(3x²)³ · x⁻⁴', steps:[['op_power','(3x²)³ = 3³ · x²·³ = 27x⁶'],['op_product','27x⁶ · x⁻⁴ = 27x⁶⁺⁽⁻⁴⁾ = 27x²'],['op_growth','A(t) = 200(1.05)ᵗ   →   1 + 0.05 = 1.05']], check:'x = 1:   (3)³ · 1 = 27 = 27(1)²   ✓', tq:'(2x⁴)² ÷ (4x³)', ta:'x⁵', tw:['(2x⁴)² = 4x⁸','4x⁸ ÷ 4x³ = x⁸⁻³','= x⁵']},
  'polynomials-factoring': {ex:'2x² + 7x + 3', steps:[['op_findac','a · c = 2 · 3 = 6   →   6 · 1,  6 + 1 = 7'],['op_split','2x² + 6x + x + 3'],['op_group','2x(x + 3) + 1(x + 3)'],['op_commonbin','(2x + 1)(x + 3)']], check:'(2x + 1)(x + 3) = 2x² + 6x + x + 3 = 2x² + 7x + 3   ✓', tq:'x² − 3x − 28', ta:'(x − 7)(x + 4)', tw:['−7 · 4 = −28','−7 + 4 = −3','(x − 7)(x + 4)']},
  'quadratic-functions': {ex:'y = x² − 4x − 5', steps:[['op_axis','x = −b/(2a) = 4/2 = 2'],['op_height','y = 2² − 4(2) − 5 = −9   →   (2, −9)'],['op_direction','a = 1 > 0   →   ∪,  min = −9'],['op_zeros','(x − 5)(x + 1) = 0   →   x = 5,  x = −1']], check:'(5 + (−1)) / 2 = 2   ✓', tq:'y = −x² + 6x − 1', ta:'(3, 8)', tw:['x = −6/(2·(−1)) = 3','y = −9 + 18 − 1 = 8']},
  'solving-quadratics': {ex:'x² − x − 12 = 0', steps:[['op_discrim','b² − 4ac = 1 + 48 = 49 > 0   →   2'],['op_factor','(x − 4)(x + 3) = 0'],['op_zeroprod','x − 4 = 0   or   x + 3 = 0'],['op_solveeach','x = 4   or   x = −3']], check:'4² − 4 − 12 = 0   ✓   (−3)² + 3 − 12 = 0   ✓', tq:'2x² − 3x − 2 = 0', ta:'x = 2,  x = −1/2', tw:['(2x + 1)(x − 2) = 0','x = −1/2 or x = 2']},
  'working-with-functions': {ex:'f(x) = 2x + 1\ng(x) = x²', steps:[['op_inner','g(3) = 3² = 9'],['op_outer','f(g(3)) = f(9) = 2(9) + 1 = 19'],['op_swap','y = 2x + 1   →   x = 2y + 1'],['op_solvey','f⁻¹(x) = (x − 1)/2']], check:'f⁻¹(19) = (19 − 1)/2 = 9   ✓', tq:'f(x) = 3x − 2\ng(x) = x + 4\nf(g(1)) = ?', ta:'13', tw:['g(1) = 5','f(5) = 15 − 2 = 13']},
  'analyzing-data': {ex:'2, 4, 4, 5, 10\nŷ = 2x + 1,   (3, 8)', steps:[['op_mean','(2 + 4 + 4 + 5 + 10) ÷ 5 = 25 ÷ 5 = 5'],['op_median','2, 4, [4], 5, 10   →   4'],['op_compare','5 > 4   ←   10'],['op_residual','ŷ = 2(3) + 1 = 7   →   8 − 7 = 1']], check:'5 · 5 = 25   ✓', tq:'3, 5, 6, 6, 10', ta:'x̄ = 6,   median = 6', tw:['30 ÷ 5 = 6','3, 5, [6], 6, 10']}
};
