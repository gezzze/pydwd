from wetterdienst.util.url import ConnectionString


def test_connectionstring_database_from_path():

    url = "foobar://host:1234/dbname"
    cs = ConnectionString(url)

    assert cs.get_database() == "dbname"


def test_connectionstring_database_from_query_param():

    url = "foobar://host:1234/?database=dbname"
    cs = ConnectionString(url)

    assert cs.get_database() == "dbname"


def test_connectionstring_table_from_query_param():
    url = "foobar://host:1234/?database=dbname&table=tablename"
    cs = ConnectionString(url)

    assert cs.get_table() == "tablename"
