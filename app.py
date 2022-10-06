from flask import Flask, render_template, request, flash, jsonify, make_response
from flask_wtf import FlaskForm
from wtforms import StringField, validators, SubmitField, IntegerField, SelectField, BooleanField
from wtforms.validators import DataRequired, InputRequired
from wtforms.fields import DateField

from sqlite3 import Error
import datetime

import pandas as pd
import numpy as np
import plotly.graph_objects as go

import dbCycles

#Look at deployment vs development: https://flask.palletsprojects.com/en/2.2.x/config/
# Idea would be to load proper database and maybe logins.
# Would need to remember to set to deploy
# Or keep two directories (dev and prod). Use enviro export ... won't work
# those are system wide.
app = Flask(__name__)
app.secret_key = 'development key'

db = dbCycles.cycleDBClass()

#Historic number of days default
hisNumDaysDefault = 30

class cycleInputForm(FlaskForm):
    todayDate = DateField('DatePicker', format='%Y-%m-%d')

    monitor = StringField('Monitor')
    #Need to add check for LPH or number

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
                    msg.append( 'Data added for %s' % (formDate) )
                except Error as e:
                    error = e
        else:
            error = 'Replace Data Boolean in unknown state'

        return render_template('index.html', form=form,
                                             errors=errors,
                                             msg=msg,
                                             )

    return render_template('index.html', form=form,
                                         errors=errors,
                                         msg=msg,
                                         )


def addNewRecord(_form):
    db.addRecord( str(_form.todayDate.data), #Date
                  int(1), #Active
                  str(datetime.datetime.now()), #TimeStamp
                  (str(_form.monitor.data)).upper(), #Monitor
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


@app.route('/getCyclePlots', methods=['GET', 'POST'])
def getCyclePlots(numOfCycles=3):
    #Create list of dicts to store data
    cycleStats = []
    dfs = generateDFs(numOfCycles=numOfCycles)

    for df in dfs:
        startDate = df['Record Date'].iloc[-1]
        endDate = df['Record Date'].iloc[0]
        cycleDuration = len(df)

        div = generatePlot(df)

        cycleStats.append({'startDate': startDate,
                           'endDate': endDate,
                           'cycleDuration': cycleDuration,
                           'plot': div
                          })
    print(cycleStats)


def generateDFs(numOfCycles=3):
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

        #Add column with increasing integer to aid in plot later on
        tempIntList = np.arange(tempDF.shape[0])
        tempDF['Cycle Count'] = tempIntList[::-1]

        #Map LHP to numbers for easier plotting
        tempDF['Monitor'] = tempDF['Monitor'].map( {'L':0 , 'H':1, 'P':2} )

        dfs.append(tempDF)
    return dfs

def generatePlot(df):
    fig = go.Figure()

    #Add Cycle Count. Annotations using df is not supported
    dates = df['Record Date'].tolist()
    text = df['Cycle Count'].tolist()
    for i in range(len(dates)):
        fig.add_annotation(x=dates[i], y=0,
                text=text[i],
                showarrow=False,
                arrowhead=1,
                yshift=12)

    #Add Red/Green rectangles. DFs not supported.
    color = df['Green Day'].tolist()
    for i in range(len(dates)):
        startRect = datetime.datetime.strptime(dates[i], '%Y-%m-%d')
        startRect = startRect - datetime.timedelta(days=0.5)
        startRect = startRect.strftime('%Y-%m-%d %H:%M')

        endRect = datetime.datetime.strptime(dates[i], '%Y-%m-%d')
        endRect = endRect + datetime.timedelta(days=0.5)
        endRect = endRect.strftime('%Y-%m-%d %H:%M')


        fig.add_vline(x=startRect, line_width=1, line_dash="dash", line_color="black", opacity=0.8)
        fig.add_vline(x=endRect, line_width=1, line_dash="dash", line_color="black", opacity=0.8)

        if color[i] == 0:
            fig.add_vrect(x0=startRect, x1=endRect, line_width=0, fillcolor="red", opacity=0.1)
        else:
            fig.add_vrect(x0=startRect, x1=endRect, line_width=0, fillcolor="green", opacity=0.1)


    fig.add_trace(go.Scatter(x=df['Record Date'],
                             y=df['Monitor'],
                             mode='lines+markers',
                             line_color='black'))


    fig.update_xaxes(
        tickformat='%m/%d',
        tickangle = 90,
        dtick=86400000, #dticks is in milliseconds
        ticks='outside',
        tickson='boundaries')

    fig.update_yaxes(
        nticks=3,
        showticklabels=True,
        ticktext=['L', 'H', 'P'],
        tickvals=[0, 1, 2]
    )

    return fig.to_html(include_plotlyjs='cdn', full_html=False)


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
