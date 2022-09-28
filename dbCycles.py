import sqlite3
from sqlite3 import Error
import datetime
import random


class cycleDBClass():
    def __init__(self):
        self.db = r'cyclesDB.db'
        self.conn = None
        self.cur = None

    def openConnection(self):
        try:
            self.conn = sqlite3.connect(self.db)
        except Error as e:
            print(e)

    def createCursor(self):
        try:
            self.cur = self.conn.cursor()
        except Error as e:
            print(e)

    def closeConnection(self):
        try:
            self.conn.close()
        except Error as e:
            print(e)

    def createTable(self):
        """
        Fields: Datetime, monitor, sexyTime, red(0) or green(1) day
        """
        self.openConnection()
        self.createCursor()

        sql = '''CREATE TABLE readings(
                 "id" INTEGER PRIMARY KEY,
                 "date" DATE,
                 "active" INTEGER,
                 "timestamp" DATE,
                 "monitor" INTEGER,
                 "sexyTime" INTEGER,
                 "rORg" INTEGER,
                 "newCycle" INTEGER
                 )'''
        try:
            self.cur.execute(sql)
            self.conn.commit()
        except Error as e:
            print(e)

        self.closeConnection()


    def addRecord(self, _date, _active, _ts, _monitor, _st, _rOrG, _cc):
        self.openConnection()
        self.createCursor()
        sql = '''INSERT INTO readings VALUES(NULL, ?, ?, ?, ?, ?, ?, ?)'''

        try:
            self.cur.execute(sql, (_date, _active, _ts, _monitor, _st, _rOrG, _cc) )
            self.conn.commit()
        except Error as e:
            print(e)

        self.closeConnection()


    def deactivateRecordForID(self, _id):
        self.openConnection()
        self.createCursor()
        sql = '''UPDATE readings SET active = 0 WHERE id = ?'''

        try:
            self.cur.execute(sql, (str(_id))  )
            self.conn.commit()
        except Error as e:
            print(e)

        self.closeConnection()


    def deactivateRecordsForDate(self, _date):
        self.openConnection()
        self.createCursor()
        sql = '''UPDATE readings SET active = 0 WHERE date = date(?)'''
        try:
            self.cur.execute(sql, (_date,) )
            self.conn.commit()
        except Error as e:
            print(e)
        except Warning as w:
            print(w)

        self.closeConnection()


    def getAllRecords(self):
        self.openConnection()
        self.createCursor()
        sql = "SELECT * FROM readings"
        try:
            self.cur.execute(sql)
            for row in self.cur:
                print(row)
        except Error as e:
            print(e)
        self.closeConnection()


    def checkForDataForDate(self, _date):
        """
        Checks for data on a given date. Returns data if found. None if no data.
        """
        self.openConnection()
        self.createCursor()
        sql = '''SELECT * FROM readings WHERE date = ? AND active = 1'''
        try:
            result = self.cur.execute(sql, (_date,) ).fetchall()
            return result
        except Error as e:
            print(e)
        self.closeConnection()


    def getActiveRecordsForDateRange(self, _dateNewest, _dateOldest):
        self.openConnection()
        self.createCursor()
        sql = '''SELECT * FROM readings WHERE active = 1 AND date BETWEEN ? AND ?'''
        try:
            result = self.cur.execute(sql, (_dateOldest, _dateNewest,) ).fetchall()
            return result
        except Error as e:
            print(e)
        self.closeConnection()


    def generateFakeData(self):
        baseVals = [2, 2, 3, 4,
                    3, 2, 3, 4,
                    7, 9, 7, 4,
                    3, 2, 3, 2]

        for cycCount in range(0, 3):

            for idx, d in enumerate(baseVals):
                var = d * random.uniform(1.0, 3.0)
                offset = idx + (cycCount * 16)
                dateTS = datetime.datetime.now()
                dateTS = dateTS - datetime.timedelta(days=offset)
                date = dateTS.strftime('%Y-%m-%d')

                r = {'recordDate': date,
                      'active': 1,
                      'timestamp': dateTS,
                      'monitor': int(var),
                      'st': random.randint(0, 1),
                      'rOrG': random.randint(0, 1),
                      'nc': 0 if (idx != 15) else 1}

                self.addRecord(r['recordDate'], r['active'],
                                r['timestamp'], r['monitor'],
                                r['st'], r['rOrG'], r['nc'])

    def getCycleDates(self, limit=-1):
        self.openConnection()
        self.createCursor()
        sql = '''SELECT date FROM readings WHERE newCycle == 1 LIMIT ?'''
        try:
            result = self.cur.execute(sql, (limit,)).fetchall()
            return result
        except Error as e:
            print(e)
        self.closeConnection()
        
                
if __name__ == '__main__':
    print('dbCycles.py')
    db = cycleDBClass()

    db.createTable()

    db.generateFakeData()

    db.getAllRecords()

    #date = '2022-09-19'
    #db.deactivateRecordsForDate(date)

    #db.getAllRecords()
    #print("\n")
    #print(db.getActiveRecordsForDateRange('2022-09-11', '2022-09-09'))

    #print(db.checkForDataForDate('2022-09-07'))
