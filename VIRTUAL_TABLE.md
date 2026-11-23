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

## Row-wheel scrolling and pure Flet comparison

Both navigation screens use the same 500,000 records, ten columns, column widths,
38-pixel rows and 46-pixel headings. One vertical pointer-wheel event moves one
row regardless of the OS-provided pixel delta; zero/horizontal deltas do not move
rows. Wheel movement snaps from a fractional scrollbar offset to a row boundary.
Scrollbar dragging still traverses the entire dataset, rather than one window.
Touch/trackpad drag behavior is distinct from discrete mouse-wheel input.

The local extension's `RowScrollController` handles wheel input in Flutter, without
a Python round trip per row. Its prefetch window includes 64 rows before and extra
rows after the viewport; the next window is requested only near a cache edge.
Ordinary scrolling can therefore keep displaying cached rows. A large scrollbar
jump can still briefly show placeholders while a new range arrives.

`src/controls/sticky_list.py` is a separate, app-owned `StickyListView` using only
the public Flet package. `Canvas` draws visible text cells and `GestureDetector`
receives wheel/tap/drag input. The horizontal scrollable contains the heading and
body together; the independent vertical scrollbar stays at the right edge even
when viewing the last columns. The control displays real values immediately,
keeps an LRU of at most 256 raw records, supports sorting and select-all through
exceptions, and retains position/selection/ordering on re-entry. Its default cells
are painted text. `cell_builder(record, row_id, column_index)` can return any Flet
control (including Row/Column/buttons/fields) for an overlay cell, or None to use
painted text. Only visible cells build these controls. `row_height` is configurable
and fixed across rows. Persist editable data in the provider/view model; offscreen
controls are discarded. The extension retains its pinned checkbox-column feature.

The pure control has no import of `flet_virtual_table` or `flet_datagrid`. Run it
with the stock Flet client using `uv run flet run src/pure_list_demo.py --web`.
The combined application still needs its existing custom build for the other tab.
`ListWindow` owns provider/order/selection independently of the renderer; both UI
branches share this model and the pure control. The declarative branch publishes
fresh bounded drawings through observable state, instead of mutating frozen UI.

For comparison, keep viewport size, data, browser/native runtime and build mode
equal. Compare first entry, repeat entry, ordinary wheel events, a sustained wheel
sequence, dragging the thumb to the final rows, and horizontal scrolling. Sorting
has a separate whole-dataset cost and should be measured separately. The pure
control processes each wheel event in Python, whereas the extension scrolls
locally inside its cache; Python/protocol timings alone are not a frame-rate test.
No WPF-level or fixed-FPS guarantee is claimed without measuring the target device.

## Native ListView and input/lifecycle fixes

The **ListView 목록** tab uses `src/controls/windowed_list_view.py`, a real
`ft.ListView` with ordinary Flet row controls. `build_controls_on_demand=True`
enables Flutter's lazy widget construction. The tab switches between fixed
`item_extent` and `prototype_item` (never both simultaneously). These settings
do not lazily construct Python controls: the separate `ListWindow` provider still
bounds the Python control list to the visible window. The full-range logical
scrollbar addresses all 500,000 records. Because the native list holds only whole
visible rows, its own pixel-scroll extent stays zero; the shared wheel handler
moves exactly one logical row. The header remains outside the vertical ListView,
and both header/body share horizontal scrolling while the right scrollbar stays
fixed. This windowed implementation is intentional, not a prebuilt 500,000-control
ListView relying only on Flutter on-demand rendering.

`WindowedListView` supports the same `cell_builder` as Canvas and also accepts
`row_control_builder(record, row_id, selected) -> ft.Control` for a whole custom
row. Use `row_height=56` (or another fixed size) for taller content. The **복합 셀**
switch demonstrates real Row/Column/IconButton content on both pure-Flet tabs;
clicking the nested button does not also toggle selection. Native hit controls
bind displayed record IDs, so a queued click cannot select a different row merely
because another wheel event changed the current viewport. Canvas no longer
selects rows from a whole-surface `on_tap_down` coordinate calculation.

Example cell hook (records remain raw provider data):

```python
def cell_builder(record, row_id, column):
    if column == 1:
        return ft.Row([
            ft.Icon(ft.Icons.INFO_OUTLINE, size=16),
            ft.Text(record["name"], expand=True),
            ft.IconButton(ft.Icons.PLAY_ARROW, on_click=lambda e: run(record)),
        ])
    return None
```

The virtual-table remount bug was a request-ID collision: every new Flutter
widget restarted at ID 1. A repeated top-range response could exactly equal the
cached Python property, causing Flet to emit no patch while the new widget waited.
Request IDs now use a client-wide sequence that advances beyond the cached reply,
including after client reload. IDs stay within 31 bits because the web MessagePack
codec does not support its Int64 accessor. Unanswered requests retry after 750 ms; stale
replies still fail the current-ID/revision check. This is independent of the pure
Flet renderer. Tests repeatedly switch among all three tabs and verify emitted
responses, including identical ranges after remount.

Standalone stock-client runner: `uv run flet run src/listview_demo.py --web`.

Both app-owned Canvas and ListView screens include a dataset dropdown (all,
CIFAR-10, Oxford Pets, Flowers-102). `ListWindow.set_filter(predicate)` scans raw
record IDs and rebuilds the matching index order, preserving the active sort.
Only visible rows are painted/built afterwards; filtering never constructs
500,000 rows or cell controls. The footer and scrollbar use the filtered count.
Changing the filter returns to the first row and clears selection; returning
through navigation preserves the chosen filter, position and subsequent selection.
Native Python computes the index order in a worker; browser Python yields between
8,192-record filter batches (the final sort remains synchronous in browser Python).
Filtering and sorting share request revisions, so late jobs cannot overwrite newer
results. Filtering costs a full provider scan and is separate from drawing cost.
This dropdown is on the two app-owned screens, not the Flutter extension screen.

Tests cover pure imports with the extension blocked, discrete wheel steps, final
row reachability, bounded caching, stable selection through sorting, and real
Flet session patches/navigation on both branches. The extension's Flutter widget
test sends real `PointerScrollEvent`s with several delta magnitudes to a scrollable.

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
