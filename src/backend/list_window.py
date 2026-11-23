"""Bounded row viewport and selection, independent of either UI renderer."""
import asyncio
from collections import OrderedDict
import sys


def wheel_step(delta):
    """One wheel event is one row, independent of OS pixel-wheel settings."""
    return (delta > 0) - (delta < 0)


class ListWindow:
    def __init__(self, records, row_builder, *, sort_keys=None, cache_size=256):
        self.records = records
        self.row_builder = row_builder
        self.sort_keys = sort_keys or {}
        self.order = range(len(records))
        self.first = 0
        self.visible = 12
        self.height = 502
        self.track_height = 446
        self.drag_offset = 0
        self.cache_size = cache_size
        self.cache = OrderedDict()
        self.all_selected = False
        self.exceptions = set()
        self.sort_column_index = None
        self.sort_ascending = True
        self.sorting = False
        self.filtering = False
        self._filter = None
        self._applied_filter = None
        self._view_ticket = 0

    @property
    def total_count(self):
        return len(self.records)

    @property
    def count(self):
        return len(self.order)

    @property
    def maximum(self):
        return max(0, self.count - self.visible)

    @property
    def selected_count(self):
        return self.count - len(self.exceptions) if self.all_selected else len(self.exceptions)

    def selected(self, row_id):
        return self.all_selected != (row_id in self.exceptions)

    def toggle(self, row_id):
        if not 0 <= row_id < self.total_count:
            return
        if self._applied_filter is not None and not self._applied_filter(self.records[row_id]):
            return
        if row_id in self.exceptions:
            self.exceptions.remove(row_id)
        else:
            self.exceptions.add(row_id)

    def toggle_all(self):
        self.all_selected = self.selected_count != self.count
        self.exceptions.clear()

    def move(self, first):
        first = min(self.maximum, max(0, round(first)))
        changed = first != self.first
        self.first = first
        return changed

    def resize(self, height, row_height, heading_height):
        visible = max(1, int(max(0, height - heading_height) // row_height))
        changed = self.height != height or self.visible != visible
        self.height, self.visible = height, visible
        self.move(self.first)
        return changed

    def values(self, row_id):
        if row_id not in self.cache:
            self.cache[row_id] = tuple(self.row_builder(self.records[row_id]))
            if len(self.cache) > self.cache_size:
                self.cache.popitem(last=False)
        else:
            self.cache.move_to_end(row_id)
        return self.cache[row_id]

    def rows(self):
        return [(row_id, self.values(row_id))
                for row_id in self.order[self.first:self.first + self.visible]]

    def thumb(self):
        height = min(self.track_height, max(28, self.track_height * self.visible / max(1, self.count)))
        travel = max(0, self.track_height - height)
        top = travel * self.first / max(1, self.maximum)
        return top, height, travel

    async def sort(self, column):
        ascending = self.sort_column_index != column or not self.sort_ascending
        self.sort_column_index, self.sort_ascending = column, ascending
        return await self._rebuild_order()

    async def set_filter(self, predicate=None):
        """Filter raw records, retaining sort order; selection resets on change.

        Only record IDs are materialized, never the full set of cell values or
        controls. Filtering and sorting share a revision so stale jobs cannot
        replace a newer view, including after navigation.
        """
        self._filter = predicate
        return await self._rebuild_order()

    async def _rebuild_order(self):
        self._view_ticket += 1
        ticket = self._view_ticket
        predicate = self._filter
        column, ascending = self.sort_column_index, self.sort_ascending
        self.sorting = column is not None
        self.filtering = predicate is not self._applied_filter

        def matching(start, stop):
            return [i for i in range(start, stop) if predicate(self.records[i])]

        def ordered(indices):
            if column is None:
                return indices
            key = self.sort_keys.get(column, lambda record: self.row_builder(record)[column])
            return sorted(indices, key=lambda i: key(self.records[i]), reverse=not ascending)

        def work():
            indices = matching(0, self.total_count) if predicate else range(self.total_count)
            return ordered(indices)

        try:
            if sys.platform == "emscripten" and predicate is not None:
                # Browser Python has no worker threads. Yield between batches
                # so filtering does not monopolize the UI/event loop.
                indices = []
                for start in range(0, self.total_count, 8192):
                    indices.extend(matching(start, min(start + 8192, self.total_count)))
                    await asyncio.sleep(0)
                    if ticket != self._view_ticket:
                        return False
                order = ordered(indices)
            else:
                order = work() if sys.platform == "emscripten" else await asyncio.to_thread(work)
            if ticket != self._view_ticket:
                return False
            if predicate is not self._applied_filter:
                self.all_selected = False
                self.exceptions.clear()
            self._applied_filter = predicate
            self.order = order
            self.first = 0
            return True
        finally:
            if ticket == self._view_ticket:
                self.sorting = self.filtering = False
