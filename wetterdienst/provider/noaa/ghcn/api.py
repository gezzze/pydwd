# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, earthobservations developers.
# Distributed under the MIT License. See LICENSE for more info.
from enum import Enum
from typing import List, Optional

import pandas as pd

from wetterdienst import Kind, Period, Provider
from wetterdienst.core.scalar.request import ScalarRequestCore
from wetterdienst.metadata.columns import Columns
from wetterdienst.metadata.datarange import DataRange
from wetterdienst.metadata.period import PeriodType
from wetterdienst.metadata.resolution import Resolution, ResolutionType
from wetterdienst.metadata.timezone import Timezone


class NoaaGhcnResolution(Enum):
    DAILY = Resolution.DAILY.value


class NoaaGhcnRequest(ScalarRequestCore):
    _data_range = DataRange.FIXED

    _has_datasets = True
    _unique_dataset = True

    _period_type = PeriodType.FIXED
    _period_base = Period.HISTORICAL

    _resolution_type = ResolutionType.FIXED
    _resolution_base = NoaaGhcnResolution

    provider = Provider.NOAA
    kind = Kind.OBSERVATION

    _parameter_base = None

    _origin_unit_tree = None
    _si_unit_tree = None

    _values = None

    _tz = Timezone.USA

    def __init__(
        self,
        parameter: List[str],
    ):
        super(NoaaGhcnRequest, self).__init__(
            parameter=parameter, resolution=Resolution.DAILY, period=Period.HISTORICAL
        )

    def _all(self) -> pd.DataFrame:
        df = pd.read_fwf(
            "https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt",
            dtype=str,
            header=None,
            colspecs=[(0, 11), (12, 20), (21, 30), (31, 37), (41, 71)],
        )

        df.columns = [
            Columns.STATION_ID.value,
            Columns.LATITUDE.value,
            Columns.LONGITUDE.value,
            Columns.HEIGHT.value,
            Columns.NAME.value,
        ]

        return df


if __name__ == "__main__":
    request = NoaaGhcnRequest(parameter="precipitation_height").all()

    print(request.df)
