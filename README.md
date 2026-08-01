# Wumpus World - Version 8

پروژه نهایی درس هوش مصنوعی برای مقایسه سه روش حل Wumpus World روی گرید 8×8:

1. **A-Star آگاه از کل نقشه** به‌عنوان Oracle یا کران بالای عملکرد؛
2. **عامل قاعده‌محور آنلاین** مبتنی بر Breeze، Stench، پایگاه دانش و backtracking؛
3. **عامل ژنتیکی ترکیبی آنلاین** که اکتشاف را با وزن‌های تکامل‌یافته انجام می‌دهد و از پایگاه دانش و بازگشت امن استفاده می‌کند.

## وضعیت نهایی

- نسخه پروژه: `8.0.0`
- تست‌های خودکار: `44 passed`
- نقشه‌های آموزش ژنتیک: 12 نقشه جدا
- نقشه‌های آزمایش نهایی: 30 نقشه دیده‌نشده
- تعداد اپیزودهای مقایسه: 90
- seed آموزش: `17`
- seed آزمایش: `20260730`

### نتیجه آزمایش نهایی

| روش | موفقیت | امتیاز متوسط همه اجراها | حرکت متوسط همه اجراها | حرکت متوسط اجراهای موفق |
|---|---:|---:|---:|---:|
| A-Star | 100.00% | 157.60 | 12.40 | 12.40 |
| Rule-Based | 90.00% | 117.93 | 32.90 | 32.30 |
| Hybrid Genetic | 83.33% | 120.97 | 31.80 | 24.60 |

نکته علمی: A-Star کل نقشه را می‌بیند و مقایسه مستقیم آن با دو عامل آنلاین منصفانه نیست. مقایسه اصلی بین Rule-Based و Hybrid Genetic است. عامل قاعده‌محور نرخ موفقیت بیشتری داشته، ولی عامل ژنتیکی در اپیزودهای موفق مسیر کوتاه‌تر و امتیاز موفقیت بالاتری ثبت کرده است.

## نصب

```bash
python -m venv .venv
```

ویندوز:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## بررسی سلامت پروژه

```bash
pytest -q
python -m compileall -q .
```

خروجی مورد انتظار تست‌ها:

```text
44 passed
```

## اجرای سریع هر سه روش

```bash
python demo_all.py --map maps/sample_01.txt
```

خروجی فعلی نمونه:

```text
astar,True,156,14,106,0,escaped_with_gold
rule,True,140,30,90,0,escaped_with_gold
genetic,True,144,26,94,0,escaped_with_gold
```

## اجرای جداگانه

```bash
python main.py --agent astar --map maps/sample_astar_pit.txt
python main.py --agent rule --map maps/sample_rule_reasoning.txt --max-steps 250
python main.py --agent genetic --map maps/sample_01.txt --max-steps 250
```

فایل وزن ژنتیکی اجباری است. استفاده از وزن‌های دستی فقط با گزینه صریح زیر انجام می‌شود:

```bash
python main.py --agent genetic --map maps/sample_01.txt --use-default-weights
```

## آموزش دوباره عامل ژنتیکی

```bash
python train_genetic.py --regenerate-training-maps
```

تنظیمات نسخه تحویلی:

```text
population=24
generations=24
patience=8
max_steps=250
seed=17
training_maps=12
best_fitness=1840.67
```

## اجرای آزمایش نهایی

```bash
python experiment.py
```

این دستور 30 نقشه تست را با seed ثابت تولید می‌کند، هر سه عامل را اجرا می‌کند و نتایج را در `results/final/` می‌سازد. برای استفاده از نقشه‌های فعلی:

```bash
python experiment.py --skip-generate
```

## تولید گزارش PDF و اسلاید

```bash
pip install -r requirements-docs.txt
python docs/build_artifacts.py
```

اسکریپت فقط از مسیرهای نسبی پروژه استفاده می‌کند و به محیط سازنده وابستگی ندارد.

## فایل‌های تحویل

- `docs/final_report/final_report.pdf`
- `results/final/summary_results.csv`
- `results/final/difficulty_results.csv`
- `results/final/experiment_results.csv`
- `best_weights.json`

## ساختار اصلی

```text
astar_agent.py             A-Star با اطلاعات کامل
environment.py             قوانین و وضعیت محیط
knowledge_base.py          استنتاج محلی عامل‌های آنلاین
rule_based_agent.py        عامل قاعده‌محور
genetic_agent.py           سیاست وزن‌دار ترکیبی
genetic_algorithm.py       آموزش GA و Fitness
map_generator.py           تولید نقشه‌های آموزش و تست
experiment.py              benchmark و نمودارها
tests/                     44 تست خودکار
docs/                      مستندات، گزارش و ارائه
```

## محدودیت‌های گزارش‌شده

- A-Star یک Oracle است و سطح اطلاعات متفاوتی دارد.
- عامل ژنتیکی یک روش ترکیبی است، نه یک سیاست کاملاً مستقل از قواعد.
- تضمین موفقیت برای عامل‌های آنلاین وجود ندارد.
- نتایج فقط برای seed و مجموعه تست ثبت‌شده ادعا می‌شوند.
- زمان اجرا از median چند اجرای کامل به دست می‌آید و به سخت‌افزار وابسته است.

## مجوز

MIT License
