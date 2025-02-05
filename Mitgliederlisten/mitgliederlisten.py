#!/home/friedmar/.pyenv/bin/python
# -*- coding: utf-8 -*-
import sys
import netrc
import time
import datetime
from fpdf import FPDF
import requests
import vobject
import sqlite3
from sqlite3 import Error
import nextcloud_client


# globale Variablen
ncserver = "https://cloud.wixhausen.org"
nccard = "/remote.php/dav/addressbooks/users/batch/aktive-senioren_shared_by_Admin/?export"
targetdir = "Aktive Senioren/Listen/"
cardurl = ncserver + nccard
#username = 'batch'
#password = '64291Wixhausen'
aswx_logo = 'aktive-senioren.logo.jpg'
monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
PL = "x"


class PDF(FPDF):    

    # Page header
    def header(self):
        # Logo
        if self.w > self.h: 
            self.image(aswx_logo, x=260, y=10, w=20)
        else:
            self.image(aswx_logo, x=170, y=10, w=20)
        # Helvetica bold 15
        self.set_font('Helvetica', 'B', 15)
        # Title
        self.set_xy(60, 20)
        
        # Move to the right
        #self.cell(w=60)
        self.cell(text=report_title + ' per ' + printtime, new_x="LMARGIN", new_y="NEXT", align="C")
        # Line break
        self.ln(15)
        # Separation line
        if self.w > self.h:
            self.line(x1=20, y1=35, x2=300-20, y2=35)
        else:
            self.line(x1=30, y1=35, x2=210-20, y2=35)        
            
        
    # Page footer
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Separation line30
        if self.w > self.h:
            self.line(20, 195 , 300-20, 195)
        else:
            self.line(20, 280 , 210-20, 280)
        # Helvetica italic 8
        self.set_font('Helvetica', 'I', 10)
        # Page number
        self.cell(0, 10, 'Seite ' + str(self.page_no()) + '/{nb}', 0, new_x="LMARGIN", new_y="NEXT", align="C")



if __name__ == '__main__':
    # in Memory SQLite3 DB erzeugen
    dbvcf = sqlite3.connect(':memory:', timeout=10)
    dbcur = dbvcf.cursor()

    dbcur.execute('''
        CREATE TABLE IF NOT EXISTS mitglieder (
        name TEXT NOT NULL UNIQUE PRIMARY KEY,
        vorname TEXT NOT NULL,
        famname TEXT NOT NULL,
        geburtstag DATE NOT NULL,
        strasse TEXT NOT NULL,
        plz TEXT NOT NULL,
        ort TEXT NOT NULL,
        telefon TEXT,
        mobil TEXT,
        email TEXT,
        mm INTEGER,
        dd INTEGER
        );
        ''')

    dbvcf.commit()
    

# open connection to nextcloud_client
# get user and password from .netrc
netrc = netrc.netrc()
remoteHostName = "cloud.wixhausen.org"
authTokens = netrc.authenticators(remoteHostName)
username = authTokens[0]
password = authTokens[2]
nc = nextcloud_client.Client(ncserver)
nc.login(username, password)

# VCF Datei lesen und in SQLite3 Tabelle schreiben
vcfcards = requests.get(cardurl, auth=(username, password)).content
vcardlist = vobject.readComponents(vcfcards.decode())
for vcard in vcardlist:
    vollername = vcard.fn.value
    try:
        name = vcard.getChildValue('n').family
    except:
        name = 'Name'
    try:
        vorname = vcard.getChildValue('n').given
    except:
        vorname = 'Vorname'
    #telefon = vcard.tel.value
    try:
        telefon = vcard.getChildValue('tel', default = None, childNumber = 0)
    except:
        telefon = ''
    try:
        mobil = vcard.getChildValue('tel', default = None, childNumber = 1)
    except:
        mobil = ''
    try:
        adresse = vcard.adr.value
    except:
        adresse = ' '
    try:    
        strasse = vcard.getChildValue('adr').street
    except:
        strasse = ''
    try:
        ort = vcard.getChildValue('adr').city
    except:
        ort = ''
    try:
        plz = vcard.getChildValue('adr').code
    except:
        plz = ''
    ymd = vcard.bday.value
    dd = ymd[6:]
    mm = ymd[4:6]
    yy = ymd[:4]
    geburtstag = dd + '.' + mm + '.' + yy
    try:
        email = vcard.email.value
    except:
        email = ''

    insert_values = (mm, dd, vollername, vorname, name, geburtstag, strasse, plz, ort, telefon, mobil, email)
    insert_sql = '''
        INSERT INTO mitglieder (mm, dd, name, vorname, famname, geburtstag, strasse, plz, ort, telefon, mobil, email)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    '''
    dbcur.execute(insert_sql, insert_values)

dbvcf.commit()


# Creating an empty Dataframe with column names only
#cols = ['Mitglied', 'Nachname', 'Vorname', 'Geburtstag', 'Stadt', 'Straße', 'Telefon', 'Mobil', 'Email', 'mm', 'tt']
#Mitglieder = pd.DataFrame(columns=cols)


""" Erstelle Mitgliederliste aus SQLite3 DB """
pdf_file = 'mitgliederliste.pdf'
report_title = 'Mitgliederliste'
now = datetime.datetime.now()
printtime = now.strftime("%d.%m.%Y %H:%M")
PL = 'L'
pdf = PDF('L', 'mm', 'A4')
pdf.alias_nb_pages()
pdf.set_margins(left = 20, top = 25, right = 20)
pdf.add_page()
# SELECT zum auslesen der Mitglieder
select_cmd = '''
    select name, vorname, famname, geburtstag, strasse, plz, ort, telefon, mobil, email
    from mitglieder	
    order by famname, vorname
'''

