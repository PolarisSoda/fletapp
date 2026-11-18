# Virtual table prototype

The extension lives at `../flet-virtual-table`, separately from this application.
`uv sync` installs it as a local dependency.

Build the standalone benchmark with:

```powershell
uv run flet build windows --module-name table_benchmark --yes
```

The stock Flet desktop client cannot render custom extensions. A successful
custom Flutter build is required before testing the UI.

The benchmark materializes 500,000 tuples with ten integer values each in Python.
Only viewport windows (up to 512 rows per response) cross the control protocol.
Flutter uses TableView.builder with a pinned header and a draggable scrollbar.
Request IDs reject stale replies. The cache contains one window, not the full dataset.

Current scope: fixed-size text cells and vertical range requests. This is an
initial prototype, not a DataTable/DataTable2-compatible replacement yet. Sorting,
selection, arbitrary Flet cell controls, variable widths, editing, error recovery,
column-window transport, and measured Flutter frame statistics remain pending.

`build/virtual-table-staging/python-benchmark.json` records Python-only timings;
these do not establish UI performance. Reproduce with
`.venv/Scripts/python.exe build/virtual-table-staging/measure.py`.
