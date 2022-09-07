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
              choices=[('L','L'), ('M','M'), ('H','H')])

    sexyTime = BooleanField('Sexy Time')

    submit = SubmitField('Enter Data')

#This will be called by a button. It will not follow the
# FlaskForm class as it will probably be done by hijacking
# the form date field and some ajax call.
@app.route('/checkDateForData', methods=['POST'])
def checkDateForData():
    result = db.checkForDataForDate('2022-08-30')

    if result == None:
        return None
    elif len(result) > 1:
        return {'error': 'Multiple Records found'}
    else:
        return dbToJson(result[0]) #Only pass the single record

#This is the main and only page. This will load a modal to
# get user input. Modal should be disabled when page is
#loaded and data is present for the day. Use route above.
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def home():
    form = cycleInputForm()

    if form.validate_on_submit():
        return render_template('index.html', form=form)
    return render_template('index.html', form=form)


def dbToJson(obj):
    print(obj)
    toReturn = {'date': obj[0],
                'monitor': obj[1],
                'sexyTime': obj[2],
                'rOrG': obj[3]
                }
    return toReturn

if __name__ == '__main__':
  app.run(debug = True, port=5001)
