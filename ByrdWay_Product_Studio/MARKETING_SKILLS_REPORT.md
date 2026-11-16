# Marketing Skills — inventory and compatibility report (Byrd Powerhouse 6.0.0)

- Source: https://github.com/coreyhaines31/marketingskills (commit `1f837447b20bb6f0e72d87b80ece1c221c362c7d`, 2026-11-11)
- License: MIT (Copyright (c) 2025 Corey Haines) — license file kept at `.claude/skills/LICENSE_marketingskills_MIT.txt`
- Installed: **53 skills** in `.claude/skills/` (instructions + reference docs). **43 active** in the existing 10 Revenue roles; 10 installed but not activated (reasons below).
- Excluded: **163 files** — executable code (Node/Python scripts, website tracking JS snippets) and eval test data: the Powerhouse never runs third-party code; markdown instructions and references only.
- Claude Code discovery check: PASS (0 problems). Verified live 2026-11-16: Claude Code listed all 53 skills from this folder and invoked `marketing-psychology` successfully.

| Skill | Version | Status | Existing role(s) | Owner guardrails added |
|---|---|---|---|---|
| ab-testing | 2.0.7 | ACTIVE | revenue_tracker | standard |
| ad-creative | 2.13.0 | ACTIVE | script_storyboard | Organic hooks and creative only; any paid generation tool needs owner approval. |
| ads | 2.7.5 | ACTIVE | sales_qa | Used only to JUDGE whether paid ads are worth it. No ad budget without owner approval. |
| ai-seo | 2.12.3 | ACTIVE | offer_pricing | standard |
| analytics | 2.2.5 | ACTIVE | revenue_tracker | standard |
| aso | 2.0.6 | NOT ACTIVATED: App Store / Google Play listings: ByrdWay sells on TpT, has no mobile app | - | standard |
| attribution | 1.1.9 | ACTIVE | revenue_tracker | standard |
| churn-prevention | 2.0.6 | ACTIVE | retention | Applies to repeat buyers and bundles only (no subscriptions to cancel). |
| co-marketing | 2.0.6 | ACTIVE | prospector | standard |
| cold-email | 2.2.4 | ACTIVE | sales_followup | Every message must pass compliance.presend_check (CAN-SPAM: sender, postal address, opt-out, honest subject) and the duplicate check. The app never sends email. |
| community-marketing | 2.0.5 | ACTIVE | prospector | standard |
| competitor-profiling | 2.1.8 | ACTIVE | market_research | standard |
| competitors | 2.3.3 | ACTIVE | market_research | standard |
| content-strategy | 2.1.8 | ACTIVE | offer_pricing, social_publisher | standard |
| conversion-tracking | 1.0.6 | NOT ACTIVATED: pixel/GA4 setup for an own website; its JS snippets were excluded as executable code | - | standard |
| copy-editing | 2.2.4 | ACTIVE | offer_pricing | standard |
| copywriting | 2.3.5 | ACTIVE | offer_pricing | standard |
| cro | 2.0.6 | ACTIVE | offer_pricing | standard |
| customer-research | 2.0.8 | ACTIVE | market_research | standard |
| directory-submissions | 2.2.0 | ACTIVE | offer_pricing | standard |
| emails | 2.1.7 | ACTIVE | sales_followup, retention | Only to people who opted in; compliance.presend_check applies. |
| events | 1.0.3 | ACTIVE | prospector | No booth, sponsorship or travel spend without owner approval. |
| free-tools | 2.0.6 | ACTIVE | sales_followup | standard |
| image | 2.0.6 | ACTIVE | script_storyboard, video_producer | Never generate a substitute Lil Dr. Byrd; approved assets only. |
| influencer-marketing | 1.4.3 | ACTIVE | prospector | No paid sponsorships or gifting budget without owner approval. |
| launch | 2.2.3 | ACTIVE | social_publisher | standard |
| lead-magnets | 2.1.5 | ACTIVE | sales_followup | standard |
| link-building | 1.0.4 | ACTIVE | offer_pricing | standard |
| marketing-council | 1.0.3 | ACTIVE | script_storyboard, sales_qa | Simulated perspectives for thinking only: never quote, impersonate or speak in a real person's name. |
| marketing-ideas | 2.0.5 | ACTIVE | market_research | standard |
| marketing-loops | 1.8.4 | ACTIVE | revenue_tracker | standard |
| marketing-plan | 1.2.5 | ACTIVE | revenue_tracker | standard |
| marketing-psychology | 2.0.3 | ACTIVE | offer_pricing, sales_qa | standard |
| offers | 1.0.6 | ACTIVE | offer_pricing | No fake urgency, scarcity or guarantees. |
| onboarding | 2.0.5 | NOT ACTIVATED: SaaS user onboarding: not applicable (Power Tools need no account) | - | standard |
| paywalls | 2.1.4 | NOT ACTIVATED: in-app paywalls: not applicable to TpT digital downloads | - | standard |
| popups | 2.0.4 | NOT ACTIVATED: website popups: ByrdWay has no own website today | - | standard |
| pricing | 2.1.7 | ACTIVE | offer_pricing | Live TpT prices never change. Price PROPOSALS for NEW products only, for owner approval. |
| product-marketing | 2.2.3 | ACTIVE | offer_pricing | standard |
| programmatic-seo | 2.1.3 | NOT ACTIVATED: template pages at scale on an own website: not applicable on TpT | - | standard |
| prospecting | 1.5.3 | ACTIVE | prospector | Public, permitted sources only: no scraping private contacts, no purchased lists. |
| public-relations | 1.2.4 | ACTIVE | prospector | standard |
| referrals | 2.2.4 | ACTIVE | retention | Voluntary, unpaid recommendations only. No referral payments or incentives (method AH-21 excluded). |
| reverse-engineer-marketing | 1.1.4 | ACTIVE | market_research | standard |
| revops | 2.2.4 | ACTIVE | revenue_tracker | standard |
| sales-enablement | 2.4.3 | ACTIVE | sales_followup | standard |
| schema | 2.0.5 | NOT ACTIVATED: JSON-LD for an own website: TpT controls listing markup | - | standard |
| seo-audit | 2.2.5 | ACTIVE | offer_pricing | standard |
| signup | 2.0.3 | NOT ACTIVATED: SaaS signup flows: not applicable | - | standard |
| site-architecture | 2.1.3 | NOT ACTIVATED: own-website structure: no own website today | - | standard |
| sms | 1.1.3 | NOT ACTIVATED: needs a paid SMS service and TCPA consent records: not active (zero-additional-spend rule) | - | standard |
| social | 2.5.2 | ACTIVE | social_publisher | standard |
| video | 2.4.3 | ACTIVE | script_storyboard, video_producer | Lil Dr. Byrd: approved image and the approved College Statistics voice only. |

