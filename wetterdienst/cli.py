# -*- coding: utf-8 -*-
import json
import sys
import logging
from datetime import datetime, timedelta

from docopt import docopt
from munch import Munch
import pandas as pd

from wetterdienst import __appname__, __version__
from wetterdienst.dwd.forecasts import DWDMosmixSites, DWDMosmixData
from wetterdienst.dwd.observations.store import StorageAdapter
from wetterdienst.util.cli import normalize_options, setup_logging, read_list
from wetterdienst.dwd.observations.api import (
    DWDObservationData,
    DWDObservationSites,
    DWDObservationMetadata,
)
from wetterdienst.dwd.observations import (
    DWDObservationParameterSet,
    DWDObservationResolution,
    DWDObservationPeriod,
)

log = logging.getLogger(__name__)


def run():
    """
    Usage:
      wetterdienst dwd observations sites --parameter=<parameter> --resolution=<resolution> --period=<period> [--station=<station>] [--latitude=<latitude>] [--longitude=<longitude>] [--number=<number>] [--distance=<distance>] [--persist] [--sql=<sql>] [--format=<format>]
      wetterdienst dwd observations readings --parameter=<parameter> --resolution=<resolution> --station=<station> [--period=<period>] [--persist] [--date=<date>] [--tidy] [--sql=<sql>] [--format=<format>] [--target=<target>]
      wetterdienst dwd observations readings --parameter=<parameter> --resolution=<resolution> --latitude=<latitude> --longitude=<longitude> [--period=<period>] [--number=<number>] [--distance=<distance>] [--persist] [--tidy] [--date=<date>] [--sql=<sql>] [--format=<format>] [--target=<target>]
      wetterdienst dwd forecasts sites [--date=<date>] [--station=<station>] [--latitude=<latitude>] [--longitude=<longitude>] [--number=<number>] [--distance=<distance>] [--persist] [--sql=<sql>] [--format=<format>]
      wetterdienst dwd forecasts readings --parameter=<parameter> --mosmix_type=<mosmix_type> --station=<station> [--persist] [--date=<date>] [--tidy] [--sql=<sql>] [--format=<format>] [--target=<target>]
      wetterdienst dwd about [parameters] [resolutions] [periods]
      wetterdienst dwd about coverage [--parameter=<parameter>] [--resolution=<resolution>] [--period=<period>]
      wetterdienst service [--listen=<listen>]
      wetterdienst --version
      wetterdienst (-h | --help)

    Options:
      --parameter=<parameter>       Parameter Set/Parameter, e.g. "kl" or "precipitation_height", etc.
      --resolution=<resolution>     Dataset resolution: "annual", "monthly", "daily", "hourly", "minute_10", "minute_1"
      --period=<period>             Dataset period: "historical", "recent", "now"
      --station=<station>           Comma-separated list of station identifiers
      --latitude=<latitude>         Latitude for filtering by geoposition.
      --longitude=<longitude>       Longitude for filtering by geoposition.
      --number=<number>             Number of nearby stations when filtering by geoposition.
      --distance=<distance>         Maximum distance in km when filtering by geoposition.
      --persist                     Save and restore data to filesystem w/o going to the network
      --date=<date>                 Date for filtering data. Can be either a single date(time) or
                                    an ISO-8601 time interval, see https://en.wikipedia.org/wiki/ISO_8601#Time_intervals.
      --mosmix_type=<mosmix_type>   type of mosmix, either 'small' or 'large'
      --sql=<sql>                   SQL query to apply to DataFrame.
      --format=<format>             Output format. [Default: json]
      --target=<target>             Output target for storing data into different data sinks.
      --version                     Show version information
      --debug                       Enable debug messages
      --listen=<listen>             HTTP server listen address. [Default: localhost:7890]
      -h --help                     Show this screen


    Examples requesting stations:

      # Get list of all stations for daily climate summary data in JSON format
      wetterdienst dwd sites --parameter=kl --resolution=daily --period=recent

      # Get list of all stations in CSV format
      wetterdienst dwd sites --parameter=kl --resolution=daily --period=recent --format=csv

      # Get list of specific stations
      wetterdienst dwd sites --resolution=daily --parameter=kl --period=recent --station=1,1048,4411

      # Get list of specific stations in GeoJSON format
      wetterdienst dwd sites --resolution=daily --parameter=kl --period=recent --station=1,1048,4411 --format=geojson

    Examples requesting readings:

      # Get daily climate summary data for specific stations
      wetterdienst dwd readings --station=1048,4411 --parameter=kl --resolution=daily --period=recent

      # Optionally save/restore to/from disk in order to avoid asking upstream servers each time
      wetterdienst dwd readings --station=1048,4411 --parameter=kl --resolution=daily --period=recent --persist

      # Limit output to specific date
      wetterdienst dwd readings --station=1048,4411 --parameter=kl --resolution=daily --period=recent --date=2020-05-01

      # Limit output to specified date range in ISO-8601 time interval format
      wetterdienst dwd readings --station=1048,4411 --parameter=kl --resolution=daily --period=recent --date=2020-05-01/2020-05-05

      # The real power horse: Acquire data across historical+recent data sets
      wetterdienst dwd readings --station=1048,4411 --parameter=kl --resolution=daily --period=historical,recent --date=1969-01-01/2020-06-11

      # Acquire monthly data for 2020-05
      wetterdienst dwd readings --station=1048,4411 --parameter=kl --resolution=monthly --period=recent,historical --date=2020-05

      # Acquire monthly data from 2017-01 to 2019-12
      wetterdienst dwd readings --station=1048,4411 --parameter=kl --resolution=monthly --period=recent,historical --date=2017-01/2019-12

      # Acquire annual data for 2019
      wetterdienst dwd readings --station=1048,4411 --parameter=kl --resolution=annual --period=recent,historical --date=2019

      # Acquire annual data from 2010 to 2020
      wetterdienst dwd readings --station=1048,4411 --parameter=kl --resolution=annual --period=recent,historical --date=2010/2020

      # Acquire hourly data
      wetterdienst dwd readings --station=1048,4411 --parameter=air_temperature --resolution=hourly --period=recent --date=2020-06-15T12

    Examples using geospatial features:

      # Acquire stations and readings by geoposition, request specific number of nearby stations.
      wetterdienst dwd sites --resolution=daily --parameter=kl --period=recent --lat=49.9195 --lon=8.9671 --num=5
      wetterdienst dwd readings --resolution=daily --parameter=kl --period=recent --lat=49.9195 --lon=8.9671 --num=5 --date=2020-06-30

      # Acquire stations and readings by geoposition, request stations within specific radius.
      wetterdienst dwd sites --resolution=daily --parameter=kl --period=recent --lat=49.9195 --lon=8.9671 --distance=25
      wetterdienst dwd readings --resolution=daily --parameter=kl --period=recent --lat=49.9195 --lon=8.9671 --distance=25 --date=2020-06-30

    Examples using SQL filtering:

      # Find stations by state.
      wetterdienst dwd sites --parameter=kl --resolution=daily --period=recent --sql="SELECT * FROM data WHERE state='Sachsen'"

      # Find stations by name (LIKE query).
      wetterdienst dwd sites --parameter=kl --resolution=daily --period=recent --sql="SELECT * FROM data WHERE lower(station_name) LIKE lower('%dresden%')"

      # Find stations by name (regexp query).
      wetterdienst dwd sites --parameter=kl --resolution=daily --period=recent --sql="SELECT * FROM data WHERE regexp_matches(lower(station_name), lower('.*dresden.*'))"

      # Filter measurements: Display daily climate observation readings where the maximum temperature is below two degrees.
      wetterdienst dwd readings --station=1048,4411 --parameter=kl --resolution=daily --period=recent --sql="SELECT * FROM data WHERE element='temperature_air_max_200' AND value < 2.0;"

    Examples for inquiring metadata:

      # Display list of available parameters (air_temperature, precipitation, pressure, ...)
      wetterdienst dwd about parameters

      # Display list of available resolutions (10_minutes, hourly, daily, ...)
      wetterdienst dwd about resolutions

      # Display list of available periods (historical, recent, now)
      wetterdienst dwd about periods

      # Display coverage/correlation between parameters, resolutions and periods.
      # This can answer questions like ...
      wetterdienst dwd about coverage

      # Tell me all periods and resolutions available for 'air_temperature'.
      wetterdienst dwd about coverage --parameter=air_temperature

      # Tell me all parameters available for 'daily' resolution.
      wetterdienst dwd about coverage --resolution=daily

    Examples for exporting data to databases:

      # Shortcut command for fetching readings from DWD
      alias fetch="wetterdienst dwd readings --station=1048,4411 --parameter=kl --resolution=daily --period=recent"

      # Store readings to DuckDB
      fetch --target="duckdb://database=dwd.duckdb&table=weather"

      # Store readings to InfluxDB
      fetch --target="influxdb://localhost/?database=dwd&table=weather"

      # Store readings to CrateDB
      fetch --target="crate://localhost/?database=dwd&table=weather"

    Run as HTTP service:

      wetterdienst dwd service
      wetterdienst dwd service --listen=0.0.0.0:9999

    """

    appname = f"{__appname__} {__version__}"

    # Read command line options.
    options = normalize_options(docopt(run.__doc__, version=appname))

    # Setup logging.
    debug = options.get("debug")

    log_level = logging.INFO

    if debug:  # pragma: no cover
        log_level = logging.DEBUG

    setup_logging(log_level)

    # Run service.
    if options.service:  # pragma: no cover
        listen_address = options.listen
        log.info(f"Starting {appname}")
        log.info(f"Starting web service on {listen_address}")
        from wetterdienst.service import start_service

        start_service(listen_address)
        return

    # Output domain information.
    if options.about:
        about(options)
        return

    # Sanity checks.
    if options.readings and options.format == "geojson":
        raise KeyError("GeoJSON format only available for stations output")

    # Acquire station list, also used for readings if required.
    # Filtering applied for distance (a.k.a. nearby) and pre-selected stations
    df = None
    if options.sites:
        df = get_sites(options)

        if df.empty:
            log.error("No data available for given constraints")
            sys.exit(1)

    # Acquire observations.
    if options.readings:
        # Use list of station identifiers.
        if options.station or (options.lat and options.lon):
            station_ids = (
                read_list(options.station)
                or df.STATION_ID.unique()
                or df.WMO_ID.unique()
            )
        else:
            raise KeyError("Either --station or --lat, --lon required")

        storage = StorageAdapter(persist=options.persist)

        # Funnel all parameters to the workhorse.
        if options.observations:
            readings = DWDObservationData(
                station_ids=station_ids,
                parameters=read_list(options.parameter),
                resolution=options.resolution,
                periods=read_list(options.period),
                storage=storage,
                humanize_column_names=True,
                tidy_data=options.tidy,
            )
        elif options.forecasts:
            readings = DWDMosmixData(
                station_ids=station_ids,
                parameters=read_list(options.parameter),
                mosmix_type=options.type,
                humanize_column_names=True,
                tidy_data=options.tidy,
            )

        # Collect data and merge together.
        try:
            df = readings.collect_safe()

        except ValueError as ex:
            log.exception(ex)
            sys.exit(1)

    # Sanity checks.
    if df is None:
        log.error("No data available")
        sys.exit(1)

    # Filter readings by datetime expression.
    if options.readings and options.date:
        df = df.dwd.filter_by_date(options.date, readings.resolution)

    # Make column names lowercase.
    df = df.dwd.lower()

    # Apply filtering by SQL.
    if options.sql:
        log.info(f"Filtering with SQL: {options.sql}")
        df = df.io.sql(options.sql)

    # Emit to data sink, e.g. write to database.
    if options.target:
        log.info(f"Writing data to target {options.target}")
        df.io.export(options.target)
        return

    # Render to output format.
    try:
        output = df.dwd.format(options.format)
    except KeyError as ex:
        log.error(
            f'{ex}. Output format must be one of "json", "geojson", "csv", "excel".'
        )
        sys.exit(1)

    print(output)


