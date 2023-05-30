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
import matplotlib.pyplot as plt
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
    warnprev: bool = False
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
warns = []

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
                            warn = sigmaest > threshold
                            data[cnt - (2 * K)][7] = sigmaest
                            data[cnt - (2 * K)][8] = int(warn)
                            if not sd.warnprev and warn:
                                warns.append([cnt, None])
                            elif sd.warnprev and not warn:
                                warns[-1][1] = cnt
                            sd.warnprev = warn
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

with open(args.src.replace(".fit", "") + ".csv", "w") as csvfile:
    print(
        "timestamp,latitude,longitude,HR(bpm),RR(msec),RRprev(msec),instantaneous HR(bpm),est. SDΔRR(msec),warn",
        file=csvfile,
    )
    for row in data:
        print(*row, sep=",", file=csvfile)
    csvfile.close()

figno = 0
for w in warns:
    wstart = w[0]
    wend = w[1]
    if wend == None:
        wend = data[-1]
    if (wend - wstart) < 20:
        continue
    # plt.style.use("_mpl-gallery")

    nelements = wend - wstart
    subset = np.array(data[wstart:wend])
    x = subset[:, 4]
    y = subset[:, 5]
    start = subset[0, 0]
    end = subset[-1, 0]

    fig, ax = plt.subplots(figsize=(10, 10), layout="constrained")
    ax.scatter(x, y)
    ax.set(xlim=(0, 1000), ylim=(0, 1000))
    ax.set_title(
        "\n".join(
            [
                "Poincaré Plot",
                args.src,
                str(start) + " to " + str(end),
                str(end - start),
            ]
        ),
        fontsize=14,
    )
    ax.set_xlabel("RR[n](msec)", fontsize=12)
    ax.set_ylabel("RR[n-1](msec)", fontsize=12)
    ax.xaxis.grid(True)
    ax.yaxis.grid(True)

    plt.savefig(args.src.replace(".fit", "") + "-" + str(figno) + ".png")

    figno += 1

if figno > 0:
    print("Suspicious events found in " + args.src, file=sys.stderr)
