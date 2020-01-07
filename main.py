# coding: utf-8
import glob
import os
from flask import Flask, render_template, redirect, flash, send_file, request
from config import Config
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, widgets, HiddenField
from wtforms.validators import DataRequired, Regexp, ValidationError
import oyaml as yaml
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import google_calculate
import pandas as pd
from pandas import ExcelWriter
import googlemaps

app = Flask(__name__, template_folder="templates")
app.config.from_object(Config)

scheduler = BackgroundScheduler()


def read_data(filename):
    data_file = filename
    with open(data_file, 'r') as f:
        data = yaml.safe_load(f)
    return data


def write_data(filename, data_to_write):
    data_file = filename
    with open(data_file, 'w') as f:
        yaml.dump(data_to_write, f)


def check_filename_exists_settings(form, field):
    data = read_data("data.yaml")
    filename_list = []
    for routes in data["routes"]:
        filename_list.append(routes[field.name])
    if field.data.lower() in filename_list:
        raise ValidationError('Filename already exists')


def check_filename_exists_data(form, field):
    files = [os.path.basename(i) for i in glob.glob("traffic_data/*.csv")]
    if field.data.lower() + ".csv" in files:
        raise ValidationError('The file: ' + field.data + '.csv already exists')


def check_apikey(form, field):
    try:
        now = datetime.datetime.now()
        token = field.data
        client = googlemaps.Client(key=token)
        client.distance_matrix("Amsterdam", "Utrecht", departure_time=now)
    except:
        raise ValidationError('This is not a working API Token')


class Dataform(FlaskForm):
    filename = StringField('Filename',
                           validators=[DataRequired(), check_filename_exists_settings, check_filename_exists_data,
                                       Regexp('^[A-Za-z0-9_-]+$',
                                              message="Filename must contain only letters numbers or underscore")],
                           render_kw={"placeholder": "Filename"})
    start = HiddenField('Startpoint', validators=[DataRequired(), Regexp('^[0-9\., ]+$',
                                                                         message="Not a valid coordinate")])
    end = HiddenField('Endpoint', validators=[DataRequired(), Regexp('^[0-9\., ]+$',
                                                                     message="Not a valid coordinate")])
    submit_data = SubmitField('Submit')


class ApiForm(FlaskForm):
    calculator_settings = read_data("settings.yaml")
    apitoken = StringField('API-Token', validators=[DataRequired(), check_apikey])
    submit_data = SubmitField('Submit')


class IntervalForm(FlaskForm):
    calculator_settings = read_data("settings.yaml")
    interval = IntegerField('Refresh Interval in minutes', widget=widgets.Input(input_type="number"),
                            validators=[DataRequired()])
    submit_data = SubmitField('Submit')


class RemoveRoutes(FlaskForm):
    remove_route = SubmitField('Delete')


class DownloadFiles(FlaskForm):
    download_file = SubmitField('Download')


class RemoveFiles(FlaskForm):
    remove_file = SubmitField('Delete')


@app.before_first_request
def start_init():
    interval_settings = read_data("settings.yaml")
    scheduler.add_job(func=google_calculate.google_maps_calculator,
                      trigger="interval", minutes=interval_settings["interval"][0],
                      id='job')
    scheduler.start()


@app.route('/', methods=['POST', 'GET'])
def index():
    form = Dataform()
    if form.validate_on_submit():
        now = datetime.datetime.now()
        time = now.strftime("%H:%M:%S - %d:%m:%Y")
        filename = form.filename.data
        start = form.start.data
        end = form.end.data

        data = read_data("data.yaml")
        total = {"time": time, "filename": filename.lower(), "start": start, "end": end}
        data["routes"].append(total)
        write_data("data.yaml", data)
        flash('Submit successful')
        return redirect("/")
    return render_template('index.html', form=form)


@app.route('/settings', methods=['POST', 'GET'])
def settings():
    apiform = ApiForm()
    intervalform = IntervalForm()
    removeroutes = RemoveRoutes()
    data = read_data("data.yaml")
    settings = read_data("settings.yaml")
    number_of_requests = round((60 / settings["interval"][0]) * 24 * len(data["routes"]))
    if apiform.validate_on_submit():
        settings["apitoken"][0] = apiform.apitoken.data
        write_data("settings.yaml", settings)
        flash('Api-Token changed successful')
        return redirect("/settings")
    if intervalform.validate_on_submit():
        settings["interval"][0] = intervalform.interval.data
        write_data("settings.yaml", settings)
        scheduler.reschedule_job('job', trigger="interval",
                                 minutes=settings["interval"][0])
        flash('Interval changed successful')
        return redirect("/settings")

    if removeroutes.validate_on_submit():
        data = read_data("data.yaml")
        multi_select = request.form.getlist('selectRoutes', type=int)
        for i in reversed(multi_select):
            del data["routes"][i]
        write_data("data.yaml", data)
        return redirect('/settings')

    return render_template('settings.html', intervalform=intervalform, apiform=apiform, removeroutes=removeroutes,
                           data=data, settings=settings, number_of_requests=number_of_requests)


@app.route('/downloads', methods=['POST', 'GET'])
def downloads():
    downloadfile = DownloadFiles()
    removefile = RemoveFiles()
    files = [os.path.basename(i) for i in glob.glob("traffic_data/*.csv")]
    if (all(x in files for x in
            request.form.getlist('selectDownloads'))) and downloadfile.validate_on_submit() and request.form.getlist(
        'selectDownloads'):
        select_files = request.form.getlist('selectDownloads')
        writer = ExcelWriter("traffic_data/compiled.xlsx")
        for item in select_files:
            for filename in glob.glob("traffic_data/" + item):
                df_csv = pd.read_csv(filename)

                (_, f_name) = os.path.split(filename)
                (f_short_name, _) = os.path.splitext(f_name)

                df_csv.to_excel(writer, f_short_name, index=False)

                writer.save()
        return send_file('traffic_data/compiled.xlsx', as_attachment=True attachment_filename='compiled.xlsx')

    if (all(x in files for x in
            request.form.getlist('selectFiles'))) and removefile.validate_on_submit() and request.form.getlist(
        'selectFiles'):
        select_files = request.form.getlist('selectFiles')
        for item in select_files:
            os.remove("traffic_data/" + item)
        return redirect("/downloads")
    return render_template('downloads.html', downloadfile=downloadfile, removefile=removefile, files=files)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
