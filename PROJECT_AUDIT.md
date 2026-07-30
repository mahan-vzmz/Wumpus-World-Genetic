# Final Project Audit - Version 8

## Validation status

- Automated tests: **44 passed**
- Python compile check: **passed**
- Map parser validation: **all sample, training, and test maps passed**
- Training maps: **12**
- Test maps: **30**
- Final benchmark rows: **90**
- Benchmark error rows: **0**
- Main sample: **all 3 final agents succeeded**
- Report PDF: **generated and preflighted**
- Presentation PPTX/PDF: **generated and preflighted**

## Corrected issues

1. Correct `max_steps` termination.
2. Strict input validation.
3. Correct memory for survived pit entry.
4. One A-Star planning pass per episode.
5. Explicit error for missing genetic weights.
6. Varied exits, gold locations, and A-Star path lengths.
7. Equal initial health across difficulties.
8. Successful-only path-length metric.
9. Repeated median runtime.
10. Honest hybrid genetic method description.
11. Synced README, report, slides, CSV, and code.
12. Relative-path artifact generation.
13. GitHub Actions and MIT License.

## Final experiment

| Agent | Success rate | Average score | Successful steps |
|---|---:|---:|---:|
| A-Star | 100.00% | 157.60 | 12.40 |
| Rule-Based | 90.00% | 117.93 | 32.30 |
| Hybrid Genetic | 83.33% | 120.97 | 24.60 |

The only fields not inferable from the repository are personal submission metadata such as student ID, instructor, and university. They are isolated in `project_info.json` and do not affect code, tests, results, or artifacts.
