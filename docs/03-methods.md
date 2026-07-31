# ۳. روش‌های حل

## ۳.۱ A-Star

A-Star به کل نقشه دسترسی دارد. حالت جست‌وجو شامل:

```text
(position, remaining_health, has_gold)
```

دیوار و غول از فضای حالت حذف می‌شوند. چاه مجاز است، اما کاهش واقعی جان و جریمه چاه به هزینه اضافه می‌شود. تابع heuristic فاصله منهتن است:

```text
قبل از طلا: min(distance(agent,gold) + distance(gold,exit))
بعد از طلا: distance(agent,exit)
```

این روش baseline آگاه از نقشه و Oracle است.

## ۳.۲ عامل قاعده‌محور

عامل از Breeze، Stench و نتیجه حرکت‌ها یک پایگاه دانش می‌سازد:

- نبود Breeze، همسایه‌ها را از نظر چاه امن می‌کند.
- نبود Stench، همسایه‌ها را از نظر غول امن می‌کند.
- clause تک‌عضوی خطر قطعی را نتیجه می‌دهد.
- خانه واردشده دارای چاه به‌عنوان `DEFINITE_PIT` ثبت می‌شود.
- ابتدا خانه امن بازدیدنشده انتخاب می‌شود.
- سپس backtracking امن انجام می‌شود.
- اگر هیچ frontier امنی نبود، کم‌خطرترین frontier انتخاب می‌شود.

## ۳.۳ عامل ژنتیکی ترکیبی

این عامل یک روش ترکیبی است:

- پایگاه دانش محلی برای شواهد خطر؛
- سیاست خطی وزن‌دار برای انتخاب حرکت در مرحله اکتشاف؛
- بازگشت deterministic از کوتاه‌ترین مسیر شناخته‌شده امن پس از گرفتن طلا.

فرمول تصمیم:

```text
score(action) = sum(weight_i * feature_i(action))
```

ژن‌ها:

1. `safe_bonus`
2. `unvisited_bonus`
3. `exit_progress_weight`
4. `pit_risk_penalty`
5. `wumpus_risk_penalty`
6. `unknown_weight`
7. `revisit_penalty`
8. `reverse_penalty`
9. `frontier_bonus`
10. `health_caution_penalty`

## ۳.۴ الگوریتم ژنتیک

- جمعیت: 24
- نسل: 24
- Elitism: 2
- Tournament size: 3
- Mutation rate: 0.10
- Mutation sigma: 2.0
- Crossover: arithmetic/intermediate crossover
- Early stopping patience: 8
- Seed: 17
- نقشه آموزش: 12
- بهترین Fitness: 1840.67