# run a SELECT statement - no data in there, but we can try it
dbcur.execute(select_cmd)
rows = dbcur.fetchall()

for row in rows :
    # Ausgabefelder erstellen
    name=row[0]
    stadt=row[5] + " " + row[6]
    strasse = row[4]
    geburtstag = row[3]
    telefon = row[7]
    mobil = row[8]
    email = row[9]
    #print detail line
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(40, 0, name, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(50, 0, stadt, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(45, 0, strasse, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(20, 0, geburtstag, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(30, 0, telefon, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(30, 0, mobil, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(60, 0, email, 0, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(h=5)
    
pdf.output(name=pdf_file)

nc.put_file(targetdir + pdf_file, pdf_file)


""" Erstelle Mitgliederliste ohne Mail aus SQLite3 DB """
pdf_file = 'mitgliederohnemail.pdf'
report_title = 'Mitglieder ohne Mail'
now = datetime.datetime.now()
printtime = now.strftime("%d.%m.%Y %H:%M")

pdf = PDF('L', 'mm', 'A4')
PL = 'L'
pdf.alias_nb_pages()
pdf.set_margins(left = 20, top = 25, right = 20)
pdf.add_page()

# SELECT zum auslesen der Mitglieder
select_cmd = '''
    select name, vorname, famname, geburtstag, strasse, plz, ort, telefon, mobil
    from mitglieder	
    where email = "" or email = " "
    order by famname, vorname
'''

# run a SELECT statement - no data in there, but we can try it
dbcur.execute(select_cmd)
rows = dbcur.fetchall()

for row in rows :
    # Ausgabefelder erstellen
    name=row[0]
    stadt=row[5] + " " + row[6]
    strasse = row[4]
    geburtstag = row[3]
    telefon = row[7]
    mobil = row[8]
    email = " "
    #print detail line
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(40, 0, name, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(50, 0, stadt, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(45, 0, strasse, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(20, 0, geburtstag, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(30, 0, telefon, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(30, 0, mobil, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(60, 0, email, 0, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(h=5)

pdf.output(name=pdf_file)

nc.put_file(targetdir + pdf_file, pdf_file)


""" Erstelle Telefonliste aus SQLite3 DB """
pdf_file = 'telefonliste.pdf'
report_title = 'Telefonlisteliste'
now = datetime.datetime.now()
printtime = now.strftime("%d.%m.%Y %H:%M")

pdf = PDF('P', 'mm', 'A4')
PL = 'P'
pdf.alias_nb_pages()
pdf.set_margins(left = 30, top = 25, right = 20)
pdf.add_page()

# SELECT zum auslesen der Mitglieder
select_cmd = '''
    select name, telefon, mobil, email
    from mitglieder	
    order by famname, vorname
'''

# run a SELECT statement - no data in there, but we can try it
dbcur.execute(select_cmd)
rows = dbcur.fetchall()

for row in rows :
    # Ausgabefelder erstellen
    name=row[0]
    telefon = row[1]
    mobil = row[2]
    email = row[3]
    #print detail line
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(50, 0, name, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(30, 0, telefon, 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(30, 0, mobil,  0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(60, 0, email, 0, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(h=5)

pdf.output(name=pdf_file)

nc.put_file(targetdir + pdf_file, pdf_file)


""" Erstelle Geburtstagsliste aus SQLite3 DB """
pdf_file = 'geburtstagsliste.pdf'
report_title = 'Geburtstagsliste'
now = datetime.datetime.now()
printtime = now.strftime("%d.%m.%Y %H:%M")

seitenwechsel = 'Juli'
vormonat="leer"
geburtstage_im_monat=0

pdf = PDF('P', 'mm', 'A4')
PL = 'P'
pdf.alias_nb_pages()
pdf.set_margins(left = 30, top = 25, right = 20)
pdf.add_page()

# SELECT zum auslesen der Mitglieder
select_cmd = '''
    select name, geburtstag, telefon, mobil, email, mm
    from mitglieder	
    order by mm, dd, famname, vorname
'''

# run a SELECT statement - no data in there, but we can try it
dbcur.execute(select_cmd)
rows = dbcur.fetchall()

for row in rows :
    # Ausgabefelder erstellen
    name = row[0]
    geburtstag = row[1]
    telefon = row[2]
    mobil = row[3]
    email = row[4]
    mm = row[5]
    monat = monate[int(mm)-1]
    # month changed
    if monat != vormonat:
        #if vormonat != 'leer':
            #pdf.set_font('Helvetica', 'I', 12)
            #pdf.cell(0, 10, "Geburtstage im Monat " + vormonat + str(geburtstage_im_monat), 0, 1)
        vormonat=monat
        geburtstage_im_monat=1
        if vormonat == seitenwechsel:
            pdf.add_page()
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 10, monat, 0, new_x="LMARGIN", new_y="NEXT", align="L")
    else:
        geburtstage_im_monat = geburtstage_im_monat + 1
    #print detail line
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(25, 0, geburtstag , 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(50, 0, name , 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(40, 0, telefon , 0, new_x="RIGHT", new_y="TOP" ,align="L")
    pdf.cell(40, 0, mobil , 0, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(h=5)

#pdf.cell(0, 10, "Geburtstage im Monat " + vormonat + str(geburtstage_im_monat), 0, 1)    
pdf.output(name=pdf_file)

nc.put_file(targetdir + pdf_file, pdf_file)


# Sichere Db lokal
local_db = 'mitglieder.db'
dbbackup = sqlite3.connect(local_db)
dbvcf.backup(dbbackup)
nc.put_file(targetdir + local_db, local_db)

dbbackup.close() 
dbvcf.close()
exit()
