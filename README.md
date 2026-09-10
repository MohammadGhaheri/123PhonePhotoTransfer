# PhonePhotoTransfer

ابزار سبک ویندوز برای **انتقال مطمئن تعداد زیاد عکس و ویدئو از گوشی Android به کامپیوتر از طریق ADB**، بدون وابستگی به Windows Explorer و MTP.

**نسخه فعلی:** `v0.2.2`  
**سازنده:** Mohammad Ghaheri (محمد قاهری)  
**مجوز:** MIT

> هدف اصلی پروژه حل یک مشکل ساده اما آزاردهنده است: وقتی پوشه‌هایی مثل `DCIM/Camera` هزاران فایل دارند، Windows Explorer ممکن است برای فهرست‌کردن فایل‌ها بسیار کند شود، هنگ کند یا ارتباط MTP با گوشی قطع شود. PhonePhotoTransfer به‌جای MTP مستقیماً از ADB استفاده می‌کند و فایل‌ها را کنترل‌شده، قابل Resume و قابل Verify منتقل می‌کند.

## قابلیت‌ها

- تشخیص خودکار `adb.exe` از PATH، متغیرهای Android SDK، مسیرهای رایج Android Studio و مسیر ذخیره‌شده قبلی
- شناسایی خودکار گوشی‌های متصل با ADB
- انتخاب پوشه مبدأ روی گوشی و پوشه مقصد در ویندوز
- پشتیبانی از هزاران فایل بدون نیاز به بازکردن پوشه گوشی در Explorer
- فیلتر پسوندهای عکس و ویدئو
- حالت **Copy** برای کپی امن بدون حذف فایل از گوشی
- حالت **Move after Verify** برای حذف فایل از گوشی فقط پس از انتقال موفق و تطبیق اندازه
- Resume با SQLite در صورت قطع کابل، بسته‌شدن برنامه یا توقف انتقال
- Skip خودکار فایل‌هایی که قبلاً کامل منتقل شده‌اند
- انتقال اولیه به فایل موقت با پسوند `.part`
- Retry برای خطاهای معمول ADB
- توقف تمیز در صورت Offline یا Disconnect شدن گوشی
- Progress bar، فایل جاری، آمار انتقال و Log
- رابط گرافیکی با `tkinter` و بدون وابستگی Runtime به PyPI
- اسکریپت ساخت نسخه Windows EXE با PyInstaller

## چرا ADB و نه MTP؟

در ویندوز، دسترسی معمول به فایل‌های Android از طریق MTP انجام می‌شود. برای پوشه‌های بسیار بزرگ، Explorer ممکن است قبل از اینکه بتوانید فایل‌ها را Copy/Cut کنید مدت زیادی درگیر Enumerate کردن محتوا شود. در این پروژه فایل‌ها با فرمان‌های ADB مستقیماً از Android خوانده و منتقل می‌شوند؛ بنابراین Explorer اصلاً در مسیر انتقال قرار ندارد.

## پیش‌نیازها

برای اجرای نسخه Python:

- Windows 10 یا Windows 11
- Python 3
- `tkinter` (در نصب استاندارد Python برای Windows معمولاً وجود دارد)
- Android Debug Bridge یا ADB
- فعال بودن **USB debugging** روی گوشی Android

برنامه تلاش می‌کند ADB موجود روی سیستم را خودش پیدا کند. اگر Android Studio یا Platform Tools از قبل نصب باشد، در بسیاری از سیستم‌ها نیازی به تنظیم PATH نیست.

## شروع سریع

### 1. دریافت پروژه

Repository را Clone کنید:

```powershell
git clone https://github.com/MohammadGhaheri/123PhonePhotoTransfer.git
cd 123PhonePhotoTransfer
```

یا Repository را به‌صورت ZIP دانلود و Extract کنید.

### 2. گوشی را آماده کنید

در Android گزینه **USB debugging** را فعال کنید، گوشی را با کابل USB وصل کنید و در صورت نمایش پیام RSA، گزینه **Allow** را روی گوشی بزنید.

### 3. تشخیص ADB و گوشی را تست کنید

در پوشه پروژه اجرا کنید:

```text
doctor.bat
```

