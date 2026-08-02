from __future__ import annotations

import argparse
import csv
import html
import json
import shutil
import subprocess
from importlib.metadata import version
from pathlib import Path
from typing import Any

PROJECT_VERSION = version("wumpus-world-genetic")

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"
REPORT_DIR = DOCS / "final_report"
RESULTS = ROOT / "results" / "final"

VALID_MODES = {"public", "academic"}

REQUIRED_PUBLIC = {
    "project_title",
    "author_name",
    "course_name",
}

REQUIRED_ACADEMIC = {
    "student_name",
    "student_id",
    "course_name",
    "instructor_name",
    "university_name",
    "submission_date",
}

PLACEHOLDER_VALUES = {
    "Your Name",
    "Your Student ID",
    "Instructor Name",
    "University Name",
    "YYYY-MM-DD",
    "Project Title",
}


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
            except OSError as exc:
                raise RuntimeError(f"Unable to update report asset {dest}: {exc}") from exc


def load_run_metadata() -> dict[str, Any]:
    meta_path = RESULTS / "run_metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError("Missing results/final/run_metadata.json. Run experiment.py first.")

    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid run metadata format in {meta_path}: {exc}") from exc

    required_keys = [
        "project_version",
        "source_commit",
        "training_seed",
        "training_map_seed",
        "test_seed",
        "training_maps",
        "test_maps",
        "maps_per_difficulty",
        "population",
        "requested_generations",
        "generations_run",
        "mutation_rate",
        "mutation_sigma",
        "elite_count",
        "tournament_size",
        "max_steps",
        "timing_repeats",
        "weights_sha256",
        "best_fitness",
    ]
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"run_metadata.json missing required keys: {missing}")

    if not isinstance(data["source_commit"], str) or not data["source_commit"].strip():
        raise ValueError("source_commit in run_metadata.json must be a non-empty string")
    if data["training_maps"] <= 0 or data["test_maps"] <= 0 or data["population"] <= 0:
        raise ValueError("Map counts and population size in run_metadata.json must be positive integers")
    if data["requested_generations"] <= 0 or data["generations_run"] <= 0:
        raise ValueError("Generation counts in run_metadata.json must be positive integers")

    return data


def load_project_info(path: Path | str | None = None) -> dict[str, str]:
    if path is not None:
        info_path = Path(path)
    elif (ROOT / "project_info.public.json").exists():
        info_path = ROOT / "project_info.public.json"
    elif (ROOT / "project_info.json").exists():
        info_path = ROOT / "project_info.json"
    else:
        raise FileNotFoundError(
            "Missing project_info.public.json and project_info.json. "
            "Create project_info.public.json or project_info.json."
        )

    if not info_path.exists():
        raise FileNotFoundError(f"Specified info file does not exist: {info_path}")

    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid JSON in {info_path}: {exc}") from exc

    mode = info.get("report_mode", "academic").lower()
    if mode not in VALID_MODES:
        raise ValueError(f"report_mode in {info_path.name} must be one of {sorted(VALID_MODES)}; got '{mode}'")

    required = REQUIRED_PUBLIC if mode == "public" else REQUIRED_ACADEMIC
    missing = [field for field in required if not info.get(field)]
    if missing:
        raise ValueError(f"Missing required fields for '{mode}' mode in {info_path.name}: {', '.join(sorted(missing))}")

    invalid = {key: value for key, value in info.items() if value in PLACEHOLDER_VALUES}
    if invalid:
        fields = ", ".join(sorted(invalid))
        raise ValueError(f"Complete placeholder fields in {info_path.name}: {fields}")

    return info


