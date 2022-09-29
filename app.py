from flask import Flask, render_template, request, flash, jsonify, make_response
from flask_wtf import FlaskForm
from wtforms import StringField, validators, SubmitField, IntegerField, SelectField, BooleanField
from wtforms.validators import DataRequired, InputRequired
from wtforms.fields import DateField

from sqlite3 import Error
import datetime

import pandas as pd
import numpy as np
import plotly.express as px

import dbCycles

app = Flask(__name__)
app.secret_key = 'development key'

db = dbCycles.cycleDBClass()

#Historic number of days default
hisNumDaysDefault = 30

class cycleInputForm(FlaskForm):
    todayDate = DateField('DatePicker', format='%Y-%m-%d')

    monitor = IntegerField('Monitor')

    sexyTime = BooleanField('Sexy Time')

    newCycle = BooleanField('New Cycle')

    rORg = BooleanField('Green Day')

    replaceData = BooleanField('Replace Existing Data')

    active = BooleanField('Delete Data')

    submit = SubmitField('Enter Data',
                         render_kw={'class': 'btn btn-primary'})


@app.route('/checkDateForData', methods=['POST'])
def checkDateForData():
    print('checkDateForData')
    currentDate = None
    if request.method == 'POST':
        currentDate = request.form['currentDate']

        result = db.checkForDataForDate(str(currentDate))

        if len(result) == 0:
            return {'data': False}
        elif len(result) > 1:
            return {'error': 'Multiple Records found'}
        else:
            #print(result[0])
            return dbToJson(result[0]) #Only pass the single record


#This is the main and only page. This will load a modal to
# get user input. Modal should be disabled when page is
# loaded and data is present for the day. Use route above.
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def home():
    form = cycleInputForm()
    errors = []
    msg = []
    historicData = getHistoricDataV2()

    if form.validate_on_submit():
        formDate = str(form.todayDate.data)

        #Check to see if data exists for the day
        dataForDayExists = False
        if len(db.checkForDataForDate(formDate)) >= 1:
            print('Data Exists for Day')
            dataForDayExists = True

        #Attempt to Delete Data
        if form.active.data == True:
            print('Delete Data')
            try:
                #Deactive old data
                deactivateDate(form)
                #Reload table
                historicData = getHistoricDataV2()
                msg.append( 'Data deleted for %s' % (formDate) )
            except Error as e:
                error = e

        #Attempt to replace data to DB
        elif form.replaceData.data == True:
            print('Replace Data')
            try:
                #Deactive old data
                deactivateDate(form)
                #Add new record
                addNewRecord(form)
                #Reload table
                historicData = getHistoricDataV2()
                msg.append( 'Data replaced for %s' % (formDate) )
            except Error as e:
                error = e

        #Attempt to add new data to DB
        elif form.replaceData.data != True:
            print('New Data')
            #Need to check for data on this day
            if dataForDayExists:
                print('Error - Data exists')
                errors.append('Data exists for this day - Select Replace Existing Data to overwrite.')
            else:
                try:
                    result = addNewRecord(form)
                    #Reload table
                    historicData = getHistoricDataV2()
                    msg.append( 'Data added for %s' % (formDate) )
                except Error as e:
                    error = e
        else:
            error = 'Replace Data Boolean in unknown state'

        return render_template('index.html', form=form,
                                             errors=errors,
                                             msg=msg,
                                             historicData=historicData)

    return render_template('index.html', form=form,
                                         errors=errors,
                                         msg=msg,
                                         historicData=historicData)


def addNewRecord(_form):
    db.addRecord( str(_form.todayDate.data), #Date
                  int(1), #Active
                  str(datetime.datetime.now()), #TimeStamp
                  str(_form.monitor.data), #Monitor
                  int(_form.sexyTime.data),
                  int(_form.rORg.data),
                  int(_form.newCycle.data))


def deactivateDate(_form):
    dateToDeactivate = str(_form.todayDate.data)
    db.deactivateRecordsForDate(dateToDeactivate)


def getHistoricData(datePresent=None, numDaysBack=7):
    dayPresent = getFormattedDate(datePresent)
    dayPast = getFormattedDate(shiftDays=numDaysBack)

    historyList = db.getActiveRecordsForDateRange(dayPresent, dayPast)

    title = ['ID', 'Record Date', 'Active', 'TimeStamp', 'Monitor', 'SexyTime',
             'Green Day', 'New Cycle']

    df = pd.DataFrame(historyList)
    df.columns = title

    df.sort_values('Record Date', inplace=True, ascending=False)

    df["SexyTime"] = np.where(df["SexyTime"] == 1, 'Yes', 'No')
    df["Red Or Green"] = np.where(df["Green Day"] == 1, 'Green', 'Red')
    df["New Cycle"] = np.where(df["New Cycle"] == 1, 'Yes', 'No')

    html = df.to_html(justify='left',
                      index=False,
                      classes='table table-striped table-bordered table-hover table-sm',
                      columns=['Record Date', 'Monitor', 'SexyTime',
                               'Green Day', 'New Cycle'])
    return html

#Looks at past data per cycles. First need to go back per cycle or number of
# days. Query DB: Select Date when active = 1. Then query each cycle per
# query. Add Plot.ly plot. This should be called from the front end?
def getHistoricDataV2(numOfCycles=3):

    #Fetch start date of cycles
    data = db.getCycleDates(numOfCycles)

    #https://stackoverflow.com/questions/10632839/transform-list-of-tuples-into-a-flat-list-or-a-matrix
    startDateList = list(sum(data, ()))

    #Add today's date to list. Reverse to start with most recent
    startDateList.append( getFormattedDate() )
    startDateList.reverse()

    #Create empty list to store each DF. Each DF is a cycle
    dfs = []

    #Loop through start dates except last date
    for idx,startDate in enumerate(startDateList[:-1]):
        endDate = startDateList[idx+1]

        rawDataList = db.getActiveRecordsForDateRange(startDate, endDate)

        title = ['ID', 'Record Date', 'Active', 'TimeStamp', 'Monitor', 'SexyTime',
                 'Green Day', 'New Cycle']

        tempDF = pd.DataFrame(rawDataList)
        tempDF.columns = title

        tempDF.sort_values('Record Date', inplace=True, ascending=False)

        #Need to remove row 1 if idx > 1

        #dfs.append(tempDF)

        #Create figures
        fig = px.line(tempDF, x='Record Date', y='Monitor', markers=True)
        #Format date and center point
        fig.update_xaxes(tickformat='%Y-%m-%d', ticklabelmode='period')

        dfs.append(fig.to_html(include_plotlyjs='cdn', full_html=False))

    return dfs


def getFormattedDate(_date=None, shiftDays=0):
    formatString = "%Y-%m-%d"
    if _date == None:
        _date = datetime.datetime.now()
    else:
        _date = datetime.strptime(_date, formatString)
    _date = _date - datetime.timedelta(days=shiftDays)

    return _date.strftime(formatString)

def dbToJson(obj):
    toReturn = {'id': obj[0],
                'date': obj[1],
                'active': obj[2],
                'timestamp': obj[3],
                'monitor': obj[4],
                'sexyTime': obj[5],
                'rORg': obj[6],
                'newCycle': obj[7],
                'data': True
                }
    return toReturn

if __name__ == '__main__':
  app.run(debug = True, port=5001)
