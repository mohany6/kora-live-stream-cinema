# Short Design: Blogger Google Search Console Redirect Error & Bot-Safe Adsterra Fix

**Date:** 2026-11-26  
**Target Domain:** `https://kora-live-to.blogspot.com/`  
**Size:** Small change (`scripts/build_modern_blogger_theme.py`, `blogger_theme/kora_pro_blogger_theme.xml`, regression tests, and GSC checklist)

## 1. Intent & Why
Resolve the recurring `Page is not indexed: Redirect error` (`Googlebot smartphone`) and `Sitemaps: Temporary processing error` on `kora-live-to.blogspot.com` so the blog indexes cleanly in Google Search while keeping 100% of Adsterra revenue (`6226474`) safe on Blogger and keeping Cloudflare Pages free of risky ad scripts.

## 2. Goals, Non-Goals & Anti-Goals
- **Goals:** Eliminate duplicate `<link rel='canonical'/>` emission in Blogger `<head>`, use canonical homepage linking (`data:blog.canonicalHomepageUrl`), shield `Googlebot` / Search Console WRS from executing third-party Adsterra scripts (`Popunder`, `SocialBar`, `Banner` loaders) while preserving all ad units for real human visitors, and document exact Search Console steps (`sitemap.xml` vs `atom.xml` and `?m=1` inspection).
- **Non-Goals:** Adding Adsterra JS tags to `kora-stream-cinema.pages.dev` or migrating away from Blogger.
- **Anti-Goals:** Never add `Disallow: /*?m=1` to `robots.txt` (which blocks `Googlebot smartphone` from following Blogger's mandatory mobile `302` redirect) and never use client-side URL-stripping hacks (`history.replaceState`) that cause redirect loops.

## 3. Constraints
- Generated XML (`blogger_theme/kora_pro_blogger_theme.xml`) must pass `xml.etree.ElementTree.parse()` and Node.js inline-script syntax checks (`test_theme_js_syntax.js`).
- All existing Adsterra placement URLs, keys, 20-minute Popunder frequency cap (`kora_popunder_last`), and Smartlink buttons must remain intact for human users and pass `tests/test_blogger_theme_ads.py`.

## 4. Approaches Considered
1. **Option 1 (Selected — Blogger Theme Fix + GSC Canonical Workflow):** Fix duplicate canonicals and bot-gate Adsterra script injection in the Blogger theme, remove bare `/atom.xml` in GSC, and inspect `?m=1` once so Google links the mobile `302` target to the clean canonical URL. *Trade-off:* 100% free, protects both Blogger and Cloudflare accounts, though Blogger's native `302 -> ?m=1` still requires Google's normal canonical consolidation cycle.
2. **Option 2 (Dual SEO Engine — Blogger + Static SEO Pages on Cloudflare Pages):** Apply Option 1 plus pre-render static HTML match pages and `sitemap.xml` on `kora-stream-cinema.pages.dev` for GSC only (no Adsterra scripts on Pages). *Trade-off:* Higher engineering scope; deferred since only Blogger is registered in GSC.
3. **Option 3 (Move Everything Including Adsterra to Cloudflare Pages):** Host articles and Adsterra scripts on `pages.dev`. *Rejected:* High risk of Cloudflare `Suspected Phishing` suspension and Adsterra `pages.dev` subdomain rejection.

## 5. Design Decisions
- **Single Canonical & Clean Meta (`build_modern_blogger_theme.py`):** Remove the redundant manual `<link expr:href='data:blog.canonicalUrl' rel='canonical'/>` (since `<b:include data='blog' name='all-head-content'/>` already emits the single authoritative canonical link), scope the static homepage `<meta name='description'/>` to `data:view.isHomepage`, and point the header brand link to `expr:href='data:blog.canonicalHomepageUrl'`.
- **Bot Guard + Deferred Human Ad Loading:** Introduce a lightweight `isSearchCrawler()` helper matching `Googlebot|InspectionTool|AdsBot|Mediapartners|Bingbot|HeadlessChrome|Lighthouse`. For crawlers, skip injecting external Adsterra scripts (`capitalhospitals.org` Popunder, `czernik.org` SocialBar/Banners) so WRS renders instantaneously with zero third-party redirects; for human visitors, load display banners asynchronously after DOM ready and trigger Popunder/SocialBar on first user interaction (`pointerdown`, `touchstart`, `scroll`, `mousemove`) or short fallback timer while keeping the 20-minute `localStorage` cap.
- **Google Search Console Operational Fix:** Delete bare `/atom.xml` from Sitemaps (keep `/sitemap.xml` only), inspect `https://kora-live-to.blogspot.com/?m=1` + one clean article URL once without spamming `Request Indexing`.
