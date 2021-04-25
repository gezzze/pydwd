# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, earthobservations developers.
# Distributed under the MIT License. See LICENSE for more info.
import json
import logging
from typing import Optional

from click_params import StringListParamType
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from wetterdienst import Provider, Wetterdienst, __appname__, __version__
from wetterdienst.core.scalar.request import ScalarRequestCore
from wetterdienst.exceptions import ProviderError
from wetterdienst.ui.cli import get_api
from wetterdienst.ui.core import get_stations, get_values, set_logging_level
from wetterdienst.util.cli import setup_logging

app = FastAPI(debug=False)

log = logging.getLogger(__name__)

PRODUCER_NAME = "Wetterdienst"
PRODUCER_LINK = "https://github.com/earthobservations/wetterdienst"

CommaSeparator = StringListParamType(",")


@app.get("/", response_class=HTMLResponse)
def index():
    appname = f"{__appname__} {__version__}"

    about = "Wetterdienst - Open weather data for humans."

    sources = ""
    for provider in Provider:
        shortname = provider.name
        _, name, country, copyright_, url = provider.value
        sources += (
            f"<li><a href={url}>{shortname}</a> ({name}, {country}) - {copyright_}</li>"
        )

    return f"""
    <html>
        <head>
            <title>{appname}</title>
        </head>
        <body>
            <h3>About</h3>
            <h3>{about}</h3>
            <h4>Providers</h4>
            <ul>
                {sources}
            </ul>
            <h4>Providers</h4>
            <ul>
                <li><a href=restapi/coverage>coverage</a></li>
                <li><a href=restapi/stations>stations</a></li>
                <li><a href=restapi/values>values</a></li>
            </ul>
            <h4>Producer</h4>
            {PRODUCER_NAME} - <a href="{PRODUCER_LINK}">{PRODUCER_LINK}</a></li>
            <h4>Examples</h4>
            <ul>
            <li><a href="restapi/stations?provider=dwd&kind=observation&parameter=kl&resolution=daily&period=recent&all=true">DWD Observation stations</a></li>
            <li><a href="restapi/values?provider=dwd&kind=observation&parameter=kl&resolution=daily&period=recent&station-id=00011">DWD Observation values</a></li>
            </ul>
        </body>
    </html>
    """  # noqa:E501,B950


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return """
User-agent: *
Disallow: /api/
    """.strip()


@app.get("/restapi/coverage")
def coverage(
    provider: str = Query(default=None),
    kind: str = Query(default=None),
    debug: bool = Query(default=False),
    filter_=Query(alias="filter", default=None),
):
    set_logging_level(debug)

    if not provider or not kind:
        cov = Wetterdienst.discover()

        return Response(
            content=json.dumps(cov, indent=4), media_type="application/json"
        )

    api = get_api(provider=provider, kind=kind)

    # dataset = kwargs.get("dataset")
    # if dataset:
    #     dataset = read_list(dataset)

    cov = api.discover(
        filter_=filter_,
        # dataset=dataset,
        flatten=False,
    )

    return Response(content=json.dumps(cov, indent=4), media_type="application/json")


@app.get("/restapi/stations")
def stations(
    provider: str = Query(default=None),
    kind: str = Query(default=None),
    parameter: str = Query(default=None),
    resolution: str = Query(default=None),
    period: str = Query(default=None),
    all_: str = Query(alias="all", default=False),
    station_id: str = Query(default=None),
    name: str = Query(default=None),
    coordinates: str = Query(default=None),
    rank: int = Query(default=None),
    distance: float = Query(default=None),
    bbox: str = Query(default=None),
    sql: str = Query(default=None),
    fmt: str = Query(alias="format", default="json"),
    debug: bool = Query(default=False),
    pretty: bool = Query(default=False),
):
    if provider is None or kind is None:
        raise HTTPException(
            status_code=400,
            detail="Query arguments 'provider' and 'kind' are required",
        )

    if parameter is None or resolution is None:
        raise HTTPException(
            status_code=400,
            detail="Query arguments 'parameter', 'resolution' "
            "and 'period' are required",
        )

    if fmt not in ("json", "geojson"):
        raise HTTPException(
            status_code=400,
            detail="format argument must be one of json, geojson",
        )

    set_logging_level(debug)

    try:
        api = Wetterdienst(provider, kind)
    except ProviderError:
        return HTTPException(
            status_code=404,
            detail=f"Choose provider and kind from {app.url_path_for('coverage')}",
        )

    parameter = parameter.split(",")
    if period:
        period = period.split(",")
    if station_id:
        station_id = station_id.split(",")

    try:
        stations_ = get_stations(
            api=api,
            parameter=parameter,
            resolution=resolution,
            period=period,
            all_=all_,
            station_id=station_id,
            name=name,
            coordinates=coordinates,
            rank=rank,
            distance=distance,
            bbox=bbox,
            sql=sql,
            date=None,
            tidy=False,
            si_units=False,
        )
    except (KeyError, ValueError) as e:
        return HTTPException(status_code=404, detail=str(e))

    if not stations_.parameter or not stations_.resolution:
        return HTTPException(
            status_code=404,
            detail=f"No parameter found for provider {provider}, kind {kind}, "
            f"parameter(s) {parameter} and resolution {resolution}.",
        )

    # Postprocessing.
    # if sql is not None:
    #     results.filter_by_sql(sql)

    stations_.fill_gaps()

    indent = None
    if pretty:
        indent = 4

    if fmt == "json":
        output = stations_.to_dict()
    elif fmt == "geojson":
        output = stations_._to_ogc_feature_collection()

    output = make_json_response(output, api.provider)

    output = json.dumps(output, indent=indent, ensure_ascii=False)

    return Response(content=output, media_type="application/json")


