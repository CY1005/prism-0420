"""api.ws — WebSocket handlers 横切目录。

横切归属（design 02-modules/M17-ai-import/00-design.md §6 + R-X6 + 04-layer Q7）：
业务 owner = 各模块（如 M17 own import_progress.py），但位置在 api/ws/ 横切目录
（与 api/queue/ 同款；防业务模块目录爆炸）。
"""
