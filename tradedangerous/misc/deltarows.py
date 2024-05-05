"""
Copyright (C) The Trade Dangerous Developers
See the LICENSE file for more information.
Original Author: Oliver 'kfsone' Smith <oliver@kfs.org>, 2024/05/04

Mechanism for identifying deltas between two row streams.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import sys
import typing

if typing.TYPE_CHECKING:
    from typing import Generator, Iterable, Optional, Union
    import datetime


# Use the 'slots' attribute when we have it.
if sys.version_info >= (3, 10, 0):
    dataclass_args = {'slots': True, 'frozen': True}
else:
    dataclass_args = {'frozen': True}


class Op(Enum):
    """ Enumerates the possible operations sync_sources can describe for a row. """
    ADD = 1     # New record
    MOD = 2     # Modified record
    DEL = 3     # Deleted record
    UPD = 4     # Timestamp update only


@dataclass(**dataclass_args)
class DeltaRow:
    """ Represents a row-stream element row. It requires you to surface the id and
        modified fields independently of the columns, so that the delta() method can
        match elements by ID and detect old vs new records.
        
        Example:
        
            old = [DeltaRow(id=1, name="A", modified=123, columns=(1, "A", None, 123)),
                   DeltaRow(id=3, name="C", modified=124, columns=(3, "C", "X",  124))]
            new = [DeltaRow(id=2, name="B", modified=150, columns=(2, "B", "B",  150)),
                   DeltaRow(id=3, name="C", modified=125, Columns=(3, "C", "Y",  125))]

            for op, row in sync_sources(old, new):
                print(op, row)

        Yields:
            Op.Add, new[0]  # because row is not present in old
            Op.Mod, new[1]  # because id=3 is in both but only the timestamp changed
    """
    # `id` can be an integer, a string, or an integer pair.
    id:         Union[int, str, tuple[int, int]]
    modified:   Optional[Union[int, float, datetime.datetime]]
    columns:    Iterable[Union[str, int, float]]


def delta(
          old: Iterable[DeltaRow], new: Iterable[DeltaRow],
          ) -> Generator[tuple[Op, DeltaRow], None, None]:
    """
        Compares two ordered sequences of DeltaRows to find gaps and changes and
        yields these with an op and the row affected.
        
        Both streams should be ordered by the "id" field.
        
        Items present in new_rows but not in old_rows are yielded as an ADD,
        while rows present in both but with modified fields are yield as
        MOD if old's modified is None or lower than new's modified.
        
        Modified of None is treated as zero. For the new to be considered
        newer, the old must have a lower modified value. If the older
        has a None modified while the new has a 0 modified, they will be
        considered equal.
        
        :param old_rows:    Iterable of the current state of the dataset
        :param new_rows:    Iterable of the new entries for the dataset
    """
    old_rows, new_rows = iter(old), iter(new)
    old_row, new_row = next(old_rows, None), next(new_rows, None)
    while old_row and new_row:
        if old_row.id < new_row.id:
            # Deletion
            yield Op.DEL, old_row
            old_row = next(old_rows, None)
            continue
            
        if old_row.id > new_row.id:
            # Addition
            yield Op.ADD, new_row
            new_row = next(new_rows, None)
            continue
            
        # Get the advance out of the way.
        prev_old_row, prev_new_row = old_row, new_row
        old_row, new_row = next(old_rows, None), next(new_rows, None)

        old_modified, new_modified = prev_old_row.modified, prev_new_row.modified
        if (old_modified or 0) >= (new_modified or 0):
            # older record is newer or they're both None.
            continue
            
        assert len(prev_old_row.columns) == len(prev_new_row.columns), "Mismatched records passed to sync_sources"
        op = Op.UPD  # timestamp update
        for columns in zip(prev_old_row.columns, prev_new_row.columns):
            if columns[0] != columns[1]:
                # Don't detect the timestamp changing as an alteration.
                if columns[0] is old_modified and columns[1] is new_modified:
                    continue
                op = Op.MOD  # actual change
                break

        yield op, prev_new_row

    # Only new records remaining means they are all additions. For example, when the original source
    # is empty, it will have no "old" rows, and the entire new stream can simply be yielded as adds.
    while new_row:
        yield Op.ADD, new_row
        new_row = next(new_rows, None)

    # Only old records, such as when there are no new records (partial update) or when many tail-
    # records have been deleted.
    while old_row:
        yield Op.DEL, old_row
        old_row = next(old_rows, None)


def delta_partial(
          old_rows: Iterable[DeltaRow], new_rows: Iterable[DeltaRow],
          ) -> Generator[tuple[Op, DeltaRow], None, None]:
    """ A convenience wrapper for delta that does not produce DEL operations. """
    yield from ((op, row) for op, row in delta(old_rows, new_rows) if op != Op.DEL)
