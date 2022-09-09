from flask import Flask, render_template, request, flash, jsonify, make_response
from flask_wtf import FlaskForm
from wtforms import StringField, validators, SubmitField, IntegerField, SelectField, BooleanField
from wtforms.validators import DataRequired, InputRequired
from wtforms.fields import DateField
import dbCycles

app = Flask(__name__)
app.secret_key = 'development key'

db = dbCycles.cycleDBClass()

class cycleInputForm(FlaskForm):
    todayDate = DateField('DatePicker', format='%Y-%m-%d')

    monitor = SelectField('Monitor',
              choices=[('LH','LH'), ('ES','ES')])

    sexyTime = BooleanField('Sexy Time')

    newCycle = BooleanField('New Cycle')

    replaceData = BooleanField('Replace Existing Data')

    submit = SubmitField('Enter Data')


@app.route('/checkDateForData', methods=['POST'])
def checkDateForData():
    print('checkDateForData')
    currentDate = None
    if request.method == 'POST':
        currentDate = request.form['currentDate']

        result = db.checkForDataForDate(str(todayDate))

        if len(result) == 0:
            return {'data': False}
        elif len(result) > 1:
            return {'error': 'Multiple Records found'}
        else:
            return dbToJson(result[0]) #Only pass the single record

#This is the main and only page. This will load a modal to
# get user input. Modal should be disabled when page is
# loaded and data is present for the day. Use route above.
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def home():
    form = cycleInputForm()

    if form.validate_on_submit():
        formDate = str(form.todayDate.value)
        error = False

        #Check to see if data exists for the day
        dataForDayExists = False
        if db.checkForDataForDate(formDate) == 0:
            dataForDayExists = True

        #Attempt to replace data to DB
        if form.replaceData.value == True:
            try:
                #Deactive old data
                result = deactivateDate(form)
                #Add new record
                result = addNewRecord(form)
            except Error as e:
                error = e

        #Attempt to add new data to DB
        elif form.replaceData.value != True:
            #Need to check for data on this day
            try:
                result = addNewRecord(form)
            except Error as e:
                error = e
        else:
            error = 'Replace Data Boolean in unknown state'

        #Need to pass errors below - Look at blocks setup
        return render_template('index.html', form=form)
    return render_template('index.html', form=form)

def addNewRecord(_form):
    #db.addRecord('2022-09-07', 1, str(datetime.datetime.now()), 'LH', 0, 'G', 12)
    pass

def deactivateDate(_form):
    db.deactivateRecordsForDate(formDate)



def dbToJson(obj):
    print(obj)
    toReturn = {'date': obj[0],
                'monitor': obj[1],
                'sexyTime': obj[2],
                'rOrG': obj[3],
                'data': True
                }
    return toReturn

if __name__ == '__main__':
  app.run(debug = True, port=5001)
