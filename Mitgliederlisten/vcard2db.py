#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import netrc
import time
import datetime
import requests
import vobject
#import sqlite3
import ibm_db
#from sqlite3 import Error
import nextcloud_client


# globale Variablen
ncserver = "https://cloud.wixhausen.org"
nccard = "/remote.php/dav/addressbooks/users/batch/aktive-senioren_shared_by_Admin/?export"
cardurl = ncserver + nccard

connect2db = "DATABASE=MYDB;hostname=192.168.5.1;PORT=50291;PROTOCOL=TCPIP;UID=db2inst1;PWD=N8Falter!;"

def do_msg(msg_typ, msg_text):
    """ Meldungen ausgeben """
    now = datetime.datetime.now()
    print(msg_typ, now.strftime("%d.%m.%M %H:%M:%S"), msg_text)


if __name__ == '__main__':
    """ einlesen der VCard für Active Senioren und Abgleich mit Db2 """
    pass

# open connection to nextcloud_client
# get user and password from .netrc
netrc = netrc.netrc()
remoteHostName = "cloud.wixhausen.org"
authTokens = netrc.authenticators(remoteHostName)
username = authTokens[0]
password = authTokens[2]
nc = nextcloud_client.Client(ncserver)
nc.login(username, password)

# Verbindung zu Db2 herstellen
do_msg('Info', 'Connect Db2')
try:
    connected = ibm_db.connect(connect2db, "", "")
except:
    do_msg('Error', 'no connection' + ibm_db.conn_errormsg())
    sys.exit(4)
    
# VCF Datei lesen 
vcfcards = requests.get(cardurl, auth=(username, password)).content
vcardlist = vobject.readComponents(vcfcards.decode())
do_msg('Info', 'VCard lesen')
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
    adresse = vcard.adr.value
    #print(adresse)
    strasse = vcard.getChildValue('adr').street
    ort = vcard.getChildValue('adr').city
    plz = vcard.getChildValue('adr').code
    try:
        ymd = vcard.bday.value
    except:
        ymd = '20000101'
    dd = ymd[6:]
    mm = ymd[4:6]
    yy = ymd[:4]
    if ymd == '20000101':
        geburtstag = 'Fehlt'
    else:
        geburtstag = dd + '.' + mm + '.' + yy
    try:
        email = vcard.email.value
    except:
        email = ''

    # hole Daten von Db2
    sql_select = """
                SELECT * FROM ASWX.MITGLIEDER WHERE NAME = ? AND GEBURTSTAG = ?
                """                
    stmt = ibm_db.prepare(connected, sql_select)
    values = name, geburtstag
    ##do_msg('Debug', values)
    try:
        ibm_db.execute(stmt, values)
    except:
        do_msg('Error', 'Select: ' + name + ' ' + geburtstag)
        sys.exit(4)
    else:
        result = ibm_db.fetch_assoc(stmt)
        ##do_msg('Debug', str(result['ID']) + ' ' + result['NAME'])
    
    if result:
        ##do_msg('Debug', result)
        # Exists check if update is necessary
        if telefon != result['TELEFON']:
            sql_update = "UPDATE ASWX.MITGLIEDER SET TELEFON = '" + telefon + "'" + \
                " WHERE ID = " + str(result['ID'])
            do_msg('Debug', sql_update)
            stmt = ibm_db.exec_immediate(connected, sql_update)
            do_msg('Debug', 'Telefon ' + str(ibm_db.num_rows(stmt)))
            
        if mobil == result['MOBIL']:
            # nothing to do
            pass
        else:
            if mobil == '' and result['MOBIL'] is None:
                # Null bzw. leer
                pass
            else:
                ##print(result['ID'], name, mobil, type(mobil), result['MOBIL'], type(result['MOBIL']))
                sql_update = "UPDATE ASWX.MITGLIEDER SET MOBIL = '" + mobil + "'" + \
                    " WHERE ID = " + str(result['ID'])
                do_msg('Debug', sql_update)
                stmt = ibm_db.exec_immediate(connected, sql_update)
                do_msg('Debug', 'Mobil ' + str(ibm_db.num_rows(stmt)))
                
        if email == result['EMAIL']:
            pass
        else:
            if email == '' and result['EMAIL'] is None:
                # Null bzw. leer
                pass
            else:
                sql_update = "UPDATE ASWX.MITGLIEDER SET EMAIL = '" + email + "'" + \
                    " WHERE ID = " + str(result['ID'])
                do_msg('Debug', sql_update)
                stmt = ibm_db.exec_immediate(connected, sql_update)
                do_msg('Debug', 'E-Mail ' + str(ibm_db.num_rows(stmt)))
            
        if plz == result['PLZ'] and ort == result['ORT'] and strasse == result['STRASSE']:
            pass
        else:
            sql_update = "UPDATE ASWX.MITGLIEDER SET PLZ = " + plz + ", ORT = '" + ort + "', STRASSE = '" + strasse + "'" +\
                " WHERE ID = " + str(result['ID'])
            do_msg('Debug', sql_update)
            stmt = ibm_db.exec_immediate(connected, sql_update)
            do_msg('Debug', 'E-Mail ' + str(ibm_db.num_rows(stmt)))
    else:
        # neues Mitglied
        sql_insert = """
            INSERT INTO ASWX.MITGLIEDER
                (VORNAME, NAME, GEBURTSTAG, PLZ, ORT, STRASSE, TELEFON, MOBIL, EMAIL)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        stmt = ibm_db.prepare(connected, sql_insert)
        values = vorname, name, geburtstag, plz, ort, strasse, telefon, mobil, email
        do_msg('Debug', sql_insert + str(values))
        try:
            ibm_db.execute(stmt, values)
        except:
            do_msg('Error', 'Insert: ' + vorname + ' ' + name + ' ' + geburtstag)
    
    
sys.exit(0)
