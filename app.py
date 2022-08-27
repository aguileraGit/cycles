from flask import Flask, render_template, request, flash, jsonify, make_response
from flask_wtf import FlaskForm
from wtforms import StringField, validators, SubmitField, IntegerField, SelectField, BooleanField
from wtforms.validators import DataRequired, InputRequired
from wtforms.fields import DateField

app = Flask(__name__)
app.secret_key = 'development key'

class cycleInputForm(FlaskForm):
    todayDate = DateField('DatePicker', format='%Y-%m-%d')

    monitor = SelectField('Monitor', choices=[('L','L'), ('M','M'), ('H','H')])

    sexyTime = BooleanField('Sexy Time')

    submit = SubmitField('Enter Data')

    #cycleCount


@app.route('/update', methods=['GET', 'POST'])
def update():
    """
    This function is used to update the DB
    """
    form = cycleInputForm()
    if form.validate_on_submit():
        return redirect('/success')
    return render_template('index.html', form=form)


def read():



if __name__ == '__main__':
  app.run(debug = True, port=5001)