Standard guardrails on every skill:
- Drafts and analysis only: the owner approves, sends and publishes.
- Market only Studio QA PASS + owner-approved products, linked to their exact TpT page.
- Never invent sales, traffic, conversion rates, testimonials, endorsements, credentials or outcomes.
- Zero additional spend: no new tools, ads, subscriptions or API charges without separate owner approval.
- Every output passes Sales QA before anyone sees it.

## Excluded files

- `ads/evals/evals.json`
- `influencer-marketing/evals/evals.json`
- `paywalls/evals/evals.json`
- `analytics/evals/evals.json`
- `launch/evals/evals.json`
- `content-strategy/evals/evals.json`
- `customer-research/evals/evals.json`
- `pricing/evals/evals.json`
- `lead-magnets/evals/evals.json`
- `video/evals/evals.json`
- `cold-email/evals/evals.json`
- `onboarding/evals/evals.json`
- `aso/evals/evals.json`
- `sales-enablement/evals/evals.json`
- `competitor-profiling/evals/evals.json`
- `directory-submissions/references/submission-tracker-template.csv`
- `directory-submissions/evals/evals.json`
- `signup/evals/evals.json`
- `marketing-psychology/evals/evals.json`
- `marketing-loops/evals/evals.json`
- `cro/evals/evals.json`
- `link-building/evals/evals.json`
- `events/evals/evals.json`
- `community-marketing/evals/evals.json`
- `churn-prevention/evals/evals.json`
- `product-marketing/evals/evals.json`
- `ab-testing/evals/evals.json`
- `conversion-tracking/scripts/check_recipes.py`
- `conversion-tracking/scripts/build_recipe.py`
- `conversion-tracking/evals/evals.json`
- `conversion-tracking/assets/gtm-recipes/README.md`
- `conversion-tracking/assets/gtm-recipes/event-map.json`
- `conversion-tracking/assets/snippets/thank-you-page.js`
- `conversion-tracking/assets/snippets/wix-scheduling.js`
- `conversion-tracking/assets/snippets/phone-click.js`
- `conversion-tracking/assets/snippets/webflow-forms.js`
- `conversion-tracking/assets/snippets/squarespace-forms.js`
- `conversion-tracking/assets/snippets/calendly.js`
- `conversion-tracking/assets/snippets/ws-form.js`
- `conversion-tracking/assets/snippets/elementor-forms.js`
- `conversion-tracking/assets/snippets/acuity-scheduling-field.html`
- `conversion-tracking/assets/snippets/ninja-forms.js`
- `conversion-tracking/assets/snippets/acuity-scheduling.js`
- `conversion-tracking/assets/snippets/divi-forms.js`
- `conversion-tracking/assets/snippets/README.md`
- `conversion-tracking/assets/snippets/tally.js`
- `conversion-tracking/assets/snippets/forminator.js`
- `conversion-tracking/assets/snippets/contact-form-7.js`
- `conversion-tracking/assets/snippets/formidable-forms.js`
- `conversion-tracking/assets/snippets/gravity-forms.js`
- `conversion-tracking/assets/snippets/generic-ajax-form.js`
- `conversion-tracking/assets/snippets/cal-com.js`
- `conversion-tracking/assets/snippets/wpforms.js`
- `conversion-tracking/assets/snippets/wix-forms.js`
- `conversion-tracking/assets/snippets/typeform.js`
- `conversion-tracking/assets/snippets/jotform.js`
- `conversion-tracking/assets/snippets/fluent-forms.js`
- `conversion-tracking/assets/snippets/file-download.js`
- `conversion-tracking/assets/snippets/hubspot-forms.js`
- `conversion-tracking/assets/snippets/framer-forms.js`
- `conversion-tracking/assets/gtm-recipes/detect/detect-hubspot-forms.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-fluent-forms.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-framer-forms.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-wix-scheduling.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-webflow-forms.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-typeform.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-tally.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-elementor-forms.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-acuity-scheduling.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-formidable-forms.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-wix-forms.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-cal-com.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-contact-form-7.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-file-download.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-generic-ajax-form.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-calendly.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-thank-you-page.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-phone-click.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-ninja-forms.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-squarespace-forms.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-forminator.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-divi-forms.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-gravity-forms.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-jotform.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-ws-form.json`
- `conversion-tracking/assets/gtm-recipes/detect/detect-wpforms.json`
- `conversion-tracking/assets/gtm-recipes/send/microsoft.json`
- `conversion-tracking/assets/gtm-recipes/send/meta.json`
- `conversion-tracking/assets/gtm-recipes/send/google-ads.json`
- `conversion-tracking/assets/gtm-recipes/send/tiktok.json`
- `conversion-tracking/assets/gtm-recipes/send/ga4.json`
- `conversion-tracking/assets/gtm-recipes/send/linkedin.json`
- `image/evals/evals.json`
- `copywriting/evals/evals.json`
- `ad-creative/assets/creative-review-template.html`
- `ad-creative/evals/evals.json`
- `popups/evals/evals.json`
- `offers/evals/evals.json`
- `marketing-plan/evals/evals.json`
- `sms/evals/evals.json`
- `seo-audit/evals/evals.json`
- `ai-seo/evals/evals.json`
- `co-marketing/evals/evals.json`
- `marketing-ideas/evals/evals.json`
- `competitors/evals/evals.json`
- `programmatic-seo/evals/evals.json`
- `marketing-council/evals/evals.json`
- `marketing-council/references/advisors/gary-halbert.md`
- `marketing-council/references/advisors/claude-hopkins.md`
- `marketing-council/references/advisors/gary-vaynerchuk.md`
- `marketing-council/references/advisors/david-ogilvy.md`
- `marketing-council/references/advisors/alex-hormozi.md`
- `marketing-council/references/advisors/rory-sutherland.md`
- `marketing-council/references/advisors/april-dunford.md`
- `marketing-council/references/advisors/byron-sharp.md`
- `marketing-council/references/advisors/eugene-schwartz.md`
- `marketing-council/references/advisors/russell-brunson.md`
- `marketing-council/references/advisors/seth-godin.md`
- `marketing-council/references/advisors/ann-handley.md`
- `site-architecture/evals/evals.json`
- `prospecting/evals/evals.json`
- `social/evals/evals.json`
- `reverse-engineer-marketing/scripts/teardown.mjs`
- `reverse-engineer-marketing/evals/evals.json`
- `reverse-engineer-marketing/references/industries/legal-professional-services.md`
- `reverse-engineer-marketing/references/industries/govtech-public-sector.md`
- `reverse-engineer-marketing/references/industries/ecommerce-dtc.md`
- `reverse-engineer-marketing/references/industries/cpg-food-beverage.md`
- `reverse-engineer-marketing/references/industries/mobile-apps-games.md`
- `reverse-engineer-marketing/references/industries/events-entertainment.md`
- `reverse-engineer-marketing/references/industries/manufacturing-industrial.md`
- `reverse-engineer-marketing/references/industries/crypto-web3.md`
- `reverse-engineer-marketing/references/industries/hospitality-travel.md`
- `reverse-engineer-marketing/references/industries/solar-home-energy.md`
- `reverse-engineer-marketing/references/industries/care-services.md`
- `reverse-engineer-marketing/references/industries/games-pc-console.md`
- `reverse-engineer-marketing/references/industries/media-creators.md`
- `reverse-engineer-marketing/references/industries/saas.md`
- `reverse-engineer-marketing/references/industries/healthcare.md`
- `reverse-engineer-marketing/references/industries/regulated-goods.md`
- `reverse-engineer-marketing/references/industries/logistics-transportation.md`
- `reverse-engineer-marketing/references/industries/marketplaces.md`
- `reverse-engineer-marketing/references/industries/retail.md`
- `reverse-engineer-marketing/references/industries/nonprofit.md`
- `reverse-engineer-marketing/references/industries/real-estate.md`
- `reverse-engineer-marketing/references/industries/insurance.md`
- `reverse-engineer-marketing/references/industries/consumer-hardware.md`
- `reverse-engineer-marketing/references/industries/agencies-b2b-services.md`
- `reverse-engineer-marketing/references/industries/finance.md`
- `reverse-engineer-marketing/references/industries/franchising.md`
- `reverse-engineer-marketing/references/industries/gambling-betting.md`
- `reverse-engineer-marketing/references/industries/local-services.md`
- `reverse-engineer-marketing/references/industries/fitness-wellness.md`
- `reverse-engineer-marketing/references/industries/education.md`
- `reverse-engineer-marketing/references/industries/automotive.md`
- `emails/evals/evals.json`
- `revops/evals/evals.json`
- `copy-editing/evals/evals.json`
- `referrals/evals/evals.json`
- `public-relations/evals/evals.json`
- `attribution/evals/evals.json`
- `schema/evals/evals.json`
- `free-tools/evals/evals.json`