خروجی موفق باید ADB و حداقل یک دستگاه با وضعیت `device` نشان دهد.

### 4. برنامه را اجرا کنید

```text
run.bat
```

برای دوربین گوشی‌های Samsung و بسیاری از دستگاه‌های Android مسیر معمول این است:

```text
/sdcard/DCIM/Camera
```

سپس پوشه مقصد روی کامپیوتر را انتخاب کنید.

## توصیه مهم برای اولین اجرا

برای اولین انتقال حتماً حالت **Copy** را انتخاب کنید. بعد از اینکه مطمئن شدید فایل‌ها در مقصد سالم هستند و Resume/Skip مطابق انتظار کار می‌کند، در صورت نیاز از حالت Move استفاده کنید.

## رفتار Resume

در پوشه مقصد فایلی با نام زیر ایجاد می‌شود:

```text
.phone_photo_transfer.sqlite3
```

این SQLite Database وضعیت انتقال‌ها را نگه می‌دارد. اگر کابل قطع شود یا برنامه را ببندید، دفعه بعد همان مبدأ و مقصد را انتخاب کنید و انتقال را دوباره شروع کنید. فایل‌هایی که قبلاً کامل و با اندازه صحیح منتقل شده‌اند Skip می‌شوند.

این Database در `.gitignore` قرار دارد و نباید داخل Repository Commit شود.

## حالت Copy

در این حالت فایل روی گوشی دست‌نخورده باقی می‌ماند. روند هر فایل به‌صورت خلاصه:

1. اندازه فایل روی گوشی خوانده می‌شود.
2. فایل با ADB به مسیر موقت `.part` منتقل می‌شود.
3. اندازه فایل مقصد با فایل روی گوشی مقایسه می‌شود.
4. در صورت تطبیق، فایل موقت به نام نهایی Rename می‌شود.
5. نتیجه در SQLite ثبت می‌شود.

## حالت Move after Verify

Move همان مراحل Copy را انجام می‌دهد، اما بعد از Verify موفق، فایل اصلی را از گوشی حذف می‌کند.

ترتیب عملیات عمداً این‌گونه است:

```text
Remote file
   ↓
ADB pull → local .part
   ↓
Size verification
   ↓
Atomic rename to final file
   ↓
Delete remote file (فقط در حالت Move)
   ↓
Record completion
```

**توجه:** Verify فعلی بر اساس اندازه فایل است و Hash رمزنگاری‌شده کامل محتوای فایل محاسبه نمی‌شود. برای آرشیوهای بسیار حساس، Copy محافظه‌کارانه‌تر است.

## اگر کابل قطع شود چه می‌شود؟

اگر ADB دستگاه را `offline` یا disconnected تشخیص دهد، انتقال متوقف می‌شود تا هزاران خطای پشت‌سرهم ایجاد نشود. پس از اتصال مجدد گوشی، برنامه را دوباره اجرا کنید. فایل‌های کامل قبلی Skip می‌شوند و انتقال ادامه پیدا می‌کند.

## پسوندهای پیش‌فرض

نسخه فعلی این فرمت‌ها را به‌صورت پیش‌فرض در نظر می‌گیرد:

```text
3gp, avi, gif, heic, heif, jpeg, jpg, mkv, mov, mp4, png, webm, webp
```

فهرست پسوندها از داخل UI قابل تغییر است.

## مسیرهای پیشنهادی Android

چند مسیر رایج که داخل برنامه هم به‌عنوان Preset قرار داده شده‌اند:

```text
/sdcard/DCIM/Camera
/sdcard/Pictures
/sdcard/Download
/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images
/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Video
```

وجود دقیق این مسیرها به نسخه Android و برنامه‌های نصب‌شده بستگی دارد.

## ساخت EXE ویندوز

برای اجرای روزمره نیازی به PyInstaller ندارید. اگر می‌خواهید نسخه مستقل Windows بسازید:

```text
build_exe.bat
```

این مرحله `PyInstaller` را از `requirements-build.txt` نصب می‌کند و خروجی را در مسیر زیر قرار می‌دهد:

```text
dist\PhonePhotoTransfer\PhonePhotoTransfer.exe
```

