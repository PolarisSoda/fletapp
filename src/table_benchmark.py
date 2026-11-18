"""Standalone real-data benchmark: flet build windows --module-name table_benchmark."""
import asyncio
import time
import flet as ft
from flet_datagrid import DataGrid

async def main(page: ft.Page):
    page.title = "Flet DataGrid — 500,000 rows × 10 columns"
    status = ft.Text("Generating 5,000,000 values…")
    page.add(status)
    started = time.perf_counter()
    rows = []
    for start in range(0, 500_000, 2000):
        rows.extend(tuple((i * (2 * j + 1)) % 500_000 for j in range(10)) for i in range(start, start + 2000))
        await asyncio.sleep(0)
    elapsed = time.perf_counter() - started
    def report(e=None):
        status.value = f"500,000 × 10 | generation {elapsed:.3f}s | selected {table.selected_count:,} | sort column {table.sort_column_index} {'ASC' if table.sort_ascending else 'DESC'} | sort {table.last_sort_ms:.1f}ms"
        status.update()
    table = DataGrid(columns=[ft.DataColumn(f"Column {j + 1}", numeric=True) for j in range(10)],
                     records=rows, expand=True, on_selection_change=report, on_sort=report)
    page.add(table)
    report()

    # This second grid exercises the ordinary DataTable API and real Flet widgets.
    sample_status = ft.Text("Native DataColumn / DataRow / DataCell sample")
    def tapped(e):
        sample_status.value = "Cell callback received"
        sample_status.update()
    sample = DataGrid(columns=[ft.DataColumn(ft.Text("Name")), ft.DataColumn("Score", numeric=True)],
        rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(name), on_tap=tapped), ft.DataCell(ft.Text(str(score)))])
              for name, score in [('Alice', 30), ('Bob', 10), ('Carol', 20)]],
        sort_keys={1: lambda row: int(row.cells[1].content.value)}, height=156,
        column_widths=[220, 160])
    page.add(sample_status, sample)

if __name__ == "__main__":
    ft.run(main)
