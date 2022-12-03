from flask import Flask, render_template, request, flash, jsonify, make_response, g
from flask_wtf import FlaskForm
from wtforms import StringField, validators, SubmitField, IntegerField, SelectField, BooleanField
from wtforms.validators import DataRequired, InputRequired
from wtforms.fields import DateField

from turbo_flask import Turbo

from sqlite3 import Error
import datetime

import pandas as pd
import numpy as np
import plotly.graph_objects as go

import dbCycles

import threading
import queue
import time
import random
import os
import uuid

from enum import Enum

class qObjType(Enum):
    PLOT = 1
    MSG = 2
    ERROR = 3

#Look at deployment vs development: https://flask.palletsprojects.com/en/2.2.x/config/
# Idea would be to load proper database and maybe logins.
# Would need to remember to set to deploy
# Or keep two directories (dev and prod). Use enviro export ... won't work
# those are system wide.
app = Flask(__name__)
app.secret_key = 'development key'

turbo = Turbo(app)
#Add to <head>: <!-- {{ turbo() }} -->
db = dbCycles.cycleDBClass()

dateListQueue = queue.Queue()


class cycleInputForm(FlaskForm):
    todayDate = DateField('DatePicker', format='%Y-%m-%d')

    monitor = SelectField('LPH', choices=[('L','L'), ('P','P'), ('H','H')])

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

    #Anytime main page is loaded, start generating plots
    initCycleDivs()

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

        #Add message & error to g.msg/g.error
        if len(msg) > 0:
            g.msg = msg

        if len(errors) > 0:
            g.error = errors

        #Update msgCenter
        turbo.push(turbo.append(render_template('msgCenter.html'), 'msgCenter'))


    return render_template('index.html', form=form,
                                         errors=errors,
                                         msg=msg)


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


def initCycleDivs(numOfCycles=3):
    #Fetch start date of cycles
    data = db.getCycleDates(numOfCycles)

    #https://stackoverflow.com/questions/10632839/transform-list-of-tuples-into-a-flat-list-or-a-matrix
    startDateList = list(sum(data, ()))

    #Add today's date to list. Reverse to start with most recent
    startDateList.append( getFormattedDate() )
    startDateList.reverse()

    #Loop through start dates except last date
    for idx,startDate in enumerate(startDateList[:-1]):
        endDate = startDateList[idx+1]

        #Push to queue
        dateListQueue.put( (qObjType.PLOT, (startDate, endDate)) )


def generateCycleDivs(df, img):
    startDate = df['Record Date'].iloc[-1]
    endDate = df['Record Date'].iloc[0]
    cycleDuration = len(df)

    g.startDate = startDate
    g.endDate = endDate
    g.cycleDuration = cycleDuration
    g.imgLocation = img


#Starts threading Fn before app starts
@app.before_first_request
def startBackgroundThread():
    threading.Thread(target=pushDataThread).start()


#Threaded loop. Waits for items to be put in the queue
# Used for plots.
def pushDataThread():
    with app.app_context():
        while True:
            if dateListQueue.empty():
                #print('Queue empty')
                time.sleep(0.2)
            else:
                #print('Items in queue')

                qObjTemp = dateListQueue.get()

                #Update the plots on the website
                if qObjTemp[0] == qObjType.PLOT:
                    #Get date from queue
                    dates = qObjTemp[1]
                    startDate = dates[0]
                    endDate = dates[1]

                    df = generateDF(startDate, endDate)

                    #Create image
                    img = generatePlot(df)

                    #Returns dict to app with context_processor
                    generateCycleDivs(df, img)

                    turbo.push(turbo.append(render_template('plotDiv.html'), 'historicData'))

                '''
                #Using this queue for messages and errors takes to long to process
                # when plots are being generated since they take a few seconds.
                # These messages are sent in the index function. Leaving the qObj cause
                # I'm too lazy to delete the work done.
                elif qObjTemp[0] == qObjType.MSG:
                    print('MSG sent to UI')
                    g.msg = qObjTemp[1]
                    print(qObjTemp[1])
                    turbo.push(turbo.append(render_template('msgCenter.html'), 'msgCenter'))

                elif qObjTemp[0] == qObjType.ERROR:
                    print('ERROR sent to UI')
                    g.error = qObjTemp[1]
                    print(qObjTemp[1])
                    turbo.push(turbo.append(render_template('msgCenter.html'), 'msgCenter'))
                '''



def generateDF(startDate, endDate):
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

    return tempDF


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

    #return fig.to_html(include_plotlyjs='cdn', full_html=False)
    _location = 'static/plots/' + str(uuid.uuid4()) + '.png'
    fig.write_image(_location)

    return _location


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
