import json
import random

from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import InputRequired, Length

from settings import get_csrf

app = Flask(__name__)
app.secret_key = get_csrf()

with open('data/auxiliary_data.json', 'r') as json_days:
    auxiliary_data = json.load(json_days)
    days = auxiliary_data['days of the week']


def update_data():
    with open('data/data.json', 'r') as json_data:
        data = json.load(json_data)
    return data


class BookingForm(FlaskForm):
    name = StringField('Имя', [InputRequired(message='Похоже на пустое поле, введите, пожалуйста, имя')])
    phone = StringField('Телефон', [Length(min=5, message='Не похоже на телефон, введите, пожалуйста, ваш телефон')])
    week = HiddenField()
    time = HiddenField()
    teacher = HiddenField()
    submit = SubmitField('Записаться на пробный урок')


@app.route('/')
def main():
    teachers = update_data()['teachers']
    random_teachers_id = random.sample(list(teachers), 6)
    random_teachers = {key: teachers[key] for key in random_teachers_id}
    return render_template('index.html', goals=update_data()['goals'], teachers=random_teachers,
                           emojis=auxiliary_data['goal_emoji'])


@app.route('/goals/<goal>')
def render_goals(goal):
    teachers = update_data()['teachers']
    goal_teachers = {}

    for key, val in teachers.items():
        if goal in val['goals']:
            goal_teachers.update({key: val})

    goal_teachers = {k: v for k, v in sorted(goal_teachers.items(), key=lambda item: item[1]['rating'], reverse=True)}
    return render_template('goal.html',
                           teachers=goal_teachers,
                           goals=update_data()['goals'],
                           goal=goal,
                           emojis=auxiliary_data['goal_emoji'])


@app.route('/profiles/<teacher_id>')
def render_profiles(teacher_id):
    teachers = update_data()['teachers']
    return render_template('profile.html', teacher=teachers[teacher_id], goals=update_data()['goals'], days=days)


@app.route('/request/')
def render_request():
    return render_template('request.html')


@app.route('/request_done', methods=['POST'])
def render_request_done():
    request_dict = {}

    for key, val in request.form.items():
        request_dict.update({key: val})

    pk = f"{request_dict['name']}_{request_dict['phone']}_{request_dict['goal']}_{request_dict['time']}"

    with open('data/request.json', 'r+') as request_data:
        data = json.load(request_data)
        request_data.seek(0)
        request_data.truncate(0)
        data.update({pk: request_dict})
        json.dump(data, request_data, ensure_ascii=False)

    return render_template('request_done.html', form=request_dict, goals=update_data()['goals'])


@app.route('/booking/<teacher_id>/<week>/<time>')
def render_booking(teacher_id, week, time):
    teachers = update_data()['teachers']
    form = BookingForm(week=week, time=time, teacher=teacher_id)
    return render_template('booking.html', teacher=teachers[teacher_id], days=days, form=form)


def save_application(form):
    user_week = form.data['week']
    user_time = form.data['time']
    teacher_id = form.data['teacher']

    with open('data/data.json', 'r+') as json_data:
        data = json.load(json_data)
        json_data.seek(0)
        json_data.truncate(0)
        data['teachers'][teacher_id]['free'][user_week][f"{user_time}:00"] = False
        json.dump(data, json_data, ensure_ascii=False)

    pk = f'{teacher_id}_{user_time}_{user_week}'
    request_dict = {
        'user_name': form.data['name'],
        'user_phone': form.data['phone'],
        'teacher_id': teacher_id,
        'week': user_week,
        'time': user_time,
    }

    with open('data/booking.json', 'r+') as booking_data:
        data = json.load(booking_data)
        booking_data.seek(0)
        booking_data.truncate(0)
        teacher_data = data.get(teacher_id)

        if teacher_data:
            data[teacher_id].update({pk: request_dict})
        else:
            data.update({teacher_id: {pk: request_dict}})

        json.dump(data, booking_data, ensure_ascii=False)


@app.route('/submit', methods=['POST'])
def submit():
    teachers = update_data()['teachers']
    form = BookingForm()

    if form.validate_on_submit():
        save_application(form)
        return render_template('booking_done.html', form=form, days=days)
    else:
        form.name.data = None
        form.phone.data = None
        return render_template('booking.html', teacher=teachers[form.teacher.data], days=days, form=form)


if __name__ == '__main__':
    app.run()
