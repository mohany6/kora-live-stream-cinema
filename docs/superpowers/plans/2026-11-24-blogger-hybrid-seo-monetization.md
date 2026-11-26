# المنظومة الهجينة (Blogger SEO + Cloudflare Tunnel + Adsterra) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** تزويد المستخدم بمنظومة متكاملة ومجانية 100% لربط منصة كرة القدم الحية بمدونة Blogger لجلب زوار محركات بحث Google (SEO) وتحقيق أقصى عائد مادي من Adsterra وعروض التسويق بالعمولة (1xBet / Melbet) دون الحاجة لأي صلاحيات مسؤول (Admin Rights) على حاسوبه.

**Architecture:** 
1. مشغل محمول غير متطلب لصلاحيات مسؤول (`run_kora_free.bat`) يطلق السيرفر الموحد وأداة `.tools\cloudflared.exe` ويستخرج رابط الـ HTTPS العام وينسخه للحافظة تلقائياً.
2. محرك توليد مقالات رياضية احترافية (`article_generator.py` + API endpoint) متوافق مع معايير Google Schema.org (`SportsEvent`) وأزرار توجيه آمنة (`rel="noopener noreferrer"`).
3. زر تفاعلي بنقرة زر واحدة في لوحة التحكم (`AdminPanel.jsx`) لنسخ مقال أي مباراة لـ Blogger فورياً.
4. حزمة توثيق إعلانات Adsterra ودليل Blogger المتكامل.

**Tech Stack:** Python 3.12, FastAPI, React 18, Vite, Tailwind CSS, Batch Scripting, Schema.org Microdata, Adsterra Direct Link & Scripts.