@app.get("/restapi/values")
def values(
    provider: str = Query(default=None),
    kind: str = Query(default=None),
    parameter: str = Query(default=None),
    resolution: str = Query(default=None),
    period: str = Query(default=None),
    date: str = Query(default=None),
    all_: str = Query(alias="all", default=False),
    station: str = Query(default=None),
    name: str = Query(default=None),
    coordinates: str = Query(default=None),
    rank: int = Query(default=None),
    distance: float = Query(default=None),
    bbox: str = Query(default=None),
    sql: str = Query(default=None),
    sql_values: str = Query(alias="sql-values", default=None),
    # fmt: str = Query(alias="format", default="json"),
    tidy: bool = Query(default=True),
    si_units: bool = Query(alias="si-units", default=True),
    pretty: bool = Query(default=False),
    debug: bool = Query(default=False),
):
    """
    Acquire data from DWD.

    :param provider:
    :param kind:        string for product, either observation or forecast
    :param parameter:   Observation measure
    :param resolution:  Frequency/granularity of measurement interval
    :param period:      Recent or historical files
    :param date:        Date or date range
    :param all_:
    :param station:
    :param name:
    :param coordinates:
    :param rank:
    :param distance:
    :param bbox:
    :param sql:         SQL expression
    :param sql_values:
    :param fmt:
    :param tidy:        Whether to return data in tidy format. Default: True.
    :param si_units:
    :param pretty:
    :param debug:
    :return:
    """
    # TODO: Add geojson support
    fmt = "json"

    if provider is None or kind is None:
        raise HTTPException(
            status_code=400,
            detail="Query arguments 'provider' and 'kind' are required",
        )

    if parameter is None or resolution is None or date is None:
        raise HTTPException(
            status_code=400,
            detail="Query arguments 'parameter', 'resolution' "
            "and 'date' are required",
        )

    if fmt not in ("json", "geojson"):
        raise HTTPException(
            status_code=400,
            detail="format argument must be one of json, geojson",
        )

    set_logging_level(debug)

    try:
        api: ScalarRequestCore = Wetterdienst(provider, kind)
    except ProviderError:
        return HTTPException(
            status_code=404,
            detail=f"Given combination of provider and kind not available. "
            f"Choose provider and kind from {Wetterdienst.discover()}",
        )

    parameter = parameter.split(",")
    if period:
        period = period.split(",")
    if station:
        station = station.split(",")

    try:
        values_ = get_values(
            api=api,
            parameter=parameter,
            resolution=resolution,
            date=date,
            period=period,
            all_=all_,
            station_id=station,
            name=name,
            coordinates=coordinates,
            rank=rank,
            distance=distance,
            bbox=bbox,
            sql=sql,
            sql_values=sql_values,
            si_units=si_units,
            tidy=tidy,
        )
    except Exception as e:
        log.exception(e)

        return HTTPException(status_code=404, detail=e)

    indent = None
    if pretty:
        indent = 4

    output = values_.to_dict()

    # if fmt == "json":
    #     output = stations_.to_dict()
    # elif fmt == "geojson":
    #     output = stations_._to_ogc_feature_collection()

    output = make_json_response(output, api.provider)

    output = json.dumps(output, indent=indent, ensure_ascii=False)

    return Response(content=output, media_type="application/json")


def make_json_response(data, provider):
    name_local, name_english, country, copyright_, url = provider.value

    response = {
        "meta": {
            "provider": {
                "name_local": name_local,
                "name_english": name_english,
                "country": country,
                "copyright": copyright_,
                "url": url,
            },
            "producer": {
                "name": PRODUCER_NAME,
                "url": PRODUCER_LINK,
                "doi": "10.5281/zenodo.3960624",
            },
        },
        "data": data,
    }
    return response


def start_service(
    listen_address: Optional[str] = None, reload: Optional[bool] = False
):  # pragma: no cover

    setup_logging()

    if listen_address is None:
        listen_address = "127.0.0.1:7890"

    host, port = listen_address.split(":")
    port = int(port)
    from uvicorn.main import run

    run(app="wetterdienst.ui.restapi:app", host=host, port=port, reload=reload)