def get_sites(options: Munch) -> pd.DataFrame:
    """
    Convenience utility function to dispatch command
    line options related to geospatial requests.

    It will get used from both acquisition requests for station-
    and measurement data.

    It is able to handle both "number of stations nearby"
    and "maximum distance in kilometers" query flavors.

    :param options: Normalized docopt command line options.
    :return: nearby_stations
    """

    # Obtain DWIM date range for station liveness.
    # TODO: Obtain from user.
    #   However, some dates will not work and Pandas will croak with:
    #   KeyError: "None of [Int64Index([0, 0, 0, 0, 0], dtype='int64')] are in the [index]"
    # See also https://github.com/earthobservations/wetterdienst/pull/145#discussion_r487698588.

    days500 = datetime.utcnow() + timedelta(days=-500)
    now = datetime.utcnow() + timedelta(days=-2)

    start_date = datetime(days500.year, days500.month, days500.day)
    end_date = datetime(now.year, now.month, now.day)

    sites = None
    if options.sites:
        if options.observations:
            sites = DWDObservationSites(
                parameter_set=options.parameter,
                resolution=options.resolution,
                period=options.period,
                start_date=start_date,
                end_date=end_date,
            )
        elif options.forecasts:
            sites = DWDMosmixSites()

        if options.latitude and options.longitude:
            if options.number:
                sites = sites.nearby_number(
                    latitude=float(options.latitude),
                    longitude=float(options.longitude),
                    num_stations_nearby=int(options.number),
                )
            elif options.distance:
                sites = sites.nearby_radius(
                    latitude=float(options.latitude),
                    longitude=float(options.longitude),
                    max_distance_in_km=int(options.distance),
                )
        else:
            sites = sites.all()

        if options.station:
            station_ids = read_list(options.station)

            if options.observations:
                sites = sites[sites.STATION_ID.isin(station_ids)]
            else:
                sites = sites[sites.WMO_ID.isin(station_ids)]

        return sites
    return pd.DataFrame()


def about(options: Munch):
    """
    Output possible arguments for command line options
    "--parameter", "--resolution" and "--period".

    :param options: Normalized docopt command line options.
    """

    def output(thing):
        for item in thing:
            if item:
                if hasattr(item, "value"):
                    value = item.value
                else:
                    value = item
                print("-", value)

    if options.parameters:
        output(DWDObservationParameterSet)

    elif options.resolutions:
        output(DWDObservationResolution)

    elif options.periods:
        output(DWDObservationPeriod)

    elif options.coverage:
        output = json.dumps(
            DWDObservationMetadata(
                resolution=options.resolution,
                parameter_set=read_list(options.parameter),
                period=read_list(options.period),
            ).discover_parameter_sets(),
            indent=4,
        )
        print(output)

    else:
        log.error(
            'Please invoke "wetterdienst dwd about" with one of these subcommands:'
        )
        output(["parameters", "resolutions", "periods", "coverage"])
        sys.exit(1)
