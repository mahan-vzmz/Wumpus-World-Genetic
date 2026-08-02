# ۲. معماری سیستم

## اجزای اصلی

| فایل | مسئولیت |
|---|---|
| `src/wumpus_world/map_parser.py` | خواندن و اعتبارسنجی سخت‌گیرانه فایل نقشه |
| `src/wumpus_world/environment.py` | قوانین بازی، امتیاز، پایان و ادراک‌ها |
| `src/wumpus_world/agents/base_agent.py` | رابط مشترک عامل‌ها |
| `src/wumpus_world/agents/astar_agent.py` | برنامه‌ریزی A-Star با اطلاعات کامل |
| `src/wumpus_world/knowledge_base.py` | حافظه و استنتاج محلی |
| `src/wumpus_world/agents/rule_based_agent.py` | تصمیم‌گیری قاعده‌محور و backtracking |
| `src/wumpus_world/agents/genetic_agent.py` | استخراج ویژگی و سیاست وزن‌دار ترکیبی |
| `src/wumpus_world/training/genetic_algorithm.py` | Fitness، انتخاب، crossover، mutation و elitism |
| `src/wumpus_world/map_generator.py` | تولید قطعی نقشه‌های آموزش و تست |
| `src/wumpus_world/runner.py` | اجرای یکپارچه اپیزود برای انواع عامل‌ها |
| `src/wumpus_world/cli.py` | رابط خط فرمان تک‌عامل (`wumpus-world`) |
| `src/wumpus_world/demo.py` | رابط خط فرمان مقایسه‌ای (`wumpus-world-demo`) |
| `experiment.py` | اجرای benchmark، خلاصه، CSV و نمودار |
| `docs/build_artifacts.py` | ساخت قابل‌بازتولید گزارش HTML و PDF |

## جریان اجرای یک اپیزود

1. نقشه توسط parser اعتبارسنجی می‌شود.
2. محیط و عامل ساخته می‌شوند.
3. `reset()` دقیقاً یک بار برنامه یا حافظه عامل را آماده می‌کند.
4. عامل فقط observation مجاز را دریافت می‌کند.
5. محیط اکشن را اجرا و state، reward، done و info را برمی‌گرداند.
6. پایان طبیعی، خطای عامل یا `max_steps` با علت مشخص ثبت می‌شود.
7. خروجی استاندارد برای benchmark تولید می‌شود.
