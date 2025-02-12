#!/home/friedmar/.pyenv/bin/python
# -*- coding: UTF-8 -*-

### Imports
import os
from datetime import date, datetime, timedelta, time
import pytz 
import netrc
import sqlite3
import psycopg2
from sqlite3 import Error
from fpdf import FPDF
import nextcloud_client


### globale Variablen
ncserver = "https://cloud.wixhausen.org"
targetdir = "Aktive Senioren/Listen/"
nc = nextcloud_client.Client(ncserver)

utc=pytz.UTC
sqlite3_db = "ASW_Kalender.db"
psql_conn = psycopg2.connect(database="wixhau_drupal",
                        host="hjq1.your-database.de",
                        user="wixhau_drupal",
                        password="aay4LzVg72xhba2s",
                        port="5432")
now = datetime.now()
aswx_logo = "aktive-senioren.logo.jpg"
kino_logo = "ASW_Kino_Logo.jpg"


sql_kino = """
           SELECT TERMIN, BEGINN, ENDE, ORT, BESCHREIBUNG
           FROM KALENDER
           WHERE TERMIN LIKE 'Kino%'
           ORDER BY substr(beginn,12,8), substr(beginn,1,10), ENDE, TERMIN, ORT
           """ 

sql_ext = """
           SELECT TERMIN, BEGINN, ENDE, ORT, BESCHREIBUNG
           FROM KALENDER
           WHERE INTEXT = ''
           ORDER BY STRFTIME('%H%M', BEGINN), STRFTIME('%Y%m%d', BEGINN), ENDE, TERMIN, ORT
           """ 

sql_full = """SELECT TERMIN, BEGINN, ENDE, ORT, BESCHREIBUNG 
           FROM KALENDER 
           ORDER BY BEGINN, ENDE, TERMIN, ORT"""

update_nexttermin = """ UPDATE ASWIX_NODE__BODY SET BODY_VALUE = %s
              WHERE ENTITY_ID = 769 """
              
update_nextterminr = """ UPDATE ASWIX_NODE_REVISION__BODY SET BODY_VALUE = %s
              WHERE ENTITY_ID = 769 """
              
update_nextkino = """ UPDATE ASWIX_NODE__BODY SET BODY_VALUE = %s
              WHERE ENTITY_ID = 713 """
htmp = "<p>"
htmpend = "</p>"
htmfett = "<strong>"
htmfettend = "</strong>"
htmhl = "<hr>"
Kinokopf = """<p>
<img src="/sites/default/files/users/user2/ASW_Kino_Logo.jpg" data-align="right" data-entity-uuid="5d7c4a59-502b-495f-a70e-2dbde78ceca7" data-entity-type="file" alt="" width="330" height="220">Wir freuen uns Filme für <strong>Jung und Alt</strong> bei den Aktiven Senioren in der Alten Schule (Ostendstr. 27-29 64291 Wixhausen) im Saal zu präsentieren - Eintritt frei.&nbsp;
</p>
<br>
<h2>Hier die nächsten Termine:</h2>
<br>
"""
    


### Class
class PDF(FPDF):    

    # Page header
    def header(self):
        # Arial bold 15
        self.set_font(family="DejaVuSans-Bold", size=15)
        # Move to the right
        ##self.cell(20)
        # Title
        if report_title == "Kino für Jung und Alt":
            self.cell(140, 10, report_title, new_x="LMARGIN", new_y="NEXT", align="C")
            self.cell(140, 10, report_title2, new_x="LMARGIN", new_y="NEXT", align="C")
            # Line break
            self.ln()
            # Separation line
            if self.w > self.h:
                self.line(x1=20, y1=35 , x2=300-20, y2=35)
            else:
                self.line(x1=20, y1=35 , x2=210-20, y2=35)
        else:
            self.cell(180, 10, report_title + report_title2, new_x="LMARGIN", new_y="NEXT", align="C")
            # Line break
            self.ln()
            # Separation line
            if self.w > self.h:
                self.line(x1=20, y1=25 , x2=300-20, y2=25)
            else:
                self.line(x1=20, y1=25 , x2=210-20, y2=25)        
        
    # Page footer
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Logo
        if self.w > self.h: 
            self.image(aswx_logo, x=260, y=270, w=20)
        else:
            self.image(aswx_logo, x=180, y=270, w=20)
        # Separation line30
        if self.w > self.h:
            self.line(x1=20, y1=195 , x2=300-35, y2=195)
        else:
            self.line(x1=20, y1=280 , x2=210-35, y2=280)
        # Arial italic 8
        self.set_font(family="helvetica", style="I", size=10)
        # Page number
        self.cell(text=printtime, align="L")
        self.cell(text="Seite " + str(self.page_no()) + "/{nb}", w=120, new_x="LMARGIN", new_y="NEXT", align="C")


