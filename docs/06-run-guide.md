# ۶. راهنمای نصب و اجرا

## پیش‌نیاز

- Python 3.10 یا جدیدتر

## نصب

```bash
python -m venv .venv
```

```bash
pip install -e ".[dev]"
```

## تست

```bash
ruff check .
ruff format --check .
pytest -q
```

خروجی مورد انتظار: تمامی تست‌ها پاس شوند.

## اجرا

```bash
wumpus-world-demo --map maps/sample_01.txt
wumpus-world --agent astar --map maps/sample_astar_pit.txt
wumpus-world --agent rule --map maps/sample_rule_reasoning.txt
wumpus-world --agent genetic --map maps/sample_01.txt
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

## ساخت گزارش PDF

ابتدا فایل `project_info.json` را بسازید:

Windows PowerShell:
```powershell
Copy-Item project_info.example.json project_info.json
```

Linux/macOS:
```bash
cp project_info.example.json project_info.json
```

سپس مقادیر داخل آن را کامل کرده و اجرا کنید:

```bash
pip install -e ".[docs]"
python docs/build_artifacts.py
```
