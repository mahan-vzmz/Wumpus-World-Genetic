# ۶. راهنمای نصب و اجرا

## پیش‌نیاز

- Python 3.10 یا جدیدتر

## نصب

```bash
python -m venv .venv
```

```bash
pip install -r requirements.txt
```

## تست

```bash
pytest -q
python -m compileall -q .
```

خروجی مورد انتظار:

```text
44 passed
```

## اجرا

```bash
python demo_all.py --map maps/sample_01.txt
python main.py --agent astar --map maps/sample_astar_pit.txt
python main.py --agent rule --map maps/sample_rule_reasoning.txt
python main.py --agent genetic --map maps/sample_01.txt
```

## آزمایش

```bash
python experiment.py
```

یا بدون تولید دوباره نقشه:

```bash
python experiment.py --skip-generate
```

## آموزش

```bash
python train_genetic.py --regenerate-training-maps
```

## ساخت گزارش و ارائه

ابتدا مقادیر `project_info.json` را کامل کن:

```bash
pip install -r requirements-docs.txt
python docs/build_artifacts.py
```

## خطاهای متداول

| خطا | راه‌حل |
|---|---|
| `ModuleNotFoundError` | دستور را از ریشه پروژه اجرا کن |
| نبود وزن | مطمئن شو `best_weights.json` موجود است |
| نقشه نامعتبر | فایل باید دقیقاً 8 سطر گرید و 4 خط تنظیمات داشته باشد |
| نتیجه متفاوت runtime | زمان به سیستم وابسته است؛ معیار اصلی نرخ موفقیت و score است |
| PDF قدیمی | پس از تغییر اطلاعات یا نتایج، `docs/build_artifacts.py` را اجرا کن |
