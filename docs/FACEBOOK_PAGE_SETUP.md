# 📘 دليل ربط صفحة الفيسبوك بالنشر التلقائي (Graph API Setup)

لتفعيل النشر التلقائي بضغطة واحدة من تطبيق **استوديو كورة لايف** (`publish_facebook_today.bat`) وكذلك تلقائياً كل يوم عبر **GitHub Actions**:

---

## 1️⃣ استخراج `FB_PAGE_ID`
1. افتح صفحتك على فيسبوك ➔ **About (حول)** ➔ **Page transparency (شفافية الصفحة)**.
2. انسخ رقم **`Page ID`** (مثال: `123456789012345`).

---

## 2️⃣ استخراج `FB_PAGE_ACCESS_TOKEN` (مجاناً بدون App Review)
1. ادخل إلى [Meta for Developers](https://developers.facebook.com/) ➔ **My Apps** ➔ **Create App**.
2. اختر **Other** ➔ **Business** ➔ سمّه `KoraLivePublisher`.
3. افتح [Graph API Explorer](https://developers.facebook.com/tools/explorer/):
   * من اليمين اختر التطبيق `KoraLivePublisher`.
   * من خانة **User or Page** اختر **Get User Access Token**.
   * فعّل الصلاحيات الثلاث:
     * `pages_show_list`
     * `pages_read_engagement`
     * `pages_manage_posts`
   * اضغط **Generate Access Token** ووافق لصفحتك فقط.
4. في شريط الاستعلام العلوي (GET) اكتب:
   ```text
   me/accounts
   ```
   واضغط **Submit**.
5. ستظهر بيانات صفحتك وبداخلها حقل **`access_token`** — انسخه! هذا هو **Page Access Token** الخاص بصفحتك.

---

## 3️⃣ التفعيل في الجهاز وفي GitHub Actions
1. **على جهازك (للتطبيق والزر الواحد):**
   افتح `publish_facebook_today.bat` ➔ الصق `FB Page ID` و`Page Access Token` في الأسفل ➔ اضغط **💾 حفظ للنشر الآلي**.
2. **في GitHub Actions (للتشغيل السحابي 24/7):**
   في مستودعك على GitHub: **Settings ➔ Secrets and variables ➔ Actions** أضف:
   * `FB_PAGE_ID`
   * `FB_PAGE_ACCESS_TOKEN`