def build_report(info: dict[str, str], summary: list[dict[str, str]]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    run_meta = load_run_metadata()

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

    mode = info.get("report_mode", "academic").lower()
    if mode == "public":
        author = info.get("author_name") or info.get("student_name", "Public Repository")
        title = info.get("project_title", "Wumpus World Genetic Agents")
        institution = info.get("institution_name", "GitHub Public Edition")
        meta_html = (
            f"<p><b>نسخه عمومی GitHub</b></p>"
            f"<p><b>پروژه:</b> {html.escape(title)}</p>"
            f"<p><b>نویسنده:</b> {html.escape(author)}</p>"
            f"<p><b>درس/محیط:</b> {html.escape(info.get('course_name', 'Artificial Intelligence'))}</p>"
            f"<p><b>ناشر/منبع:</b> {html.escape(institution)}</p>"
            f"<p><b>نسخه نرم‌افزار:</b> {html.escape(PROJECT_VERSION)}</p>"
        )
    else:
        meta_html = (
            f"<p><b>نام دانشجو:</b> {html.escape(info.get('student_name', ''))}</p>"
            f"<p><b>درس:</b> {html.escape(info.get('course_name', ''))}</p>"
            f"<p><b>استاد:</b> {html.escape(info.get('instructor_name', ''))}</p>"
            f"<p><b>دانشگاه:</b> {html.escape(info.get('university_name', ''))}</p>"
        )

    summary_by_agent = {row["agent"]: row for row in summary}
    astar_rate = summary_by_agent.get("astar", {}).get("success_rate", "0")
    rule_rate = summary_by_agent.get("rule", {}).get("success_rate", "0")
    genetic_rate = summary_by_agent.get("genetic", {}).get("success_rate", "0")

    rule_steps_succ = float(summary_by_agent.get("rule", {}).get("average_steps_success", "0"))
    genetic_steps_succ = float(summary_by_agent.get("genetic", {}).get("average_steps_success", "0"))

    initial_health = 120

    best_fit = f"{float(run_meta['best_fitness']):.2f}"
    training_maps = run_meta["training_maps"]
    pop_size = run_meta["population"]
    req_gens = run_meta["requested_generations"]
    run_gens = run_meta["generations_run"]
    mut_rate = run_meta["mutation_rate"]
    mut_sigma = run_meta["mutation_sigma"]
    elitism = run_meta["elite_count"]
    tournament_size = run_meta["tournament_size"]
    seed_val = run_meta["training_seed"]
    test_maps = run_meta["test_maps"]
    per_diff = run_meta.get("maps_per_difficulty", 10)
    timing_repeats = run_meta.get("timing_repeats", 3)

    if float(rule_rate) >= float(genetic_rate):
        rel_text = f"در میان عامل‌های آنلاین، Rule-Based با نرخ موفقیت {rule_rate}٪ نسبت به Hybrid Genetic ({genetic_rate}٪) عملکرد مطمئن‌تری ثبت کرد."
    else:
        rel_text = f"در میان عامل‌های آنلاین، Hybrid Genetic با نرخ موفقیت {genetic_rate}٪ نسبت به Rule-Based ({rule_rate}٪) عملکرد بهتری نشان داد."

    if genetic_steps_succ < rule_steps_succ:
        step_text = f"Hybrid Genetic در اپیزودهای موفق با میانگین {genetic_steps_succ:.1f} حرکت در مقایسه با Rule-Based ({rule_steps_succ:.1f} حرکت) مسیر کوتاه‌تری را طی کرد."
    else:
        step_text = f"Rule-Based در اپیزودهای موفق با میانگین {rule_steps_succ:.1f} حرکت در مقایسه با Hybrid Genetic ({genetic_steps_succ:.1f} حرکت) مسیر کوتاه‌تری را ثبت کرد."

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
{meta_html}
</div>
</section>

<h2>چکیده</h2>
<p>در این پروژه محیط Wumpus World روی گرید 8×8 پیاده‌سازی شد و سه روش متفاوت روی یک محیط و مجموعه معیار مشترک مقایسه شدند. A-Star به کل نقشه دسترسی دارد و نقش Oracle را ایفا می‌کند. عامل قاعده‌محور و عامل ژنتیکی ترکیبی فقط از ادراک‌های محلی، حافظه و مختصات عمومی خروج استفاده می‌کنند. وزن‌های روش ژنتیکی روی {training_maps} نقشه آموزش تکامل یافتند و ارزیابی نهایی روی {test_maps} نقشه تست جداگانه انجام شد.</p>
<div class="callout">نتیجه اصلی: A-Star به {astar_rate}٪، Rule-Based به {rule_rate}٪ و Hybrid Genetic به {genetic_rate}٪ موفقیت رسید. {rel_text} {step_text}</div>

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
<ul><li>{training_maps} نقشه آموزش جدا</li><li>Population = {pop_size}</li><li>Maximum generations = {req_gens}</li><li>Generations executed = {run_gens}</li><li>Elitism = {elitism}</li><li>Tournament size = {tournament_size}</li><li>Mutation rate = {mut_rate}</li><li>Mutation sigma = {mut_sigma}</li><li>Seed = {seed_val}</li><li>Best fitness = {best_fit}</li></ul>
<figure><img src="../assets/genetic_fitness.png"><figcaption>روند بهترین و میانگین Fitness در طول آموزش</figcaption></figure>

<h2>۷. طراحی آزمایش</h2>
<p>{test_maps} نقشه تست دیده‌نشده شامل {per_diff} نقشه آسان، {per_diff} متوسط و {per_diff} سخت با seed ثابت تولید شدند. خروج، محل طلا و طول مسیرها متنوع است. جان اولیه همه سطوح برابر {initial_health} است تا امتیاز بین دشواری‌ها قابل مقایسه باشد. زمان اجرا median {timing_repeats} اجرای کامل است و تعداد حرکت موفق جداگانه گزارش می‌شود.</p>

<h2>۸. نتایج کلی</h2>
<table><thead><tr><th>Agent</th><th>Success</th><th>Score all</th><th>Steps all</th><th>Steps success</th><th>Health</th><th>Pit entries</th><th>Wumpus deaths</th></tr></thead><tbody>{rows}</tbody></table>
<figure><img src="../assets/success_rate.png"><figcaption>نرخ موفقیت سه روش</figcaption></figure>
<figure><img src="../assets/average_steps_success.png"><figcaption>میانگین حرکت فقط در اپیزودهای موفق</figcaption></figure>

<h2>۹. تحلیل مقایسه‌ای</h2>
<p>A-Star به دلیل اطلاعات کامل و وجود حداقل یک مسیر امن، کران بالای عملکرد است. {rel_text} {step_text} بنابراین نتیجه علمی، برتری مطلق یک روش نیست؛ بلکه تفاوت در trade-off میان اطمینان، توضیح‌پذیری و سرعت موفقیت است.</p>
<figure><img src="../assets/success_by_difficulty.png"><figcaption>نرخ موفقیت بر اساس سطح دشواری</figcaption></figure>
<figure><img src="../assets/failure_reasons.png"><figcaption>دلایل شکست</figcaption></figure>

<h2>۱۰. محدودیت‌ها</h2>
<ul><li>A-Star سطح اطلاعات متفاوتی دارد.</li><li>نتایج برای seed و مجموعه تست ثبت‌شده معتبرند.</li><li>عامل ژنتیکی تضمین بهینگی یا موفقیت ندارد.</li><li>زمان اجرا به سخت‌افزار وابسته است.</li><li>برای استنباط آماری قوی‌تر، چند seed و confidence interval لازم است.</li></ul>

<h2>۱۱. نتیجه‌گیری</h2>
<p>نسخه {PROJECT_VERSION} یک pipeline قابل‌بازتولید از تولید نقشه و آموزش تا تست، ارزیابی و گزارش فراهم می‌کند. A-Star بهترین عملکرد را در محیط کاملاً شناخته‌شده دارد. {rel_text} {step_text}</p>

<h2>۱۲. منابع</h2>
<ol><li>Russell, S. J., & Norvig, P. Artificial Intelligence: A Modern Approach.</li></ol>
</body></html>"""
    html_path = REPORT_DIR / "final_report.html"
    pdf_path = REPORT_DIR / "final_report.pdf"

    if (
        html_path.exists()
        and pdf_path.exists()
        and pdf_path.stat().st_size > 0
        and html_path.read_text(encoding="utf-8") == html_text
    ):
        return pdf_path

    html_path.write_text(html_text, encoding="utf-8")
    pdf_path.unlink(missing_ok=True)
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
        if browser_binary is None:
            errors.append("Browser fallback: no supported browser found")
        else:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Wumpus World final HTML/PDF report.")
    parser.add_argument("--info", default=None, help="Path to project info JSON file.")
    args = parser.parse_args()

    info = load_project_info(args.info)
    summary = read_csv(RESULTS / "summary_results.csv")
    copy_assets()
    report = build_report(info, summary)
    print(f"report={report.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
