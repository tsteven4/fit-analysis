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

import argparse
from collections import deque
from dataclasses import dataclass
from datetime import datetime as dt
from enum import Enum, auto
import sys

import fitparse
import folium
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_THRESHOLD = 50
DEFAULT_AXIS_LIMIT = 1.0


def cleanll(a):
    """remove rows that contain None values

    Parameters
    ----------
    a : ndarray
        The input array that may contain rows with None values

    Returns
    -------
    ndarray
        array without the rows that had None values
    """

    # pylint: disable=singleton-comparison
    return a[np.logical_not((a == None).any(axis=1)), :]


def analyze(fitfilename, axislimit=DEFAULT_AXIS_LIMIT, threshold=DEFAULT_THRESHOLD, includestopped=False):
    K = 16
    N = (4 * K) + 1

    class state_t(Enum):
        STOPPED = auto()
        RUNNING = auto()

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
        state: state_t = state_t.STOPPED

    try:
        fitfile = fitparse.FitFile(
            fitfilename,
            check_crc=True,
            data_processor=fitparse.processors.StandardUnitsDataProcessor(),
        )
    except fitparse.utils.FitParseError as e:
        print(f"Error while parsing .FIT file: {e}")
        sys.exit(1)

    data = []
    sd = DecodeState()
    cnt = 0
    warns = []
    hrvdatafound = False

    for record in fitfile.get_messages(["hrv", "record", "event"]):
        if record.name == "hrv":
            hrvdatafound = True
            if sd.state == state_t.RUNNING:
                for record_data in record:
                    for rr_interval in record_data.value:
                        if rr_interval is not None:
                            rr = rr_interval * 1000.0
                            sd.q1.pop()
                            if sd.rrprev is None:
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
                                    60.0 / rr_interval,
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
            if not includestopped and eventtype == "stop_all":
                # terminate any active warning
                if len(warns) != 0 and warns[-1][1] is None:
                    warns[-1][1] = cnt
                sd = DecodeState()
            elif eventtype == "start":
                sd.state = state_t.RUNNING

    if not hrvdatafound:
        print(
            "No HRV data found in "
            + fitfilename
            + ". Is HRV logging enabled on your device?",
            file=sys.stderr,
        )
        return

    with open(
        fitfilename.replace(".fit", "") + ".csv", "w", encoding="utf-8"
    ) as csvfile:
        print(
            "timestamp,latitude,longitude,HR(bpm),RR(msec),RRprev(msec),"
            "instantaneous HR(bpm),est. SDΔRR(msec),warn",
            file=csvfile,
        )
        for row in data:
            print(*row, sep=",", file=csvfile)
        csvfile.close()

    genmap = len(warns) != 0
    if genmap:
        eventmap = folium.Map()
        folium.PolyLine(cleanll(np.array(data)[:, [1, 2]])).add_to(eventmap)
        eventmap.fit_bounds(eventmap.get_bounds(), padding=(10, 10))

    figno = 0
    for w in warns:
        wstart = w[0]
        wend = w[1]
        if wend is None:
            wend = len(data)
        if (wend - wstart) < 20:
            continue

        subset = np.array(data[wstart:wend])
        y = subset[:, 4]
        x = subset[:, 5]
        start = subset[0, 0]
        end = subset[-1, 0]

        if genmap:
            folium.PolyLine(cleanll(subset[:, [1, 2]]), color="red").add_to(eventmap)
            folium.Circle(subset[0, [1, 2]], color="red", fill=True, radius=10).add_to(eventmap)
            folium.Circle(subset[-1, [1, 2]], color="green", fill=True, radius=10).add_to(eventmap)
        fig, ax = plt.subplots(figsize=(10, 10), layout="constrained")
        ax.scatter(x, y)
        ax.plot(x, y, alpha=0.1)
        ax.set(xlim=(0, axislimit * 1000), ylim=(0, axislimit * 1000))
        ax.set_title(
            "\n".join(
                [
                    "Poincaré Plot",
                    fitfilename,
                    f"{start} to {end}",
                    f"Duration: {end - start}, "
                    + r"$\overline{HR}$"
                    + f": {1000.0*60.0*len(x)/sum(x):.1f} bpm",
                ]
            ),
            fontsize=14,
        )
        ax.set_xlabel(r"$RR_{n}(msec)$", fontsize=12)
        ax.set_ylabel(r"$RR_{n+1}(msec)$", fontsize=12)
        ax.xaxis.grid(True)
        ax.yaxis.grid(True)

        plt.savefig(fitfilename.replace(".fit", "") + "-" + str(figno) + ".png")
        plt.close(fig)

        figno += 1

    if genmap:
        eventmap.save(fitfilename.replace(".fit", ".html"))
    if figno > 0:
        print("Suspicious events found in " + fitfilename, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        prog="analyze_hrv",
        description="FIT file HRV analyzer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("src", help="Input FIT file")
    parser.add_argument(
        "--axislimit",
        "-a",
        type=float,
        help="Maximum axis value for plots(seconds)",
        default=DEFAULT_AXIS_LIMIT,
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        help="SDΔRR warning threshold(msec)",
        default=DEFAULT_THRESHOLD,
    )
    parser.add_argument(
        "--includestopped",
        "-i",
        action='store_true',
        help="include data while stopped",
    )
    args = parser.parse_args()
    analyze(fitfilename=args.src, axislimit=args.axislimit, threshold=args.threshold, includestopped=args.includestopped)


if __name__ == "__main__":
    main()
