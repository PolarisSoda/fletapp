"""Standalone real-data benchmark: flet build windows --module-name table_benchmark."""
import asyncio
import time
import flet as ft
from flet_virtual_table import FletVirtualTable

async def main(page: ft.Page):
    page.title = "Virtual table — 500,000 rows × 10 columns"
    status = ft.Text("Generating 5,000,000 values…")
    page.add(status)
    started = time.perf_counter()
    rows = []
    for start in range(0, 500_000, 2000):
        rows.extend(tuple(i * 10 + j for j in range(10)) for i in range(start, start + 2000))
        await asyncio.sleep(0)
    elapsed = time.perf_counter() - started
    table = FletVirtualTable(columns=[f"Column {j + 1}" for j in range(10)], row_count=len(rows), expand=True)
    requests = 0
    async def fetch(e):
        nonlocal requests
        requests += 1
        table.supply(e.request_id, e.start, [list(row) for row in rows[e.start:e.start + min(e.count, 512)]])
        status.value = f"500,000 × 10 | generation {elapsed:.3f}s | request {requests} | rows {e.start:,}–{e.start + e.count:,}"
        status.update()
    table.on_range_request = fetch
    page.add(table)

if __name__ == "__main__":
    ft.run(main)
