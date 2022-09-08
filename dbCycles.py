import sqlite3
from sqlite3 import Error
import datetime


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
        Fields: Datetime, monitor, sexyTime, red or green day
        """
        self.openConnection()
        self.createCursor()

        sql = '''CREATE TABLE readings(
                 "id" INTEGER PRIMARY KEY,
                 "date" DATE,
                 "active" INTEGER,
                 "timestamp" DATE,
                 "monitor" TEXT,
                 "sexyTime" INTEGER,
                 "rORg" INTEGER,
                 "cycleCount" INTEGER
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
        sql = '''SELECT * FROM readings WHERE date = ? '''
        try:
            result = self.cur.execute(sql, (_date,) ).fetchall()
            return result
        except Error as e:
            print(e)
        self.closeConnection()


if __name__ == '__main__':
    db = cycleDBClass()

    db.createTable()

    db.addRecord('2022-09-07', 1, str(datetime.datetime.now()), 'LH', 0, 'G', 12)

    db.getAllRecords()

    #print(db.checkForDataForDate('2022-09-07'))