**Spec:** [docs/superpowers/specs/2026-11-24-blogger-hybrid-seo-monetization-design.md](file:///C:/Users/Mohany/Desktop/football-live-score-platform/docs/superpowers/specs/2026-11-24-blogger-hybrid-seo-monetization-design.md)

## Global Constraints

- تكلفة الاستضافة والدومين: \$0 مجاناً بالكامل.
- لا يتطلب أي صلاحيات مسؤول (Zero Admin Rights / Non-Elevated Standard User).
- الحفاظ على لغة الواجهة العربية RTL مع أسماء أندية موحدة.
- عزل مشغلات البث المباشر خارج نطاق `*.blogspot.com` لحماية حساب Blogger من إشعارات DMCA.

## Review Focus

1. **Tunnel Log Parsing Flakiness:** إذا تأخرت أداة `cloudflared` في إخراج الرابط، يجب ألا يتجمد السكريبت بل يقوم بالمحاولة المتكررة وإشعار المستخدم.
2. **Missing Match Metadata in Article:** في حال عدم توفر القناة الناقلة أو اسم المعلق في بيانات المباراة، يجب أن يولد المقال قيماً افتراضية جذابة (مثل: "سيتم التحديد قبل المباراة") دون أخطاء برمجية.
3. **Clipboard Permission in Browser:** يجب أن يعمل زر "نسخ المقال" في لوحة التحكم في بيئات HTTP المحلية و HTTPS العامة بسلاسة مع توفير fallback في حال تعذر الوصول للـ Clipboard API.
4. **Adsterra Direct Link Fallback:** في حال لم يقم المستخدم بإدخال رابط Adsterra المخصص، يجب أن تتصرف الأزرار بشكل طبيعي وتنقل الزائر مباشرة لصفحة تفاصيل المباراة.
5. **SEO Schema Microdata Validation:** كود JSON-LD المدمج في المقال يجب أن يكون صالحاً بنسبة 100% وفق اختبارات Google Rich Results.

---

### Task 1: مشغل النفق والسيرفر المحمول الخالي من قيود المسؤول (`run_kora_free.bat`)

**Files:**
- Create: `scripts/extract_tunnel_url.py`
- Create: `run_kora_free.bat`
- Test: `tests/live_score/test_tunnel_helper.py`

**Interfaces:**
- Consumes: `.tools\cloudflared.exe`, `run.py` (FastAPI Server on port 8000).
- Produces: `data/tunnel_url.txt` containing the active `https://*.trycloudflare.com` URL, copied to Windows clipboard via `clip`.

- [ ] **Step 1: كتابة الاختبار الفاشل لمحلل سجلات النفق `test_tunnel_helper.py`**

```python
import pytest
from scripts.extract_tunnel_url import parse_trycloudflare_url

def test_parse_trycloudflare_url_success():
    log_content = """
    2026-11-24T02:00:00Z INF +--------------------------------------------------------------------------------------------+
    2026-11-24T02:00:00Z INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
    2026-11-24T02:00:00Z INF |  https://crisp-banana-xyz.trycloudflare.com                                                |
    2026-11-24T02:00:00Z INF +--------------------------------------------------------------------------------------------+
    """
    url = parse_trycloudflare_url(log_content)
    assert url == "https://crisp-banana-xyz.trycloudflare.com"

def test_parse_trycloudflare_url_none():
    assert parse_trycloudflare_url("some random startup logs with no url") is None
```

- [ ] **Step 2: تشغيل الاختبار للتحقق من فشله**

Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_tunnel_helper.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.extract_tunnel_url'`

- [ ] **Step 3: تنفيذ دالة استخراج الرابط في `scripts/extract_tunnel_url.py`**

كتابة `parse_trycloudflare_url(text: str) -> str | None` باستخدام التعبير النمطي `https://[a-zA-Z0-9-]+\.trycloudflare\.com`، ودعم القراءة المباشرة من ملف السجل وحفظ الرابط في `data/tunnel_url.txt` ونسخه إلى الحافظة عند الاستدعاء كـ CLI.

- [ ] **Step 4: تشغيل الاختبار للتحقق من نجاحه**

Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_tunnel_helper.py -v`  
Expected: PASS

- [ ] **Step 5: إنشاء مشغل الباتش المحمول `run_kora_free.bat`**

إنشاء ملف Bat غير متطلب لأي صلاحيات مسؤول يقوم بـ:
1. تشغيل بايثون للسيرفر الموحد على المنفذ `8000` في نافذة خلفية.
2. تشغيل `.tools\cloudflared.exe tunnel --url http://127.0.0.1:8000` وتوجيه المخرجات لملف `.tools\tunnel.log`.
3. استدعاء `scripts/extract_tunnel_url.py` لانتظار ظهور الرابط ونسخه للحافظة وطباعة رسالة ترحيبية عربية واضحة للمستخدم.

---

### Task 2: محرك توليد المقالات الرياضية المتوافقة مع Google SEO (`article_generator.py`)

**Files:**
- Create: `src/live_score/domain/article_generator.py`
- Modify: `src/live_score/api/admin_routes.py`
- Test: `tests/live_score/test_article_generator.py`

**Interfaces:**
- Consumes: Match dictionary from `catalog.get_match_summary(match_id)` or `catalog.get_today_schedule()`.
- Produces: `generate_blogger_article(match: dict, platform_base_url: str = "") -> str` returning ready-to-paste Arabic Blogger HTML with Schema.org JSON-LD and CTA button.
- Endpoint: `GET /api/v1/admin/matches/{match_id}/article?base_url=...` returning `{"article_html": "...", "title": "..."}`.

- [ ] **Step 1: كتابة الاختبار الفاشل لمولد المقالات `test_article_generator.py`**

```python
import pytest
from src.live_score.domain.article_generator import generate_blogger_article

def test_generate_blogger_article_structure():
    mock_match = {
        "id": "match_clasico",
        "home_team": "ريال مدريد",
        "away_team": "برشلونة",
        "competition": "الدوري الإسباني",
        "kickoff_time": "2026-11-24T20:00:00Z",
        "status": "SCHEDULED",
        "venue": "سانتياغو برنابيو",
        "referee": "خيسوس خيل مانزانو",
        "channel": "beIN Sports 1 HD",
        "commentator": "حفيظ دراجي"
    }
    result = generate_blogger_article(mock_match, platform_base_url="https://live.example.com")
    
    # التحقق من وجود العنوان الجذاب
    assert "مشاهدة مباراة ريال مدريد وبرشلونة" in result["title"]
    # التحقق من كود Schema.org المعتمد من Google
    assert 'application/ld+json' in result["content"]
    assert '"@type": "SportsEvent"' in result["content"]
    # التحقق من زر التوجيه الآمن
    assert 'rel="noopener noreferrer"' in result["content"]
    assert 'https://live.example.com' in result["content"]
```

- [ ] **Step 2: تشغيل الاختبار للتحقق من فشله**

Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_article_generator.py -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: تنفيذ `generate_blogger_article` في `src/live_score/domain/article_generator.py`**

بناء الدالة مع تضمين:
- توليد عنوان المقال المخصص لجلب الزيارات (`title`).
- قالب HTML عربي أنيق مع جدول تفاصيل المباراة وبطاقات التوقيت لكافة العواصم العربية (مكة المكرمة، القاهرة، الرباط، دبي).
- كود Schema.org مدمج (`SportsEvent`) لظهور النتيجة في نتائج Google البحثية الأولى.
- زر تفاعلي عريض ومتحرك يوجه للمنصة الحية برابط المباراة المباشر.

- [ ] **Step 4: إضافة الـ Endpoint في `src/live_score/api/admin_routes.py`**

إضافة مسار `GET /api/v1/admin/matches/{match_id}/article` المحمي بـ `X-Admin-Token`، الذي يقرأ تفاصيل المباراة ويولد المقال ويعيده كـ JSON.

- [ ] **Step 5: تشغيل الاختبارات للتأكد من نجاحها**

Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_article_generator.py tests/live_score/test_api.py -v`  
Expected: PASS

---

### Task 3: زر 1-Click "نسخ مقال التدوينة 📝" في لوحة التحكم (`AdminPanel.jsx`)

**Files:**
- Modify: `frontend/src/components/AdminPanel.jsx`
- Create/Test: `frontend/src/components/__tests__/AdminPanelArticle.test.jsx`

**Interfaces:**
- Consumes: `GET /api/v1/admin/matches/{match_id}/article` from backend.
- Produces: Instant copying of ready-to-paste article HTML to the administrator's clipboard with a visual success toast.

- [ ] **Step 1: كتابة الاختبار الفاشل لزر نسخ المقال في لوحة التحكم**

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AdminPanel from '../AdminPanel';

describe('AdminPanel Blogger Article Generator Button', () => {
  it('renders "نسخ المقال" button on match cards', async () => {
    render(<AdminPanel token="dev-admin-token" onBack={vi.fn()} />);
    await waitFor(() => {
      const copyButtons = screen.getAllByRole('button', { name: /نسخ المقال/i });
      expect(copyButtons.length).toBeGreaterThan(0);
    });
  });
});
```

- [ ] **Step 2: تشغيل الاختبار للتأكد من فشله**

Run: `cd frontend && npm test -- src/components/__tests__/AdminPanelArticle.test.jsx`  
Expected: FAIL

- [ ] **Step 3: تعديل `AdminPanel.jsx` لإضافة زر نسخ المقال والـ Toast**

إضافة زر `نسخ المقال 📝` في كل بطاقة مباراة داخل تبويب "المباريات والبث المباشر"، عند الضغط عليه يستدعي الـ API، وينسخ كود المقال ومحتواه إلى الحافظة (`navigator.clipboard.writeText`) ويعرض تنبيهاً أخضر أنيقاً: "تم نسخ مقال المباراة لـ Blogger بنجاح!".

- [ ] **Step 4: تشغيل الاختبار والتحقق من النجاح**

Run: `cd frontend && npm test -- src/components/__tests__/AdminPanelArticle.test.jsx`  
Expected: PASS

- [ ] **Step 5: إعادة بناء الواجهة الإنتاجية**

Run: `cd frontend && npm run build`  
Expected: تحديث مجلد `frontend/dist` ليصبح جاهزاً للخدمة الموحدة على المنفذ `8000`.

---

### Task 4: حزمة إطلاق Blogger وتفعيل إعلانات Adsterra المتكاملة (Publishing & Monetization Kit)

**Files:**
- Create: `docs/blogger_launch_kit.md`
- Create: `docs/templates/article_template.html`

**Interfaces:**
- Consumes: Documented strategy from `docs/superpowers/specs/2026-11-24-blogger-hybrid-seo-monetization-design.md`.
- Produces: Complete, step-by-step Arabic documentation guiding the user through:
  1. إنشاء مدونة Blogger مجانية في دقيقتين.
  2. توثيق مدونة Blogger في شبكة Adsterra وتركيب كود **Social Bar** و **Popunder**.
  3. كيفية استخدام مشغل `run_kora_free.bat` والحصول على الرابط.
  4. نشر أول مقال مباراة بنقرة زر واحدة عبر لوحة التحكم.
  5. دمج روابط Adsterra Direct Link وبانرات 1xBet داخل لوحة تحكم المنصة.

- [ ] **Step 1: إنشاء ملف القالب المصدري المستقل `docs/templates/article_template.html`**
- [ ] **Step 2: كتابة دليل الإطلاق الشامل الموضح بالصور والخطوات في `docs/blogger_launch_kit.md`**
- [ ] **Step 3: التحقق النهائي لكافة اختبارات النظام (120+ Pytest و 40+ Vitest)**

Run: `.\.venv\Scripts\python.exe -m pytest -q`  
Expected: All tests pass.
