""" unit tests for the tradedangerous.misc.deltarows module. """
from tradedangerous.misc import deltarows
from unittest import TestCase


# pylint: disable=import-outside-toplevel


class TestDeltaRows(TestCase):
    """ Unit tests for the td/misc/deltarows module. """
    def test_ops(self):
        assert deltarows.Op.ADD.value == 1
        assert deltarows.Op.MOD.value == 2
        assert deltarows.Op.DEL.value == 3
        assert deltarows.Op.UPD.value == 4

    def test_row_args(self):
        """ Test the positional-ordered construction. """
        my_columns = ["x", TestCase, 0, None]
        row = deltarows.DeltaRow(
            1,
            4.2,
            my_columns,
        )
        assert row.id == 1
        assert row.modified == 4.2
        # We don't want equality, we want it to be a reference.
        assert row.columns is my_columns

    def test_row_kwargs(self):
        """ Test the named-argument construction. """
        my_columns = ["y", TestDeltaRows, "string", 4.2 ]
        row = deltarows.DeltaRow(
            id=3,
            columns=my_columns,
            modified=None,
        )
        assert row.id == 3
        assert row.modified is None
        assert row.columns is my_columns

    def test_delta_empty(self):
        """ Confirm behavior of passing two empty streams."""
        result = deltarows.delta([], [])
        print(list(result))
        assert len(list(result)) == 0, "expected no rows from empty inputs"

    def test_delta_only_new(self):
        """ Pass in streams that only contain new rows. """
        from tradedangerous.misc.deltarows import Op, DeltaRow, delta
        old_rows = []
        new_rows = [
            DeltaRow(1, 4.2, ["x", TestCase, 0,    None]),
            DeltaRow(2, 4.2, ["y", None,     None, None]),
        ]
        # First, try just the first row
        result = delta(old_rows, new_rows[:1])
        rows = list(result)
        assert len(rows) == 1, "expected 1 row from new row"
        assert rows[0] == (Op.ADD, new_rows[0]), "expected ADD for new row"

        # Check that it works with an iterable
        result = delta(old_rows, (r for r in new_rows if r.id == 1))
        rows = list(result)
        assert len(rows) == 1, "expected 1 row from generator"
        assert rows[0] == (Op.ADD, new_rows[0]), "expected ADD for new row"

        # Now try both rows, which should both be new            
        result = delta(old_rows, new_rows)
        rows = list(result)
        assert len(rows) == 2, "expected 2 rows from new rows"
        assert rows[0] == (Op.ADD, new_rows[0]), "expected ADD for new row 1"
        assert rows[1] == (Op.ADD, new_rows[1]), "expected ADD for new row 2"

    def test_delta_only_old(self):
        """ When only old rows are present, they should be deleted. """
        from tradedangerous.misc.deltarows import Op, DeltaRow, delta
        old_rows = [
            DeltaRow(1, 4.2, ["x", TestCase, 0,    None]),
            DeltaRow(2, 4.2, ["y", None,     None, None]),
        ]
        new_rows = []
        # First try just the one row.
        result = delta(old_rows[:1], new_rows)
        rows = list(result)
        assert len(rows) == 1, "expected only 1 result"
        assert rows[0] == (Op.DEL, old_rows[0]), "expected DEL for old row"
    
        # Now try both rows, which should both be deleted
        result = delta(old_rows, new_rows)
        rows = list(result)
        assert len(rows) == 2, "expected 2 rows from old rows"
        assert rows[0] == (Op.DEL, old_rows[0]), "expected DEL for old row 1"
        assert rows[1] == (Op.DEL, old_rows[1]), "expected DEL for old row 2"

    def test_delta_same(self):
        """ Passing streams of the same data shouldn't result in any changes. """
        from tradedangerous.misc.deltarows import DeltaRow, delta
        rows = [
            DeltaRow(1, None, ["x", TestCase, 0, None]),
            # Try two the same to ensure we don't do anything weird
            DeltaRow(1, None, ["x", TestCase, 0, None]),
            # Test empty columns,
            DeltaRow(2, None, []),
            DeltaRow(3, None, ["y"]),
            DeltaRow(4, None, [None]),
        ]
        result = delta(rows[:1], rows[:1])
        assert next(result, None) is None, "expected no rows single same row"
        result = delta(rows[:2], rows[:2])
        assert next(result, None) is None, "expected no rows from two same rows"
        result = delta(rows[:3], rows[:3])
        assert next(result, None) is None, "expected no nows from three rows"
        result = delta(rows[:4], rows[:4])
        assert next(result, None) is None, "expected no rows from four rows"
        result = delta(rows, rows)
        assert next(result, None) is None, "expected no rows from all rows"

    def test_delta_modified(self):
        """ Test combinations that should result in an apparent modification. """
        from tradedangerous.misc.deltarows import DeltaRow, delta
        old_rows = [
            DeltaRow(1, 100, ["x"]), DeltaRow(1, 110, ["z"]),
        ]
        new_rows = [
            DeltaRow(1, 120, ["X"]), DeltaRow(1, 120, ["Z"]),
        ]
        result_rows = list(delta(old_rows, new_rows))
        assert len(result_rows) == 2, "expected both rows to be returned"
        assert result_rows[0] == (deltarows.Op.MOD, new_rows[0]), "expected first row to be modified"
        assert result_rows[1] == (deltarows.Op.MOD, new_rows[1]), "expected second row to be modified"

        # If we make the first new row matches the timestamp of the old row, it should not be returned.
        new_rows[0] = DeltaRow(1, 100, ["X"])
        result_rows = list(delta(old_rows, new_rows))
        assert len(result_rows) == 1, "expected only one row"
        assert result_rows[0] == (deltarows.Op.MOD, new_rows[1]), "expected second row to be modified"
        
        # If we make it None, it should not be returned still.
        new_rows[0] = DeltaRow(1, None, ["X"])
        result_rows = list(delta(old_rows, new_rows))
        assert len(result_rows) == 1, "expected only one row"
        assert result_rows[0] == (deltarows.Op.MOD, new_rows[1]), "expected second row to be modified"

        # Even if the new old row is None, we should be considered untouched.
        old_rows[0] = DeltaRow(1, None, ["x"])
        result_rows = list(delta(old_rows, new_rows))
        assert len(result_rows) == 1, "expected both rows to be returned"
        assert result_rows[0] == (deltarows.Op.MOD, new_rows[1]), "expected first row to be unmodified"
        
        # Increment that to 0, and we should still not be a change.
        new_rows[0] = DeltaRow(1, 0, ["X"])
        result_rows = list(delta(old_rows, new_rows))
        assert len(result_rows) == 1, "expected both rows to be returned"
        assert result_rows[0] == (deltarows.Op.MOD, new_rows[1]), "expected first row to be unmodified"

        # Same for the old row.
        old_rows[0] = DeltaRow(1, 0, ["x"])
        result_rows = list(delta(old_rows, new_rows))
        assert len(result_rows) == 1, "expected both rows to be returned"
        assert result_rows[0] == (deltarows.Op.MOD, new_rows[1]), "expected first row to be unmodified"

        # And same for old row == 0, new row == None
        new_rows[0] = DeltaRow(1, None, ["X"])
        result_rows = list(delta(old_rows, new_rows))
        assert len(result_rows) == 1, "expected both rows to be returned"
        assert result_rows[0] == (deltarows.Op.MOD, new_rows[1]), "expected first row to be unmodified"

    def test_delta_update(self):
        """ Tests that we correctly detect a change that only represents a timestamp delta. """
        from tradedangerous.misc.deltarows import DeltaRow, delta
        old_rows = [DeltaRow(100, None, ["x", TestCase,  0.0])]
        new_rows = [DeltaRow(100,   30, ["x", TestCase,  0.0])]
        result_rows = list(delta(old_rows, new_rows))
        assert len(result_rows) == 1, "expected row to be returned"
        assert result_rows[0][0] == deltarows.Op.UPD, "expected row to be marked for update"
        assert result_rows[0][1] == new_rows[0]

        # Now try different numeric values
        old_rows = [DeltaRow(100,    0, ["x", TestCase,  0.0])]
        result_rows = list(delta(old_rows, new_rows))
        assert len(result_rows) == 1, "expected row to be returned"
        assert result_rows[0][0] == deltarows.Op.UPD, "expected row to be marked for update"

        # Now let's reflect the timestamp into the columns too
        old_rows = [DeltaRow(123, 3.1, [None, 0, 1.1, "x", 3.1, ()])]
        new_rows = [DeltaRow(123, 4.2, [None, 0, 1.1, "x", 4.2, ()])]
        result_rows = list(delta(old_rows, new_rows))
        assert len(result_rows) == 1, "expected row to be returned"
        assert result_rows[0][0] == deltarows.Op.UPD, "expected row to be marked for update"
        assert result_rows[0][1] == new_rows[0]
    
    def test_delta_update_mixed(self):
        """ Apply a combination of tests. """
        from tradedangerous.misc.deltarows import DeltaRow, delta, Op
        old_rows, new_rows, expect_result = [], [], []
        # start with a deletion
        row1 = DeltaRow(1000, None, ["x", "y", (), None])
        old_rows += [row1]
        expect_result += [(Op.DEL, row1)]
        # Then an addition
        row2 = DeltaRow(1001, None, ["x", "y", (), None])
        new_rows += [row2]
        expect_result += [(Op.ADD, row2)]
        # An unmodified row
        row3 = DeltaRow(1002, 111, ["x", "y", (), 111])
        old_rows += [row3]
        new_rows += [row3]
        # A timestamp update
        row4 = DeltaRow(1100, 200, ["x", "y", (), 200])
        row5 = DeltaRow(1100, 201, ["x", "y", (), 200])
        old_rows += [row4]
        new_rows += [row5]
        expect_result += [(Op.UPD, row5)]
        # A modification
        row6 = DeltaRow(1200, 210, ["x", "y", (), 210])
        row7 = DeltaRow(1200, 220, ["X", "Y", (1,), 220])
        old_rows += [row6]
        new_rows += [row7]
        expect_result += [(Op.MOD, row7)]
        
        # Run with these rows
        result_rows = list(delta(old_rows, new_rows))
        assert result_rows == expect_result

        # Add a clear ID boundary separation
        old_rows += [DeltaRow(2000, 0, [])]
        new_rows += [DeltaRow(2000, 0, [])]
        original_result = list(expect_result)

        # What if we tack a bunch of adds on the end?
        old_rows += [row1, row2, row3]
        expect_result += [(Op.DEL, row1), (Op.DEL, row2), (Op.DEL, row3)]
        result_rows = list(delta(old_rows, new_rows))
        assert result_rows[:len(original_result)] == original_result, "earlier rows shouldn't be changed"
        assert result_rows == expect_result
        
        # Now use higher IDs to extend the adds
        new_rows += [row4, row5, row6]
        expect_result += [(Op.ADD, row4), (Op.ADD, row5), (Op.ADD, row6)]
        result_rows = list(delta(old_rows, new_rows))
        assert result_rows[:len(original_result)] == original_result, "earlier rows shouldn't be changed"
        assert result_rows == expect_result
