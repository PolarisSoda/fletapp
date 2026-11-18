from unittest.mock import patch
import pytest
from flet_virtual_table import FletVirtualTable

def test_window_bounds_and_shape():
    table = FletVirtualTable(columns=['A', 'B'], row_count=500_000)
    with patch.object(FletVirtualTable, 'update'):
        table.supply(3, 499_999, [[1, 2]])
        assert table.response['start'] == 499_999
        with pytest.raises(ValueError):
            table.supply(4, 500_000, [[1, 2]])
        with pytest.raises(ValueError):
            table.supply(4, 0, [[1]])
        with pytest.raises(ValueError):
            table.supply(4, 0, [[1, 2]] * 513)
