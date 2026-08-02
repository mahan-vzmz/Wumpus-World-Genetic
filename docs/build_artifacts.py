from __future__ import annotations

import csv
import html
import json
import shutil
import subprocess
from importlib.metadata import version
from pathlib import Path

PROJECT_VERSION = version("wumpus-world-genetic")

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"
REPORT_DIR = DOCS / "final_report"
RESULTS = ROOT / "results" / "final"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def copy_assets() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    sources = [
        RESULTS / "success_rate.png",
        RESULTS / "average_score.png",
        RESULTS / "average_steps_success.png",
        RESULTS / "remaining_health.png",
        RESULTS / "runtime.png",
        RESULTS / "success_by_difficulty.png",
        RESULTS / "failure_reasons.png",
        ROOT / "results" / "genetic_fitness.png",
    ]
    for source in sources:
        if not source.exists():
            raise FileNotFoundError(f"Missing artifact source: {source}. Run train_genetic.py and experiment.py first.")
        dest = ASSETS / source.name
        data = source.read_bytes()
        if not dest.exists() or dest.read_bytes() != data:
            try:
                dest.write_bytes(data)
            except OSError:
                pass


def build_report(info: dict[str, str], summary: list[dict[str, str]]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = "".join(
        f"<tr><td>{html.escape(row['agent'])}</td>"
        f"<td>{row['success_rate']}%</td>"
        f"<td>{row['average_score_all']}</td>"
        f"<td>{row['average_steps_all']}</td>"
        f"<td>{row['average_steps_success']}</td>"
        f"<td>{row['average_remaining_health_all']}</td>"
        f"<td>{row['average_pit_entries']}</td>"
        f"<td>{row['wumpus_deaths']}</td></tr>"
        for row in summary
    )

    html_text = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<style>
@page {{ size: A4; margin: 18mm 16mm 18mm 16mm; background:#060810; @bottom-center {{ content: counter(page); font-size: 9pt; color:#5eead4; }} }}
html {{ background:#060810; }}
body {{ font-family: 'Noto Sans Arabic', 'DejaVu Sans', sans-serif; direction: rtl; color:#e7e9f5; line-height:1.75; font-size:10.5pt; background:#060810; -webkit-print-color-adjust:exact; print-color-adjust:exact; color-adjust:exact; }}
h1,h2,h3 {{ color:#5eead4; page-break-after: avoid; text-shadow:0 0 6px rgba(94,234,212,0.55), 0 0 14px rgba(94,234,212,0.25); }}
h1 {{ font-size:23pt; text-align:center; margin-top:45mm; color:#f472ff; text-shadow:0 0 8px rgba(244,114,255,0.6), 0 0 20px rgba(244,114,255,0.3); }}
h2 {{ font-size:16pt; border-bottom:1px solid #7c3aed; padding-bottom:3px; margin-top:18px; }}
h3 {{ font-size:12.5pt; }}
p {{ text-align:justify; }}
.cover {{ page-break-after: always; text-align:center; }}
.meta {{ margin:28mm auto 0; width:82%; border:1px solid #7c3aed; border-radius:8px; padding:18px; background:#0d1120; box-shadow:0 0 18px rgba(124,58,237,0.45); }}
.meta p {{ text-align:center; margin:8px; color:#e7e9f5; }}
table {{ width:100%; border-collapse:collapse; margin:12px 0; font-size:9pt; direction:ltr; }}
th,td {{ border:1px solid #3730a3; padding:6px; text-align:center; color:#e7e9f5; }}
th {{ background:#141a33; color:#5eead4; text-shadow:0 0 5px rgba(94,234,212,0.5); }}
figure {{ page-break-inside:avoid; margin:14px auto; text-align:center; }}
figure img {{ max-width:95%; max-height:95mm; border:1px solid #3730a3; box-shadow:0 0 14px rgba(59,130,246,0.35); }}
figcaption {{ font-size:9pt; color:#93a3c9; margin-top:4px; }}
.callout {{ background:#0d1120; border-right:4px solid #f472ff; padding:9px 12px; margin:12px 0; box-shadow:0 0 16px rgba(244,114,255,0.35); color:#e7e9f5; }}
.code {{ direction:ltr; text-align:left; font-family:monospace; background:#02040a; color:#5eead4; padding:8px; border:1px solid #3730a3; }}
ul {{ margin-right:20px; }}
.small {{ font-size:9pt; color:#8891b3; }}
</style>
</head>
<body>
<section class="cover">
<h1>گزارش نهایی پروژه Wumpus World</h1>
<h2 style="border:0;text-align:center"> مقایسه A-Star، عامل قاعده‌محور و عامل ژنتیکی ترکیبی</h2>
<div class="meta">
<p><b>نام دانشجو:</b> {html.escape(info["student_name"])}</p>
<p><b>درس:</b> {html.escape(info["course_name"])}</p>
<p><b>استاد:</b> {html.escape(info["instructor_name"])}</p>
<p><b>دانشگاه:</b> {html.escape(info["university_name"])}</p>
</div>
</section>

<h2>چکیده</h2>
<p>در این پروژه محیط Wumpus World روی گرید 8×8 پیاده‌سازی شد و سه روش متفاوت روی یک محیط و مجموعه معیار مشترک مقایسه شدند. A-Star به کل نقشه دسترسی دارد و نقش Oracle را ایفا می‌کند. عامل قاعده‌محور و عامل ژنتیکی ترکیبی فقط از ادراک‌های محلی، حافظه و مختصات عمومی خروج استفاده می‌کنند. وزن‌های روش ژنتیکی روی 12 نقشه آموزش تکامل یافتند و ارزیابی نهایی روی 30 نقشه تست جداگانه و 90 اپیزود انجام شد.</p>
<div class="callout">نتیجه اصلی: A-Star به 100٪، Rule-Based به 90٪ و Hybrid Genetic به 83.33٪ موفقیت رسید. در میان عامل‌های آنلاین، Rule-Based مطمئن‌تر و Hybrid Genetic در اپیزودهای موفق کوتاه‌مسیرتر بود.</div>

<h2>۱. تعریف مسئله و قوانین</h2>
<p>عامل از خانه (1,1) شروع می‌کند، باید حداقل یک طلا جمع‌آوری کند و پیش از تمام‌شدن جان به خروج برسد. هر تلاش برای حرکت یک واحد جان کم می‌کند. دیوار حرکت را مسدود می‌کند، چاه پس از هزینه حرکت جان را نصف می‌کند، غول مرگ فوری ایجاد می‌کند و خروج بدون طلا شکست است.</p>
<ul><li>Breeze: وجود چاه در همسایگی چهارجهته</li><li>Stench: وجود غول در همسایگی چهارجهته</li><li>Pit here: تشخیص چاه پس از زنده‌ماندن و ورود</li><li>حرکت‌های معتبر، جان، داشتن طلا و مختصات خروج</li></ul>

<h2>۲. معماری</h2>
<p>parser، محیط، عامل‌ها، پایگاه دانش، آموزش ژنتیک، مولد نقشه و benchmark در ماژول‌های مستقل قرار گرفته‌اند. تمام عامل‌ها از تابع اجرای مشترک استفاده می‌کنند. در نسخه {PROJECT_VERSION} ساختار پکیج با مسیرهای استاندارد، نصب‌پذیری، و دستورات یکپارچه CLI بهینه‌سازی شده است.</p>

<h2>۳. روش A-Star</h2>
<p>حالت جست‌وجو شامل موقعیت، جان باقی‌مانده و داشتن طلاست. دیوار و غول از فضای حالت حذف می‌شوند. ورود به چاه در صورت زنده‌ماندن مجاز است، اما کاهش واقعی جان و جریمه چاه در هزینه مسیر لحاظ می‌شود. heuristic فاصله منهتن یک lower bound معتبر است.</p>

<h2>۴. عامل قاعده‌محور</h2>
<p>این عامل از Breeze و Stench پایگاه دانش می‌سازد. نبود ادراک خطر، همسایه‌ها را از همان خطر مبرا می‌کند. clause تک‌عضوی محل خطر قطعی را مشخص می‌کند. عامل خانه امن بازدیدنشده را ترجیح می‌دهد، در بن‌بست backtracking می‌کند و در نبود گزینه امن، کم‌خطرترین frontier را انتخاب می‌کند.</p>

<h2>۵. عامل ژنتیکی ترکیبی</h2>
<p>روش سوم یک عامل ترکیبی است. پایگاه دانش محلی شواهد خطر را فراهم می‌کند؛ یک سیاست خطی با 10 وزن تکامل‌یافته، حرکت‌های مرحله اکتشاف را امتیازدهی می‌کند؛ و پس از گرفتن طلا، عامل از کوتاه‌ترین مسیر شناخته‌شده امن به خروج بازمی‌گردد.</p>
<p class="code">score(action) = Σ weight_i × feature_i(action)</p>

<h2>۶. آموزش الگوریتم ژنتیک</h2>
<ul><li>12 نقشه آموزش جدا</li><li>Population = 24</li><li>Maximum generations = 24</li><li>Elitism = 2</li><li>Tournament size = 3</li><li>Mutation rate = 0.10</li><li>Seed = 17</li><li>Best fitness = 1840.67</li></ul>
<figure><img src="../assets/genetic_fitness.png"><figcaption>روند بهترین و میانگین Fitness در طول آموزش</figcaption></figure>

<h2>۷. طراحی آزمایش</h2>
<p>30 نقشه تست دیده‌نشده شامل 10 نقشه آسان، 10 متوسط و 10 سخت با seed ثابت تولید شدند. خروج، محل طلا و طول مسیرها متنوع است. جان اولیه همه سطوح برابر 120 است تا امتیاز بین دشواری‌ها قابل مقایسه باشد. زمان اجرا median سه اجرای کامل است و تعداد حرکت موفق جداگانه گزارش می‌شود.</p>

<h2>۸. نتایج کلی</h2>
<table><thead><tr><th>Agent</th><th>Success</th><th>Score all</th><th>Steps all</th><th>Steps success</th><th>Health</th><th>Pit entries</th><th>Wumpus deaths</th></tr></thead><tbody>{rows}</tbody></table>
<figure><img src="../assets/success_rate.png"><figcaption>نرخ موفقیت سه روش</figcaption></figure>
<figure><img src="../assets/average_steps_success.png"><figcaption>میانگین حرکت فقط در اپیزودهای موفق</figcaption></figure>

<h2>۹. تحلیل مقایسه‌ای</h2>
<p>A-Star به دلیل اطلاعات کامل و وجود حداقل یک مسیر امن، کران بالای عملکرد است. Rule-Based در میان عامل‌های آنلاین نرخ موفقیت بالاتری دارد و محافظه‌کارتر است. Hybrid Genetic در اپیزودهای موفق حرکت کمتری مصرف می‌کند و امتیاز موفقیت بالاتری دارد، اما ریسک مرگ با غول بیشتر است. بنابراین نتیجه علمی، برتری مطلق یک روش نیست؛ بلکه تفاوت در trade-off میان اطمینان، توضیح‌پذیری و سرعت موفقیت است.</p>
<figure><img src="../assets/success_by_difficulty.png"><figcaption>نرخ موفقیت بر اساس سطح دشواری</figcaption></figure>
<figure><img src="../assets/failure_reasons.png"><figcaption>دلایل شکست</figcaption></figure>

<h2>۱۰. محدودیت‌ها</h2>
<ul><li>A-Star سطح اطلاعات متفاوتی دارد.</li><li>نتایج برای seed و مجموعه تست ثبت‌شده معتبرند.</li><li>عامل ژنتیکی تضمین بهینگی یا موفقیت ندارد.</li><li>زمان اجرا به سخت‌افزار وابسته است.</li><li>برای استنباط آماری قوی‌تر، چند seed و confidence interval لازم است.</li></ul>

<h2>۱۱. نتیجه‌گیری</h2>
<p>نسخه {PROJECT_VERSION} یک pipeline قابل‌بازتولید از تولید نقشه و آموزش تا تست، ارزیابی و گزارش فراهم می‌کند. A-Star بهترین عملکرد را در محیط کاملاً شناخته‌شده دارد. در محیط ناشناخته، Rule-Based مطمئن‌تر و توضیح‌پذیرتر است، در حالی که Hybrid Genetic در موفقیت‌ها کوتاه‌مسیرتر اما ریسک‌پذیرتر عمل می‌کند.</p>

<h2>۱۲. منابع</h2>
<ol><li>Russell, S. J., & Norvig, P. Artificial Intelligence: A Modern Approach.</li></ol>
</body></html>"""
    html_path = REPORT_DIR / "final_report.html"
    pdf_path = REPORT_DIR / "final_report.pdf"
    html_path.write_text(html_text, encoding="utf-8")
    errors: list[str] = []

    try:
        import contextlib
        import io

        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            from weasyprint import HTML

            HTML(filename=str(html_path), base_url=str(REPORT_DIR)).write_pdf(str(pdf_path))
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                return pdf_path
    except Exception as exc:
        errors.append(f"WeasyPrint: {exc}")

    try:
        browser_paths = [
            shutil.which("msedge"),
            shutil.which("chrome"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        ]
        browser_binary = next((p for p in browser_paths if p and Path(p).exists()), None)
        if browser_binary:
            cmd = [
                str(browser_binary),
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path.resolve()}",
                str(html_path.resolve()),
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                return pdf_path
    except Exception as exc:
        errors.append(f"Browser fallback: {exc}")

    raise RuntimeError("Unable to generate PDF.\n" + "\n".join(errors))


def load_project_info(path: Path | None = None) -> dict[str, str]:
    info_path = path or ROOT / "project_info.json"

    if not info_path.exists():
        raise FileNotFoundError(
            "Missing project_info.json. Copy project_info.example.json "
            "to project_info.json and complete the required fields."
        )

    info = json.loads(info_path.read_text(encoding="utf-8"))

    PLACEHOLDER_VALUES = {
        "Your Name",
        "Your Student ID",
        "Instructor Name",
        "University Name",
        "YYYY-MM-DD",
    }

    invalid = {key: value for key, value in info.items() if value in PLACEHOLDER_VALUES}

    if invalid:
        fields = ", ".join(sorted(invalid))
        raise ValueError(f"Complete placeholder fields in project_info.json: {fields}")

    return info


def main() -> None:
    info = load_project_info()
    summary = read_csv(RESULTS / "summary_results.csv")
    copy_assets()
    report = build_report(info, summary)
    print(f"report={report.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
