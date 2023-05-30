#!/usr/bin/python3

# Copyright (C) 2023  Steven Trabert
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import fitparse
import argparse
from collections import deque
from dataclasses import dataclass
from datetime import datetime as dt
from enum import Enum, auto
import math
import numpy as np
import sys

K = 16
N = (4 * K) + 1


class state_t(Enum):
    stopped = auto()
    running = auto()


@dataclass
class DecodeState:
    ts: dt = None
    lat: float = None
    lon: float = None
    hr: int = None
    rrprev: float = None
    statecnt: int = 0
    q1: deque = deque([0] * N, N)
    state: state_t = state_t.stopped


parser = argparse.ArgumentParser(
    description="FIT file HRV analyzer",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("src", help="Input FIT file")
parser.add_argument(
    "--threshold", "-t", type=float, help="HRV threshold(msec)", default=50
)
args = parser.parse_args()

try:
    fitfile = fitparse.FitFile(
        args.src,
        check_crc=True,
        data_processor=fitparse.processors.StandardUnitsDataProcessor(),
    )
except fitparse.utils.FitParseError as e:
    print("Error while parsing .FIT file: %s" % e)
    sys.exit(1)

threshold = args.threshold
data = []
sd = DecodeState()
cnt = 0

print(
    "timestamp,latitude,longitude,HR(bpm),RR(msec),RRprev(msec),instantaneous HR(bpm),est. SDΔRR(msec),warn"
)
for record in fitfile.get_messages(["hrv", "record", "event"]):
    if record.name == "hrv":
        if sd.state == state_t.running:
            for record_data in record:
                for RR_interval in record_data.value:
                    if RR_interval is not None:
                        rr = RR_interval * 1000.0
                        sd.q1.pop()
                        if sd.rrprev == None:
                            sd.q1.appendleft(0.0)
                        else:
                            sd.q1.appendleft(rr - sd.rrprev)
                        # Estimate the standard deviation of the RR interval
                        # differences from inner quartile range (or other
                        # subset of the data) for robustness to outliers.
                        # This metric, "SDΔRR", is similar to RMSSD.
                        q2 = sorted(sd.q1)
                        sigmaest = (q2[3 * K] - q2[K]) / 1.349
                        data.append(
                            [
                                sd.ts,
                                sd.lat,
                                sd.lon,
                                sd.hr,
                                rr,
                                sd.rrprev,
                                60.0 / RR_interval,
                                "",
                                "",
                            ]
                        )
                        if sd.statecnt >= (N - 1):
                            warn = 1 if sigmaest > threshold else 0
                            data[cnt - (2 * K)][7] = sigmaest
                            data[cnt - (2 * K)][8] = warn
                        sd.rrprev = rr
                        sd.statecnt += 1
                        cnt += 1
    elif record.name == "record":
        sd.ts = record.get_value("timestamp")
        sd.hr = record.get_value("heart_rate")
        sd.lat = record.get_value("position_lat")
        sd.lon = record.get_value("position_long")
    elif record.name == "event":
        eventtype = record.get_value("event_type")
        # hrv data is unreliable after stop_all until we get started again
        if eventtype == "stop_all":
            sd = DecodeState()
        elif eventtype == "start":
            sd.state = state_t.running

for row in data:
    print(*row, sep=",")
