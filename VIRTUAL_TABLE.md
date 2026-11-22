# Flet DataGrid

## Workbench view

The **대용량 목록** navigation item opens `src/ui/virtual_list.py`. It uses the
existing DataGrid/TableView extension, including its pinned heading row and
checkbox column, instead of a stock ListView containing every Python row.

`src/backend/virtual_list.py` supplies a deterministic 500,000-row demo. Records
are represented by `range(500_000)`; values are computed only for requested rows.
There is no startup data-generation loop or full-dataset Flet control list.
The viewport has bounded height and both axes are virtualized. The grid is built
on first navigation and its Python state is cached across navigation. Selection
and ordering persist; Flutter scroll offsets reset on remount. Returning to a
screen transmits at most its cached window, never the full dataset.

`NavigationDataGrid` suppresses patches while detached, allowing a worker sort
to finish after navigating away. Its finished state is sent on the next mount.
The declarative branch keeps its provider engine outside the frozen control tree
and publishes bounded snapshots through observable state.
Sorting still scans the entire provider and uses memory for an index order;
viewport virtualization does not make sorting constant-time. In browser Python,
the existing extension sorts synchronously; use native Python for worker sorts.
No frame-rate or zero-lag guarantee is claimed.

Build this screen with `uv run flet build windows --module-name main --yes`
or `uv run flet build web --module-name main --yes`. The standalone benchmark
below uses a different entry point. Stock `flet run` clients lack the extension.

`tests/test_virtual_list_view.py` checks lazy creation, bounded row production,
sort completion while detached, navigation patch sizes, and selection retention
using a real Flet messaging session. Run `uv run pytest` on both UI branches.

## Standalone benchmark

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