### Functions
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
        print('SQLITE3 ERROR:', e)
    return conn

def select_rows(conn, sql):
    """
    Query all rows in the tasks table
    :param conn: the Connection object
    :return:
    """
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    return rows
 
def str2date(str):
    """
    Umwandel String Datum zu datetime
    """
    if type(str) == "<class 'str'>":
       return str
    if len(str) > 19:
        dt = datetime.strptime(str[0:18], "%Y-%m-%d %H:%M:%S")
    if len(str) == 19:
        dt = datetime.strptime(str, "%Y-%m-%d %H:%M:%S")
    if len(str) == 10:
        dt = datetime.strptime(str, "%Y-%m-%d")    
    return dt
    
def printKinoprogramm():
    """
    Drucke das Kinoprogramm
    """
    global report_title2
    pdf_datei = "Kinoprogramm.pdf"
    now = datetime.now()
    printtime = now.strftime("%d.%m.%Y %H:%M")
    htmlpage = Kinokopf

    # Vorbereitung PDF
    PL="P"
    pdf = PDF(PL, "mm", "A4")
    pdf.add_font(fname="font/DejaVuSans.ttf")
    pdf.add_font(fname="font/DejaVuSans-Bold.ttf")
    pdf.set_font("DejaVuSans", size=10)
    #pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_margins(left = 20, top = 10, right = 20)
    # Kino Logo
    pdf.image(kino_logo, x=140, y=10, w=60)
    pdf.ln()
    
    # hole die informationen zum Kinoprogramm
    rows = select_rows(dbcon, sql_kino)
    if len(rows) == 0:
        return None
    zeit = "1900"
    neue_seite = 0
    for row in rows:
        termin = row[0]
        beginn = str2date(row[1])
        if row[2] is not None:
            ende = str2date(row[2])
        ort = row[3]
        beschreibung = row[4]
        
        # Wechsel der Uhrzeit
        if beginn.strftime("%H%M") == zeit:
            # neue Uhreit
            ##zeit = beginn.strftime("%H%M")
            report_title2 = " am Abend"
            htmlpage = htmlpage + "<h2>Filme am Abend:</h2><br>"
            if neue_seite == 0:
                pdf.add_page()
                neue_seite = neue_seite + 1
        # Termin in Fett drucken, Linksbündig
        pdf.set_font(family="DejaVuSans-Bold", size=11)
        pdf.cell(text=termin, align="L")
        htmlpage = htmlpage + htmp + htmfett + termin + htmfettend
        # Rest Normal, Rechtsbündig
        pdf.set_font(family="DejaVuSans", size=10)
        anfang = beginn.strftime("%d.%m.%Y %H:%M h")
        pdf.cell(text=anfang, align="R", new_x="LMARGIN", new_y="NEXT")
        htmlpage = htmlpage + "    " + anfang + " - " + ort + htmpend
        pdf.ln()
        # Beschreibung Linksbündig, Breite 180
        ##print(termin, beschreibung)
        if beschreibung is None:
            beschreibung = "Beschreibung folgt"
        pdf.multi_cell(text=beschreibung, w=180, new_x="LMARGIN", new_y="NEXT", align="L")
        htmlpage = htmlpage + htmp + beschreibung + htmpend
        pdf.ln()
        htmlpage = htmlpage + htmhl
    
    pdf.output(pdf_datei)
    nc.put_file(targetdir + pdf_datei, pdf_datei)
    ##print(htmlpage)
    psql_cur = psql_conn.cursor()
    psql_cur.execute(update_nextkino, (htmlpage,))
    psql_conn.commit()
        
