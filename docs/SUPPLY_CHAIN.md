# Supply-chain ledger

w1 pins every **direct** dependency to a version published >1 month before adoption
(workspace rule). On first install (2026-06-21), `uv` resolved 75 packages total; 21 were
**transitive** deps newer than 30 days. Jay reviewed and chose **accept as-is** — they are
transitive deps of trusted, well-established packages (mlx-whisper, faster-whisper, rumps).

This file is the audit record. Re-run the audit any time with:
`uv pip freeze --python .venv/bin/python` + the PyPI date check in `.dev/`.

## Flagged on 2026-06-21 (published <30 days before install)
| Package | Version | Published | Pulled by |
|---|---|---|---|
| coverage | 7.14.2 | 2026-06-20 | pytest-cov |
| pyobjc-core | 12.2.1 | 2026-06-19 | rumps (macOS bridge) |
| pyobjc-framework-applicationservices | 12.2.1 | 2026-06-19 | rumps |
| pyobjc-framework-cocoa | 12.2.1 | 2026-06-19 | rumps |
| pyobjc-framework-coretext | 12.2.1 | 2026-06-19 | rumps |
| pyobjc-framework-quartz | 12.2.1 | 2026-06-19 | rumps |
| scipy | 1.18.0 | 2026-06-19 | mlx-whisper |
| certifi | 2026.6.17 | 2026-06-17 | requests/httpx |
| torch | 2.12.1 | 2026-06-17 | (transitive; not used by MLX path) |
| fsspec | 2026.6.0 | 2026-06-16 | huggingface-hub |
| anyio | 4.14.0 | 2026-06-15 | httpx |
| onnxruntime | 1.27.0 | 2026-06-15 | faster-whisper |
| filelock | 3.29.4 | 2026-06-13 | huggingface-hub/torch |
| protobuf | 7.35.1 | 2026-06-11 | onnxruntime |
| hf-xet | 1.5.1 | 2026-06-08 | huggingface-hub |
| av | 17.1.0 | 2026-06-07 | faster-whisper |
| ctranslate2 | 4.8.0 | 2026-06-06 | faster-whisper |
| typer | 0.26.7 | 2026-06-03 | (CLI transitive) |
| idna | 3.18 | 2026-06-02 | requests |
| click | 8.4.1 | 2026-05-22 | typer/import-linter |
| more-itertools | 11.1.0 | 2026-05-22 | mlx-whisper |

**Mitigation available if needed:** dropping the `[faster]` extra removes ctranslate2, av,
onnxruntime, protobuf (MLX is the real backend on Apple Silicon); scipy is downgradable to
1.17.1; pyobjc is Apple's macOS bridge (high-trust, required for the menu-bar/widget).
