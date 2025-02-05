#!/home/friedmar/.pyenv/bin/python
# -*- coding: UTF-8 -*-

### Imports
import os
from datetime import datetime, date, time, timedelta
import pytz 
import caldav
from caldav.elements import dav, cdav
import sqlite3
from sqlite3 import Error
from pprint import pprint


### globale Variablen
utc=pytz.UTC
#utc = pytz.timezone("GMT")
nccal = "/remote.php/dav/calendars/batch/aktivesenioren_shared_by_Admin/"
nccalint = "/remote.php/dav/calendars/batch/aktivesenioren-intern_shared_by_Admin/"
    
targetdir = "Aktive Senioren/Listen/"

ncserver = "cloud.wixhausen.org"
calurl = "https://" + ncserver  + "/remote.php/dav/calendars/batch"

tmj = "%d.%m.%Y"
hm = "%H:%M"
desckey = "description"
inmemory = ":memory:"
local_db = "ASW_Kalender.db"
heute = utc.localize(datetime.today())
J = heute.strftime("%D")
M = heute.strftime("%M")
von_datum = heute
bis_datum = von_datum + timedelta(days = 90)                                                        


sql_create_tab = """
        CREATE TABLE IF NOT EXISTS KALENDER (
        TERMIN TEXT NOT NULL,
        BEGINN TEXT NOT NULL,
        ENDE TEXT,        
        ORT TEXT DEFAULT "Saal",
        BESCHREIBUNG TEXT,
        INTEXT TEXT DEFAULT "",
        PRIMARY KEY (BEGINN, ENDE, TERMIN)
        );
        """
sql_insert = """
        INSERT OR REPLACE INTO KALENDER (TERMIN, BEGINN, ENDE, ORT, BESCHREIBUNG, INTEXT)
        VALUES (?, ?, ?, ?, ?, ?);
    """


### Funktonen
def adapt_date_iso(val):
    """Adapt datetime.date to ISO 8601 date."""
    return val.isoformat()

def adapt_datetime_iso(val):
    """Adapt datetime.datetime to timezone-naive ISO 8601 date."""
    return val.isoformat()

def adapt_datetime_epoch(val):
    """Adapt datetime.datetime to Unix timestamp."""
    return int(val.timestamp())

sqlite3.register_adapter(date, adapt_date_iso)
sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_adapter(datetime, adapt_datetime_epoch)

def convert_date(val):
    """Convert ISO 8601 date to datetime.date object."""
    return datetime.date.fromisoformat(val.decode())

def convert_datetime(val):
    """Convert ISO 8601 datetime to datetime.datetime object."""
    return datetime.datetime.fromisoformat(val.decode())

def convert_timestamp(val):
    """Convert Unix epoch timestamp to datetime.datetime object."""
    return datetime.datetime.fromtimestamp(int(val))

sqlite3.register_converter("date", convert_date)
sqlite3.register_converter("datetime", convert_datetime)
sqlite3.register_converter("timestamp", convert_timestamp)

def utc2cet(utc):
    if str(type(utc)) == "<class 'datetime.datetime'>":
        cet = utc.astimezone(pytz.timezone("Europe/Berlin")).strftime('%Y-%m-%d %H:%M:%S %Z%z')
    else:    
        cet = utc
    return cet
    
def connect_db(db_file):
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn

def select_termine(conn, sql):
    """
    Query all rows in the tasks table
    :param conn: the Connection object
    :return:
    """
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    return rows

def execute_sql(conn, sql):
    """
    Einmaliges ausführen eines SQL Befeehls
    Beispiel create Table etc
    :return:
    """
    cur = conn.cursor()
    cur.execute(sql)
    return
    
def insert_sql(conn, sql, werte):
    cur = conn.cursor()
    cur.execute(sql, werte)
    return
    
def get_calendar(cal):
    events = cal.search(
        start=von_datum, end=bis_datum, event=True, expand=True)
    return events
    
def prepare_event(event):
    event.expand_rrule(von_datum, bis_datum)
    try:
        e = event.instance.vevent
    except:
        print("Fehler bei event.instance.vevent", len(event), event)
        return "Fehler"
    else:
        d = e.__dict__["contents"]
    ##pprint(d)
    termin = e.summary.value
    # prüfen ob date oder datetime
    if str(type(e.dtstart.value)) == "<class 'datetime.date'>":
        beginn = e.dtstart.value.strftime('%Y-%m-%d')
    else:
        beginn = utc2cet(e.dtstart.value)
    if str(type(e.dtend.value)) == "<class 'datetime.date'>":
        ende = None
    else:
        ende = utc2cet(e.dtend.value)
    if "location" in d:
        ort = e.location.value
        if termin == "Gud Stubb geöffnet":
            ort = "Gud Stubb"
    else:
        ort = "Begegnungsstätte"
    if termin[:4] == "Kino":
        ort = "Saal"
    # gibt es eine Beschreibung
    if desckey in d:
        beschreibung = e.description.value
    else:
        beschreibung = None
        
    return (termin, beginn, ende, ort, beschreibung)


### Main
if __name__ == "__main__":
    # in Memory SQLite3 DB erzeugen
    #sqldb = connect_db(inmemory)
    sqldb = connect_db(local_db)
    # Tabelle löschen
    execute_sql(sqldb, "DROP TABLE KALENDER;")
    sqldb.commit()
    execute_sql(sqldb, sql_create_tab)
    sqldb.commit()
    # zu NC verbinden
    client = caldav.DAVClient(calurl)
    principal = client.principal()
    calendars = principal.calendars()


# Zeitraum anzeigen
print("Zeitraum:", von_datum.strftime(tmj), "-", bis_datum.strftime(tmj))
print()
    
# zu NC verbinden
extern = client.calendar(url="https://cloud.wixhausen.org:443/remote.php/dav/calendars/batch/aktivesenioren_shared_by_Admin/")
intern = client.calendar(url="https://cloud.wixhausen.org:443/remote.php/dav/calendars/batch/aktivesenioren-intern_shared_by_Admin/")

# externen Kalender einlesen
events = get_calendar(extern)
for event in events:
    values = prepare_event(event)
    if values != "Fehler":
        sql_value = values + ("",)
        insert_sql(sqldb, sql_insert, sql_value)
    else:
        print("Fehler aus prepare_event", values, event)
sqldb.commit()
    
# Internen Kalender einlesen
events = get_calendar(intern)
for event in events:
    values = prepare_event(event)
    if values != "Fehler":
        sql_value = values + ("Intern",)
        insert_sql(sqldb, sql_insert, sql_value)
sqldb.commit()
   
# Sichere Db lokal
sqldb.commit()
#local_db = 'ASW-Kalender.db'
#dbbackup = sqlite3.connect(local_db)
#sqldb.backup(dbbackup)
#nc.put_file(targetdir + local_db, local_db)

#dbbackup.close() 
sqldb.close()
print("done")
exit()