def printKommendeTermine():
    """
    Drucke kommende Termine
    """
    pdf_datei = "kommendeTermine.pdf"
    now = datetime.now()
    printtime = now.strftime("%d.%m.%Y %H:%M")
    htmlpage = ""

    # Vorbereitung PDF
    PL="P"
    pdf = PDF(PL, "mm", "A4")
    pdf.add_font(fname="font/DejaVuSans.ttf")
    pdf.add_font(fname="font/DejaVuSans-Bold.ttf")
    pdf.set_font("DejaVuSans", size=10)
    #pdf.alias_nb_pages()
    pdf.set_margins(left = 20, top = 10, right = 20)
    pdf.add_page()
    # hole die informationen zum Kinoprogramm
    rows = select_rows(dbcon, sql_ext)
    if len(rows) == 0:
        return None
    for row in rows:
        termin = row[0]
        beginn = str2date(row[1])
        if row[2] is not None:
            ende = str2date(row[2])
        ort = row[3]
        beschreibung = row[4]
        # Termin in Fett drucken, Linksbündig
        pdf.set_font(family="DejaVuSans-Bold", size=11)
        pdf.cell(text=termin, align="L")
        htmlpage = htmlpage + htmp + htmfett + termin + htmfettend
        # Rest Normal, Rechtsbündig
        pdf.set_font(family="DejaVuSans", size=10)
        anfang = beginn.strftime("%d.%m.%Y %H:%M h")
        pdf.cell(text=anfang, align="R", new_x="LMARGIN", new_y="NEXT")
        htmlpage = htmlpage + "  " + anfang + " - " + ort + htmpend+ htmp
        # Beschreibung Linksbündig, Breite 180
        if beschreibung is not None:
            pdf.multi_cell(text=beschreibung, w=180, new_x="LMARGIN", new_y="NEXT", align="L")
            htmlpage = htmlpage + htmp + beschreibung + htmpend
        pdf.ln()
        htmlpage = htmlpage + htmhl
    
    ##print(htmlpage)
    pdf.output(pdf_datei)
    nc.put_file(targetdir + pdf_datei, pdf_datei)
    psql_cur = psql_conn.cursor()
    psql_cur.execute(update_nexttermin, (htmlpage,))
    ##psql_cur.execute(update_nextterminr, (htmlpage,))
    psql_conn.commit()
    
def printTerminliste():
    """
    Drucke der Terminliste
    """
    pdf_datei = "Terminliste.pdf"
    now = datetime.now()
    printtime = now.strftime("%d.%m.%Y %H:%M")

    # Vorbereitung PDF
    PL="P"
    pdf = PDF(PL, "mm", "A4")
    pdf.add_font(fname="font/DejaVuSans.ttf")
    pdf.add_font(fname="font/DejaVuSans-Bold.ttf")
    pdf.set_font("DejaVuSans", size=10)
    #pdf.alias_nb_pages()
    pdf.set_margins(left = 20, top = 10, right = 20)
    pdf.add_page()
    # hole die informationen zum Kinoprogramm
    rows = select_rows(dbcon, sql_full)
    if len(rows) == 0:
        return None
    monat = "01"
    for row in rows:
        termin = row[0]
        beginn = str2date(row[1]) 
        if row[2] is not None:
            ende = str2date(row[2])
        ort = row[3]
       
        # Wechsel des Monats
        if beginn.strftime("%m") != monat:
            # neue Uhreit
            monat = beginn.strftime("%m")
            pdf.add_page()
        # Termin in Fett drucken, Linksbündig
        pdf.set_font(family="DejaVuSans", size=12)
        pdf.cell(text=termin, w=90, align="L")
        # Rest Normal
        #pdf.set_font(family="DejaVuSans", size=12)
        anfang = beginn.strftime("%d.%m.%Y %H:%M h")
        pdf.cell(text=anfang, w=44, align="L")
        pdf.cell(text=ort, w=30, align="L", new_x="LMARGIN", new_y="NEXT")
    
    pdf.output(pdf_datei)    
        

### Main
if __name__ == "__main__":
    # SQLite3 DB verbinden
    dbcon = connect_db(sqlite3_db)
    
    # open connection to nextcloud_client
    # get user and password from .netrc
    netrc = netrc.netrc()
    remoteHostName = "cloud.wixhausen.org"
    authTokens = netrc.authenticators(remoteHostName)
    username = authTokens[0]
    password = authTokens[2]
    nc = nextcloud_client.Client(ncserver)
    nc.login(username, password)

    # Termine holen
    report_title = "leer"
    report_title2 = ""
    printtime = now.strftime("%d.%m.%Y %H:%M")
    # Kinoprogramm
    report_title = "Kino für Jung und Alt"
    report_title2 = " am Nachmittag"
    printKinoprogramm()
    # Terminliste
    report_title = "Terminliste"
    report_title2 = ""
    printTerminliste()
    # Terminliste
    report_title = "kommende Termine"
    report_title2 = ""
    printKommendeTermine()
    
    # DB schließen
    dbcon.close()

exit()
