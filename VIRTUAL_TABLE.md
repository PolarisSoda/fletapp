# Flet DataGrid

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

Import `DataGrid` or its `DataTable` alias from `flet_datagrid`. Native Flet
DataColumn, DataRow and DataCell controls are accepted. For 500,000 rows use raw
`records` and optional lazy `row_builder`, rather than prebuilding all controls.
Per-column sorting, row selection, select-all with exceptions, native cell click
callbacks, fixed headings, numeric alignment and column widths are supported.
See the extension README for the API and compatibility boundaries.

Run the web benchmark with `uv run flet build web --module-name table_benchmark --yes`.
The benchmark includes both the large raw-data grid and a small native DataRow grid.
Tests cover stable selection through sorting, concurrent sorts, stale requests,
bulk selection and bounded lazy row construction. This is not exact parity with
every DataTable styling option; rows use fixed heights.

`build/virtual-table-staging/python-benchmark.json` records Python-only timings;
these do not establish UI performance. Reproduce with
`.venv/Scripts/python.exe build/virtual-table-staging/measure.py`.