ADB همچنان می‌تواند از نصب موجود روی سیستم Auto-detect شود. همچنین می‌توان پوشه `platform-tools` را کنار برنامه قرار داد تا بسته قابل‌حمل‌تری داشته باشید.

## تست‌ها

برای اجرای تست‌های پروژه:

```powershell
python -m unittest discover -s tests -v
```

در `v0.2.2` تست‌های فعلی این موارد را پوشش می‌دهند:

- حفظ ساختار نسبی پوشه‌ها
- ثبت و بازیابی Resume در SQLite
- Copy و Skip در اجرای مجدد
- حذف فایل Remote در Move فقط پس از Verify موفق
- توقف تمیز در زمان Disconnect شدن دستگاه

## ساختار پروژه

```text
PhonePhotoTransfer/
├── app.py                   # نقطه شروع برنامه
├── app_config.py            # تنظیمات و Presetها
├── app_worker.py            # Worker انتقال در Thread جدا
├── ui_main.py               # پنجره اصلی
├── ui_adb_mixin.py          # کنترل‌های ADB و دستگاه
├── ui_transfer_mixin.py     # کنترل فرآیند انتقال
├── ui_settings_mixin.py     # ذخیره/بازیابی تنظیمات
├── adb_manager.py           # API اصلی ADB
├── adb_candidate_mixin.py   # مسیرهای احتمالی ADB
├── adb_search_mixin.py      # جست‌وجوی محدود و Auto-detect
├── adb_ops_mixin.py         # اجرای فرمان‌های ADB
├── adb_types.py             # Exceptionها و مدل Device
├── transfer_engine.py       # موتور انتقال، Verify، Retry و Resume
├── transfer_database.py     # SQLite ledger
├── doctor.py                # ابزار Diagnostic
├── doctor.bat               # اجرای Diagnostic در Windows
├── run.bat                  # اجرای برنامه
├── build_exe.bat            # ساخت EXE با PyInstaller
├── tests/
└── QUICK_START_FA.md
```

## نکات امنیتی و حریم خصوصی

PhonePhotoTransfer فایل‌های شما را به سرویس Cloud ارسال نمی‌کند. انتقال بین گوشی و کامپیوتر از طریق ADB انجام می‌شود. مسیر محلی ADB و دیتابیس Resume نیز با `.gitignore` از Commit شدن در Git جلوگیری می‌شوند.

برای حالت Move، قبل از استفاده گسترده از پروژه روی داده مهم، ابتدا چند فایل را با Copy آزمایش و نتیجه را بررسی کنید.

## وضعیت نسخه 0.2.2

این نسخه مشکل گیرکردن اسکن روی پوشه‌هایی با خروجی بسیار زیاد ADB را اصلاح می‌کند. خروجی Process به‌صورت همزمان مصرف می‌شود تا پرشدن Pipe باعث Deadlock نشود.

هسته انتقال نسخه فعلی با مجموعه تست‌های Unit پروژه بررسی شده و تست عملی اولیه نیز روی یک دستگاه Samsung Galaxy Note10+ انجام شده است.

## برنامه‌های پیشنهادی برای نسخه‌های بعدی

مواردی که می‌توان در ادامه اضافه کرد:

- نمایش سرعت لحظه‌ای `MB/s`
- حجم کل منتقل‌شده
- ETA یا زمان تقریبی باقی‌مانده
- Verify اختیاری با Hash
- انتخاب گرافیکی پوشه‌های گوشی
- Build و Release آماده Windows در GitHub Actions

## مشارکت و گزارش مشکل

اگر با دستگاه یا نسخه Android خاصی مشکل داشتید، Issue باز کنید و در صورت امکان این اطلاعات را بنویسید:

- نسخه Windows
- نسخه Python
- مدل گوشی و نسخه Android
- خروجی `doctor.bat`
- Log خطا بدون اطلاعات شخصی یا مسیرهای حساس

## سازنده

**Mohammad Ghaheri (محمد قاهری)**  
GitHub: `@MohammadGhaheri`

این پروژه در سال 2026 برای ساده‌کردن انتقال حجیم عکس و ویدئو از Android به Windows ساخته شد.

## License

این پروژه تحت مجوز [MIT](LICENSE) منتشر شده است.
