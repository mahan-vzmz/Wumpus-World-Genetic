# چک‌لیست نهایی تحویل نسخه 8

## پیش از ارسال

- [ ] مقادیر `[شماره دانشجویی]`، `[نام استاد]` و `[نام دانشگاه]` در `project_info.json` تکمیل شده‌اند.
- [ ] پس از تکمیل اطلاعات، `python docs/build_artifacts.py` دوباره اجرا شده است.
- [x] تست‌ها: `44 passed`
- [x] کامپایل همه فایل‌های Python بدون خطا
- [x] اجرای سه عامل روی `maps/sample_01.txt`
- [x] آموزش GA روی 12 نقشه جدا
- [x] آزمایش روی 30 نقشه تست جدا و 90 اپیزود
- [x] CSV، نمودارها، گزارش و اسلاید در پروژه موجودند
- [x] README و گزارش با نتایج نسخه 8 هماهنگ‌اند
- [x] مسیر مطلق محیط سازنده در فایل‌های پروژه وجود ندارد
- [x] فایل MIT License و GitHub Actions اضافه شده‌اند

## دستورات کنترل نهایی

```bash
pip install -r requirements.txt
pytest -q
python -m compileall -q .
python demo_all.py --map maps/sample_01.txt
python experiment.py --skip-generate
```

## فایل‌هایی که باید تحویل شوند

کل پوشه پروژه را تحویل بده. فایل‌های مهم برای استاد:

- `README.md`
- `docs/final_report/final_report.pdf`
- `docs/presentation/wumpus_world_presentation.pptx`
- `docs/presentation/wumpus_world_presentation.pdf`
- `results/final/summary_results.csv`
- `best_weights.json`
- `tests/`
