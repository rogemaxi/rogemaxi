#!/usr/bin/env python3
"""Build the repaired Algebra 1 + Honors Power Tool from the untouched original.

Every edit is an exact-match replacement that must occur exactly once (or the
stated number of times); the build aborts otherwise, so nothing is changed blindly.
Usage: python3 tools/build.py   (run from algebra1-honors/)
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "original" / "ByrdWay_Algebra_Honors_Upgrade_V2.original.html"
OUT = ROOT / "ByrdWay_Algebra_Honors_Upgrade_V3.html"
LANGS = ["en", "es", "zh", "hi", "ar", "fr", "pt", "ru", "ht", "vi", "ko", "ja"]

html = SRC.read_text(encoding="utf-8")
log = []

def rep(old, new, count=1, tag=""):
    global html
    n = html.count(old)
    if n != count:
        sys.exit(f"[{tag}] expected {count} match(es), found {n}: {old[:90]!r}")
    html = html.replace(old, new)
    log.append(tag)

# ---------- D1/D2: original shell (global script) — dashboard, nav, How page, area tabs ----------
rep("function navBar(activeId, tab){",
    "/* ByrdWay V3 i18n repair: L(key, english) returns the selected-language string, else the original English. */\n"
    "function L(k,en){ return (window.BWM_T && window.BWM_T(k)) || en; }\n"
    "function navBar(activeId, tab){", tag="D2 helper L()")
for k, en in [("nav_cheat", "Cheat Sheet"), ("nav_blueprint", "Blueprint"), ("nav_flash", "Flashcards"),
              ("nav_testme", "Test Me"), ("nav_honors", "Honors Layer")]:
    rep(f"class=\"${{tab==='{ {'nav_cheat':'cheatsheet','nav_blueprint':'blueprint','nav_flash':'flashcards','nav_testme':'testme','nav_honors':'honors'}[k] }'?'active':''}}\">{en}</a>",
        f"class=\"${{tab==='{ {'nav_cheat':'cheatsheet','nav_blueprint':'blueprint','nav_flash':'flashcards','nav_testme':'testme','nav_honors':'honors'}[k] }'?'active':''}}\">${{esc(L('{k}','{en}'))}}</a>", tag="D2 nav "+k)
rep('<a href="#/home">Dashboard</a>\n      <a href="#/how">How This Works</a>\n      <a href="#/backmatter">Master Index</a>',
    "<a href=\"#/home\">${esc(L('nav_dashboard','Dashboard'))}</a>\n      <a href=\"#/how\">${esc(L('nav_how','How This Works'))}</a>\n      <a href=\"#/backmatter\">${esc(L('nav_index','Master Index'))}</a>",
    tag="D2 nav dashboard/how/index")

how = [("⚡", "Cheat Sheet", "nav_cheat", "how_cheat_d", "Give me what matters. Two pages. Formulas, traps, and quick recognition cues."),
       ("🧭", "Blueprint", "nav_blueprint", "how_blueprint_d", "Show me how it works. A 5-step SEE → IDENTIFY → CHOOSE → EXECUTE → CHECK decision engine."),
       ("🗂️", "Flashcards", "nav_flash", "how_flash_d", "Help me remember it. Real visual retrieval cards across 8 distinct types."),
       ("✅", "Test Me", "nav_testme", "how_testme_d", "Tell me if I'm ready. Foundation → Proficient → Advanced → Honors."),
       ("🎓", "Honors Layer", "nav_honors", "how_honors_d", "Push me further. Why / What-If / Prove / Generalize / Defend — depth, not just harder numbers."),
       ("🎬", "Interactive", "nav_interactive", "how_interactive_d", "Show me / let me practice / help me think — curated pathways, only when they add value.")]
for ic, h, hk, dk, d in how:
    rep(f'<div class="how-ic">{ic}</div><h3>{h}</h3><p>{d}</p>',
        f'<div class="how-ic">{ic}</div><h3>${{esc(L(\'{hk}\',{json.dumps(h)}))}}</h3><p>${{esc(L(\'{dk}\',{json.dumps(d)}))}}</p>', tag="D2 how "+hk)
rep("<h2>How This Works</h2>\n  <div class=\"how-grid\">", "<h2>${esc(L('nav_how','How This Works'))}</h2>\n  <div class=\"how-grid\">", tag="D2 how title")
rep("Go to Home Dashboard →</button>", "${esc(L('how_cta','Go to Home Dashboard →'))}</button>", tag="D2 how cta")
rep('<div class="tile-name">${a.area}</div>\n    </a>`).join(\'\');\n  return `<div class="page">\n    <h2>What are you working on?</h2>',
    "<div class=\"tile-name\">${esc(L('area_'+a.id,a.area))}</div>\n    </a>`).join('');\n  return `<div class=\"page\">\n    <h2>${esc(L('home_working','What are you working on?'))}</h2>",
    tag="D1 home tiles + heading")
rep('<h2 style="margin-top:36px">What do you need right now?</h2>',
    "<h2 style=\"margin-top:36px\">${esc(L('home_need','What do you need right now?'))}</h2>", tag="D1 home need heading")
needs = [("I have a test / need it fast", "→ Cheat Sheet"), ("I don't get it", "→ Blueprint"), ("I need to remember it", "→ Flashcards"),
         ("Show me", "→ Learn It (in each area)"), ("I need practice", "→ Practice It (in each area)"),
         ("Help me think", "→ Tutor Me with Khanmigo (where eligible)"), ("Am I ready?", "→ Test Me"), ("Push me further", "→ Honors Layer")]
for i, (b, p) in enumerate(needs, 1):
    rep(f'<div class="needcard"><b>{b}</b><p>{p}</p></div>',
        f"<div class=\"needcard\"><b>${{esc(L('need{i}_b',{json.dumps(b)}))}}</b><p>${{esc(L('need{i}_p',{json.dumps(p)}))}}</p></div>", tag=f"D1 need{i}")
for tab, ic, k, en in [("cheatsheet", "⚡", "nav_cheat", "Cheat Sheet"), ("blueprint", "🧭", "nav_blueprint", "Blueprint"),
                       ("flashcards", "🗂️", "nav_flash", "Flashcards"), ("testme", "✅", "nav_testme", "Test Me"),
                       ("honors", "🎓", "nav_honors", "Honors Layer"), ("interactive", "🎬", "nav_interactive", "Interactive")]:
    rep(f"class=\"${{tab==='{tab}'?'on':''}}\">{ic} {en}</a>",
        f"class=\"${{tab==='{tab}'?'on':''}}\">{ic} ${{esc(L('{k}','{en}'))}}</a>", tag="D2 area tab "+tab)

# ---------- D1: dashboard additions inside the mastery IIFE ----------
rep("'<h1>Dashboard</h1>'+hubBlock()", "'<h1>'+esc(t('dash_h1'))+'</h1>'+hubBlock()", tag="D1 dashboard h1")
rep('<h2>Learning Engines</h2><p>Pick an area, then choose the kind of help you need.</p><label for="bwm-engine-area">Learning area</label>',
    "<h2>${esc(t('eng_title'))}</h2><p>${esc(t('eng_pick'))}</p><label for=\"bwm-engine-area\">${esc(t('eng_area'))}</label>", tag="D1 engines head")
rep("${esc(a.area)}</option>`).join('')}</select>", "${esc(areaName(a.id))}</option>`).join('')}</select>", tag="D1 engines area names")
rep("[['cheatsheet','Cheat Sheets'],['blueprint','Blueprints'],['flashcards','Flashcards'],['testme','Test Me'],['interactive','Interactive Support'],['interactive','AI Tutor']].map(([tab,label])=>`<a class=\"bwm-btn ghost\" data-engine-tab=\"${tab}\" href=\"#/area/${dashboardEngineArea}/${tab}\">${label}</a>`).join('')}</div><p class=\"bwm-note\">AI Tutor provides tutoring prompts and external resources; it is not a built-in conversational chatbot.</p>",
    "[['cheatsheet','eng_cheat'],['blueprint','eng_blueprint'],['flashcards','eng_flash'],['testme','eng_testme'],['interactive','eng_interactive'],['interactive','eng_tutor']].map(([tab,label])=>`<a class=\"bwm-btn ghost\" data-engine-tab=\"${tab}\" href=\"#/area/${dashboardEngineArea}/${tab}\">${esc(t(label))}</a>`).join('')}</div><p class=\"bwm-note\">${esc(t('eng_note'))}</p>",
    tag="D1 engines buttons")
rep("block.innerHTML=`<h2>Five EOC Assessments</h2><p>Each assessment has 15 questions. The multiple-choice threshold is 12/15; written reasoning tasks have separate teacher review.</p>",
    "block.innerHTML=`<h2>${esc(t('dash_eoc_t'))}</h2><p>${esc(t('dash_eoc_d'))}</p>", tag="D1 dashboard EOC block")
rep("'/results':''}\">EOC ${c.n}</a>`).join('')}</div>`;page.appendChild(block);",
    "'/results':''}\">${esc(t('dash_eoc_n',{n:c.n}))}</a>`).join('')}</div>`;page.appendChild(block);", tag="D1 dashboard EOC links")
rep("onclick=\"BWM.startTour()\">How Do I Use This? · Show Me Around!</button><a href=\"#/how\">How This Works</a></div>'",
    "onclick=\"BWM.startTour()\">'+esc(t('help_tour'))+'</button><a href=\"#/how\">'+esc(t('nav_how'))+'</a></div>'", tag="D1 help tour button")

# ---------- D1: onboarding tour ----------
rep("el.setAttribute('aria-labelledby','bwm-tour-invite-title');el.setAttribute('lang','en');el.setAttribute('dir','ltr');\n el.innerHTML=`<h2 id=\"bwm-tour-invite-title\">Welcome to ByrdWay!</h2><p>Your math command center is ready. Want a quick, hands-on look around? About 60 seconds, at your pace.</p><button type=\"button\" class=\"bwm-btn\" onclick=\"BWM.startTour()\">Show Me Around!</button><button type=\"button\" class=\"bwm-btn ghost\" onclick=\"BWM.skipTour()\">Skip Tour</button>`;",
    "el.setAttribute('aria-labelledby','bwm-tour-invite-title');el.setAttribute('lang',DB.lang);el.setAttribute('dir',langDir());\n el.innerHTML=invitationHTML();",
    tag="D1 tour invitation")
rep("function renderTour(){",
    "function invitationHTML(){return `<h2 id=\"bwm-tour-invite-title\">${esc(t('inv_title'))}</h2><p>${esc(t('inv_p'))}</p><button type=\"button\" class=\"bwm-btn\" onclick=\"BWM.startTour()\">${esc(t('tour_show'))}</button><button type=\"button\" class=\"bwm-btn ghost\" onclick=\"BWM.skipTour()\">${esc(t('tour_skip'))}</button>`;}\nfunction renderTour(){",
    tag="D1 tour invitationHTML")
rep("const titles=['Welcome aboard!','Find your starting point','Try your learning engines','Your first small win','Your mission begins!'];",
    "const titles=[1,2,3,4,5].map(n=>esc(t('tour_t'+n)));", tag="D1 tour titles")
start = html.index(" const descriptions=[\n 'This is your dashboard")
end = html.index(" ];\n", start) + len(" ];\n")
html = html[:start] + " const descriptions=[1,2,3,4,5].map(n=>esc(t('tour_d'+n)));\n" + html[end:]
log.append("D1 tour descriptions")
rep("[['flashcards','Flip a flashcard'],['testme','Reveal a solution'],['cheatsheet','Open a cheat sheet']].map(([mode,label])=>`<button type=\"button\" class=\"bwm-btn ghost\" aria-pressed=\"${tourMode===mode}\" onclick=\"BWM.tourEngine('${mode}')\">${label}",
    "[['flashcards','tour_flip'],['testme','tour_reveal'],['cheatsheet','tour_cheat']].map(([mode,label])=>`<button type=\"button\" class=\"bwm-btn ghost\" aria-pressed=\"${tourMode===mode}\" onclick=\"BWM.tourEngine('${mode}')\">${esc(t(label))}",
    tag="D1 tour engine buttons")
rep("${tourVisited.has('flipped')?'Flashcard flipped — nice discovery! ':''}${tourVisited.has('revealed')?'Solution revealed — notice the Why.':''}</p>`;",
    "${tourStatusText()}</p>`;", tag="D1 tour status")
rep("activity=`<p><strong>${esc(q.q)}</strong></p><div class=\"bwm-tour-tools\" role=\"group\" aria-label=\"Tour practice answers\">",
    "activity=`<p><strong>${esc(t('tour_q'))}</strong></p><div class=\"bwm-tour-tools\" role=\"group\" aria-label=\"${esc(t('tour_answers'))}\">", tag="D1 tour question")
rep("${tourTry===null?'Choose an answer. It will not affect your diagnostic or EOC records.':tourTry===6?'Yes! '+esc(q.explain):'Good try! Undo the +9 first, then divide by 4. Try again — you can do this.'}</p>`;}",
    "${esc(tourTry===null?t('tour_choose'):tourTry===6?t('tour_yes'):t('tour_retry'))}</p>`;}", tag="D1 tour feedback")
rep("onclick=\"BWM.finishTour(false)\">Find a lesson</a> <a href=\"#/eoc\" class=\"bwm-btn ghost\" onclick=\"BWM.finishTour(false)\">Explore five EOCs</a></p>';",
    "onclick=\"BWM.finishTour(false)\">'+esc(t('tour_find_lesson'))+'</a> <a href=\"#/eoc\" class=\"bwm-btn ghost\" onclick=\"BWM.finishTour(false)\">'+esc(t('tour_explore_eoc'))+'</a></p>';",
    tag="D1 tour final links")
rep("el.setAttribute('aria-labelledby','bwm-tour-title');el.setAttribute('lang','en');el.setAttribute('dir','ltr');",
    "el.setAttribute('aria-labelledby','bwm-tour-title');el.setAttribute('lang',DB.lang);el.setAttribute('dir',langDir());", tag="D1 tour coach lang")
rep("el.innerHTML=`<p class=\"bwm-tour-kicker\">SHOW ME AROUND! · <span aria-live=\"polite\">Step ${tourStep+1} of 5</span></p><progress max=\"5\" value=\"${tourStep+1}\" aria-label=\"Tour progress\">",
    "el.innerHTML=`<p class=\"bwm-tour-kicker\">${esc(t('tour_kicker'))} · <span aria-live=\"polite\">${esc(t('tour_step',{n:tourStep+1}))}</span></p><progress max=\"5\" value=\"${tourStep+1}\" aria-label=\"${esc(t('tour_progress'))}\">",
    tag="D1 tour kicker")
rep("onclick=\"BWM.backTour()\">Back</button>${tourStep<4?'<button type=\"button\" class=\"bwm-btn\" onclick=\"BWM.nextTour()\">Next →</button>':'<button type=\"button\" class=\"bwm-btn\" onclick=\"BWM.finishTour(true)\">Finish Tour</button><button type=\"button\" class=\"bwm-btn alt\" onclick=\"BWM.beginAfterTour()\">Begin Diagnostic</button>'}<button type=\"button\" class=\"bwm-btn ghost\" onclick=\"BWM.skipTour()\">Skip Tour</button><button type=\"button\" class=\"bwm-btn ghost\" onclick=\"BWM.exitTour()\">Exit</button><button type=\"button\" class=\"bwm-btn ghost\" onclick=\"BWM.startTour()\">Replay Tour</button></div><p class=\"bwm-tour-note\">Optional tour. Use the highlighted real controls above. Escape exits anytime.</p>`;",
    "onclick=\"BWM.backTour()\">${esc(t('tour_back'))}</button>${tourStep<4?`<button type=\"button\" class=\"bwm-btn\" onclick=\"BWM.nextTour()\">${esc(t('tour_next'))}</button>`:`<button type=\"button\" class=\"bwm-btn\" onclick=\"BWM.finishTour(true)\">${esc(t('tour_finish'))}</button><button type=\"button\" class=\"bwm-btn alt\" onclick=\"BWM.beginAfterTour()\">${esc(t('tour_begin'))}</button>`}<button type=\"button\" class=\"bwm-btn ghost\" onclick=\"BWM.skipTour()\">${esc(t('tour_skip'))}</button><button type=\"button\" class=\"bwm-btn ghost\" onclick=\"BWM.exitTour()\">${esc(t('tour_exit'))}</button><button type=\"button\" class=\"bwm-btn ghost\" onclick=\"BWM.startTour()\">${esc(t('tour_replay'))}</button></div><p class=\"bwm-tour-note\">${esc(t('tour_note'))}</p>`;",
    tag="D1 tour footer")
rep("const status=document.getElementById('bwm-tour-action-status');if(status)status.textContent=(tourVisited.has('flipped')?'Flashcard flipped — nice discovery! ':'')+(tourVisited.has('revealed')?'Solution revealed — notice the Why.':'');});",
    "const status=document.getElementById('bwm-tour-action-status');if(status)status.textContent=tourStatusText();});", tag="D1 tour click status")
rep("const status=document.getElementById('bwm-tour-action-status');if(status)status.textContent='Flashcard flipped — nice discovery!';}});",
    "const status=document.getElementById('bwm-tour-action-status');if(status)status.textContent=tourStatusText();}});", tag="D1 tour key status")

# ---------- D3: backup controls, storage and dialog messages ----------
rep("<p>Progress stays in this browser; it is not a cloud account. Export a backup before changing devices. ${esc(controlT(\"coverage_notice\",{n:BWM_LOCALIZATION_MISSING[DB.lang]||0}))}</p>",
    "<p>${esc(t('ctl_local'))} ${esc(t('coverage_notice'))}</p>", tag="D3 controls text")
rep("if(el)el.textContent='Progress could not be saved. Export a JSON backup now.';else alert('Progress could not be saved. Export a JSON backup from the Mastery Hub.');}}",
    "if(el)el.textContent=t('save_failed');else alert(t('save_failed_alert'));}}", tag="D3 save failure")
rep("!confirm('Replace the diagnostic in progress with a new 40-question attempt?')", "!confirm(t('confirm_extended'))", tag="D3 confirm extended")
rep("if(!confirm('Replace current progress with this validated backup?'))return;", "if(!confirm(t('confirm_import')))return;", tag="D3 confirm import")
rep("alert('Backup was not imported: '+e.message);", "alert(t('import_failed',{e:e.message}));", tag="D3 import failure")
rep("if(!confirm('Delete all progress in this browser? Export a backup first.'))return;", "if(!confirm(t('confirm_reset')))return;", tag="D3 confirm reset")

# ---------- D3: study plan (final renderPlan override) ----------
rep("<p>${g.n<5?'Insufficient evidence for proficiency':provisional?'Provisional proficiency; confirm through a fresh assessment':'Further practice needed'}. Latest responses to ${g.n} distinct questions. Descriptive 95% interval: ${pct(interval[0])}–${pct(interval[1])}; this sample is adaptive and is not a calibrated ability estimate.</p><p>${errors.length?'Recommended because incorrect responses involved '+esc([...new Set(errors)].join(', '))+'.':'No error observed in this sample; use transfer practice to confirm.'}</p>${prereq.length?`<p>Study these prerequisites first: ${prereq.map",
    "<p>${esc(t(g.n<5?'plan_insufficient':provisional?'plan_provisional':'plan_further'))}. ${esc(t('plan_interval',{n:g.n,lo:pct(interval[0]),hi:pct(interval[1])}))}</p><p>${errors.length?esc(t('plan_because',{skills:[...new Set(errors)].map(skillName).join(', ')})):esc(t('plan_no_error'))}</p>${prereq.length?`<p>${esc(t('plan_prereq_first'))} ${prereq.map",
    tag="D3 plan card evidence")
rep("<p>${DB.lessons[a.id]?'Lesson recorded as studied.':'Study the lesson, complete guided and independent practice, and check your answers.'} ${provisional?'Proceed to honors transfer and the next EOC.':'After correcting each missed skill and completing the lesson check, take a fresh reassessment.'}</p></section>`;}).join('');",
    "<p>${esc(t(DB.lessons[a.id]?'plan_studied':'plan_study_next'))} ${esc(t(provisional?'plan_go_honors':'plan_reassess'))}</p></section>`;}).join('');",
    tag="D3 plan card next step")
rep("const list=ss=>ss.length?ss.map(s=>`<li>${esc(s.skill)} · ",
    "const list=ss=>ss.length?ss.map(s=>`<li>${esc(skillName(s.skill))} · ", tag="D3 plan skill names")
rep("report.misconceptions.slice(0,8).map(m=>`<li>${esc(m.tag.replace(/-/g,' '))}: ${m.distinctItems} distinct items, ${m.observations} error observations. ${m.distinctItems>=2?'Recurring pattern; explain the correction before reassessment.':'Candidate error; further evidence required.'}</li>`).join(''):'<li>No specific recurring misconception has been established.</li>';",
    "report.misconceptions.slice(0,8).map(m=>`<li>${esc(t(m.distinctItems>=2?'plan_mis_recurring':'plan_mis_candidate',{tag:tagName(m.tag),d:m.distinctItems,o:m.observations}))}</li>`).join(''):`<li>${esc(t('plan_mis_none'))}</li>`;",
    tag="D3 plan misconceptions")
rep("`<li><a href=\"#/eoc/${key.slice(2)}/results\">EOC ${key.slice(2)}: ${r.correct}/${r.total}</a> · ${r.correct/r.total>=.8?'80% multiple-choice threshold met; continue with the performance task and next level.':'Below 80%; use the area and skill recommendations below before retaking.'}</li>`",
    "`<li><a href=\"#/eoc/${key.slice(2)}/results\">${esc(t('dash_eoc_n',{n:key.slice(2)}))}: ${r.correct}/${r.total}</a> · ${esc(t(r.correct/r.total>=.8?'plan_eoc_met':'plan_eoc_below'))}</li>`",
    tag="D3 plan EOC progression")
rep("<section class=\"cs-page\"><p>Observed performance: ${report.correct}/${report.total} distinct questions. Recommendations combine the latest response to each item across diagnostic and EOC attempts; repeating the same question adds no proficiency evidence. Priority is prerequisite gaps, observed weakness, then curriculum order. Five distinct area responses and 80% correct establish provisional proficiency only.</p>",
    "<section class=\"cs-page\"><p>${esc(t('plan_observed',{c:report.correct,n:report.total}))}</p>", tag="D3 plan summary")

# ---------- D3: expanded lessons + EOC written-task chrome ----------
rep("${DB.lang!=='en'?'<p class=\"hint\">These expanded lessons are authored in English. Their complete translation has not been verified.</p>':''}",
    "${DB.lang!=='en'?`<p class=\"hint\" role=\"note\">${esc(t('lessons_en_only'))}</p>`:''}", tag="D3 lesson notice")
rep("renderEocList=function(){return beforePerformanceEoc()+`<div class=\"cs-page\" lang=\"en\" dir=\"ltr\"><h3>Written evidence beyond multiple choice</h3><p>Five supplementary tasks build from application to sustained investigations. Open a checkout result to draft and resume its written task. Checkouts 4 and 5 require multiple sessions, evidence comparison, revision, proof, and transfer. Written-task text is available in English.</p></div>`;};",
    "renderEocList=function(){return beforePerformanceEoc()+`<div class=\"cs-page\"><h3>${esc(t('eoc_written_t'))}</h3><p>${esc(t('eoc_written_d'))}</p></div>`;};",
    tag="D3 EOC written block")

# ---------- A1/A2: adaptive diagnostic ----------
rep(" const target=g.n===0?2:g.c===g.n?Math.min(5,2+g.n):g.c===0?1:3;",
    " /* V3: global staircase (start 2, ±0.5 per answer, 1–5) blended with this area's last response (±1). */\n"
    " const seen=p.ids.filter(id=>p.answers[id]!==undefined).map(id=>BANK_BY_ID[id]).filter(Boolean),right=seen.filter(q=>p.answers[q.id]===0).length;\n"
    " const level=Math.max(1,Math.min(5,2+0.5*(right-(seen.length-right)))),last=seen.filter(q=>q.a===area).at(-1);\n"
    " const target=last?Math.max(1,Math.min(5,Math.round((level+last.difficulty+(p.answers[last.id]===0?1:-1))/2))):Math.max(1,Math.min(5,Math.round(level)));",
    tag="A1 adaptive target")
rep("reason:'coverage → evidence weakness → difficulty distance → stable ID'",
    "reason:'coverage → evidence weakness → staircase difficulty (overall level + area response) → difficulty distance → stable ID'", tag="A1 trace reason")
rep(" if(key==='diag'){\n  const p=DB.progress.diag;\n  html=html.replace(/onclick=\"BWM.go\\('diag',\\d+\\)\"/g,match=>match);",
    " if(key==='diag'){\n  const p=DB.progress.diag;\n  html=html.replace(/onclick=\"BWM.go\\('diag',\\d+\\)\"/g,match=>match);\n"
    "  if(p.idx!==p.ids.length-1)html=html.replace(/<button type=\"button\" class=\"bwm-opt /g,'<button type=\"button\" disabled class=\"bwm-opt ').replace('<div class=\"bwm-opts\"',`<p class=\"bwm-note\" role=\"note\">${esc(t('diag_locked'))}</p><div class=\"bwm-opts\"`);",
    tag="A2 lock answered adaptive items")

# ---------- D1: localized solution steps in results review ----------
rep("<details><summary>${esc(t('solution'))}</summary><ol class=\"bwm-steps\">${q.w.map((w,k)=>`<li><span class=\"bwm-sn\">${k+1}</span>${math(w)}</li>`).join('')}</ol></details>",
    "<details><summary>${esc(t('solution'))}</summary><ol class=\"bwm-steps\">${q.w.map((w,k)=>`<li><span class=\"bwm-sn\">${k+1}</span>${stepHTML(w)}</li>`).join('')}</ol></details>",
    tag="D1 results solution steps")

# ---------- L1–L4: language system (injected inside the mastery IIFE, before its listeners) ----------
ui = {l: json.loads((ROOT / "i18n" / f"ui.{l}.json").read_text(encoding="utf-8")) for l in LANGS}
content = {l: json.loads((ROOT / "i18n" / f"content.{l}.json").read_text(encoding="utf-8")) for l in LANGS}
for l in LANGS:
    missing = set(ui["en"]) - set(ui[l])
    if missing: sys.exit(f"ui.{l}.json missing keys: {sorted(missing)[:8]}")
    for part in ("stems", "prose", "skills", "tags"):
        if len(content[l][part]) != len(content["en"][part]):
            sys.exit(f"content.{l}.json {part}: {len(content[l][part])} != {len(content['en'][part])}")
repair = {}
for l in LANGS:
    d = dict(ui[l])
    for part, prefix in (("stems", ""), ("prose", "w:"), ("skills", "skill:"), ("tags", "tag:")):
        for en, tr in zip(content["en"][part], content[l][part]):
            d[prefix + en] = tr
    repair[l] = d
inject = (
    "/* ===== ByrdWay V3 language repair: one selected language across every rendered screen. ===== */\n"
    "const BWM_REPAIR_I18N=" + json.dumps(repair, ensure_ascii=False, separators=(",", ":")) + ";\n"
    "for(const [l] of BWM_LANGS)Object.assign(BWM_I18N[l]||(BWM_I18N[l]={}),BWM_REPAIR_I18N[l]);\n"
    "window.BWM_T=function(k){if(DB.lang==='en')return undefined;const s=BWM_I18N[DB.lang]&&BWM_I18N[DB.lang][k];return typeof s==='string'?s:undefined;};\n"
    "/* EOC items carry skill 'EOC reasoning: <stem key>'; show the stem wording instead of the raw key. */\n"
    "function skillName(code){const m=/^EOC reasoning: (.*)$/.exec(code);if(m){let s=t(m[1]);if(s.length>60)s=s.slice(0,57)+'…';return t('eoc_reasoning')+': '+s;}const k='skill:'+code,s=t(k);return (s===k||DB.lang==='en')?code:s;}\n"
    "function tagName(code){const k='tag:'+code,s=t(k);return (s===k||DB.lang==='en')?code.replace(/-/g,' '):s;}\n"
    "function tourStatusText(){return (tourVisited.has('flipped')?t('tour_flipped')+' ':'')+(tourVisited.has('revealed')?t('tour_revealed'):'');}\n"
    "/* Prose solution lines are words, not math: show them translated; keep pure math language-neutral. */\n"
    "function stepHTML(w){if(DB.lang==='en')return math(w);const m=/^Answer: (.*)$/.exec(w);if(m)return `<span>${esc(t('ans_label'))}:</span> ${math(m[1])}`;const k='w:'+w,s=t(k);return s!==k?`<span>${esc(s)}</span>`:math(w);}\n"
    "const EN_ONLY_TABS=['cheatsheet','blueprint','flashcards','testme','honors','interactive'];\n"
    "function syncLanguage(){\n"
    " const root=document.documentElement;root.lang=DB.lang;root.dir=langDir();\n"
    " const parts=(location.hash||'#/home').replace('#/','').split('/');\n"
    " const links=document.querySelector('#app .navlinks');\n"
    " if(links&&!links.querySelector('#bwm-lang-nav')){const opts=BWM_LANGS.map(l=>`<option value=\"${l[0]}\" ${l[0]===DB.lang?'selected':''}>${l[1]}</option>`).join('');\n"
    "  links.insertAdjacentHTML('beforeend',`<label class=\"bwm-navlang\" title=\"${esc(t('lang_label'))}\">🌐 <span class=\"bwm-sr\">${esc(t('lang_label'))}</span><select id=\"bwm-lang-nav\" class=\"bwm-select\" translate=\"no\" aria-label=\"${esc(t('lang_label'))}\" onchange=\"BWM.setLang(this.value)\">${opts}</select></label>`);}\n"
    " const enOnly=(parts[0]==='area'&&EN_ONLY_TABS.includes(parts[2]||'cheatsheet'))||parts[0]==='backmatter';\n"
    " const page=document.querySelector('#app > .page');\n"
    " if(enOnly&&page){page.setAttribute('lang','en');page.setAttribute('dir','ltr');\n"
    "  if(DB.lang!=='en'&&!document.getElementById('bwm-en-only'))page.insertAdjacentHTML('afterbegin',`<p id=\"bwm-en-only\" class=\"bwm-note bwm-en-only\" role=\"note\" lang=\"${DB.lang}\" dir=\"${langDir()}\">${esc(t('en_only_notice'))}</p>`);}\n"
    " document.querySelectorAll('#app .area-tabbar, #app .topnav').forEach(el=>{el.setAttribute('lang',DB.lang);el.setAttribute('dir',langDir());});\n"
    " document.querySelectorAll('#app > .page:not([lang])').forEach(el=>{el.setAttribute('lang',DB.lang);el.setAttribute('dir',langDir());});\n"
    "}\n"
    "const beforeLanguageRoute=bwmRoute;\n"
    "bwmRoute=function(){beforeLanguageRoute();syncLanguage();};\n"
    "const baseSetLang=window.BWM.setLang;\n"
    "window.BWM.setLang=function(l){baseSetLang(l);syncLanguage();const inv=document.getElementById('bwm-tour-invitation');if(inv){inv.setAttribute('lang',DB.lang);inv.setAttribute('dir',langDir());inv.innerHTML=invitationHTML();}if(tourStep>=0)renderTour();document.querySelectorAll('#bwm-lang,#bwm-lang-nav').forEach(s=>{s.value=DB.lang;});};\n"
    "document.documentElement.lang=DB.lang;document.documentElement.dir=langDir();\n"
)
rep("\nwindow.addEventListener('hashchange', bwmRoute);\nwindow.addEventListener('DOMContentLoaded', bwmRoute);\n\n})();",
    "\n" + inject + "\nwindow.addEventListener('hashchange', bwmRoute);\nwindow.addEventListener('DOMContentLoaded', bwmRoute);\n\n})();",
    tag="L1-L4 language system")
rep("<style id=\"bwm-style\">",
    "<style id=\"bwm-v3-i18n\">.bwm-navlang{display:inline-flex;align-items:center;gap:4px;margin-inline-start:8px}.bwm-navlang .bwm-select{min-height:44px;max-width:11em}.bwm-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}.topnav .navlinks a{white-space:nowrap}.bwm-en-only{border:1px solid #fbbf24;border-radius:10px;padding:10px 14px;margin:0 0 16px;color:#fde68a}</style>\n<style id=\"bwm-style\">",
    tag="L2 picker + notice styles")

OUT.write_text(html, encoding="utf-8")
print(f"OK: {len(log)} verified edits -> {OUT.name} ({len(html):,} bytes)")
