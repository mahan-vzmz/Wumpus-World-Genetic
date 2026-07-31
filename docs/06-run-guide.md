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
