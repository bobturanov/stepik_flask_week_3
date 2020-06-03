import json
import os
from typing import Union, NoReturn

from flask import Flask, render_template, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import JSON, func
from sqlalchemy.orm.attributes import flag_modified
from wtforms import HiddenField, StringField, SubmitField
from wtforms.validators import InputRequired, Length

from settings import get_csrf

app = Flask(__name__)
app.secret_key = get_csrf()
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

teachers_goals_association = db.Table(
    "teachers_goals",
    db.Column("teacher_id", db.Integer, db.ForeignKey("teacher.id")),
    db.Column("goal_id", db.Integer, db.ForeignKey("goal.id")),
)


class Goal(db.Model):
    __tablename__ = "goal"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False)
    teacher = db.relationship("Teacher", secondary=teachers_goals_association, back_populates="goals")


class Teacher(db.Model):
    __tablename__ = "teacher"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    about = db.Column(db.String, nullable=False)
    rating = db.Column(db.Float)
    picture = db.Column(db.String)
    price = db.Column(db.Integer)
    free = db.Column(JSON)
    goals = db.relationship("Goal", secondary=teachers_goals_association, back_populates="teacher")
    booking = db.relationship("Booking", back_populates="teacher")


class Booking(db.Model):
    __tablename__ = "booking"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(18), nullable=False)
    day = db.Column(db.String, nullable=False)
    time = db.Column(db.String, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"))
    teacher = db.relationship("Teacher", back_populates="booking")


class Request(db.Model):
    __tablename__ = "request"

    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("goal.id"))
    goal = db.relationship("Goal")
    time = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String(14), nullable=False)


with open('data/auxiliary_data.json', 'r') as json_days:
    auxiliary_data = json.load(json_days)
    days = auxiliary_data['days of the week']


def get_goals() -> dict:
    goals = db.session.query(Goal).all()

    goals_dict = {}
    for goal in goals:
        goals_dict.update({goal.slug: goal.name})

    return goals_dict


def save_application(form) -> NoReturn:
    user_week = form.data['week']
    user_time = form.data['time']
    teacher_id = form.data['teacher']

    teacher = db.session.query(Teacher).get(int(teacher_id))
    teacher.free[user_week][f'{user_time}:00'] = False
    flag_modified(teacher, "free")

    booking = Booking(name=form.data['name'],
                      phone=form.data['phone'],
                      day=user_week,
                      time=user_time,
                      teacher_id=int(teacher_id))

    db.session.add_all([booking, teacher])
    db.session.commit()


def get_teacher(teacher_id: Union[int, str]) -> dict:
    teacher = db.session.query(Teacher).get_or_404(int(teacher_id))

    teacher_goals = []
    for goal in teacher.goals:
        teacher_goals.append(goal.slug)

    teacher = teacher.__dict__
    teacher['goals'] = teacher_goals
    return teacher


class BookingForm(FlaskForm):
    name = StringField('Имя', [InputRequired(message='Похоже на пустое поле, введите, пожалуйста, имя')])
    phone = StringField('Телефон', [Length(min=5, message='Не похоже на телефон, введите, пожалуйста, ваш телефон')])
    week = HiddenField()
    time = HiddenField()
    teacher = HiddenField()
    submit = SubmitField('Записаться на пробный урок')


@app.route('/')
def main():
    random_teachers = db.session.query(Teacher).order_by(func.random()).limit(6)

    random_teachers_dict = {}
    for teacher in random_teachers:
        random_teachers_dict.update({teacher.id: teacher.__dict__})

    goals = get_goals()
    return render_template('index.html',
                           goals=goals,
                           teachers=random_teachers_dict,
                           emojis=auxiliary_data['goal_emoji'])


@app.route('/goals/<goal>')
def render_goals(goal):
    goal_teachers_db = Teacher.query.join(Teacher.goals).filter(Goal.slug == goal).order_by(Teacher.rating.desc())

    goal_teachers_dict = {}
    for goal_teacher in goal_teachers_db:
        goal_teachers_dict.update({goal_teacher.id: goal_teacher.__dict__})

    goals = get_goals()
    return render_template('goal.html',
                           teachers=goal_teachers_dict,
                           goals=goals,
                           goal=goal,
                           emojis=auxiliary_data['goal_emoji'])


@app.route('/profiles/<teacher_id>')
def render_profiles(teacher_id):
    goals = get_goals()
    teacher = get_teacher(teacher_id)
    return render_template('profile.html', teacher=teacher, goals=goals, days=days)


@app.route('/request/')
def render_request():
    return render_template('request.html')


@app.route('/request_done', methods=['POST'])
def render_request_done():
    goal_id = db.session.query(Goal).filter_by(slug=request.form['goal']).first().id
    request_row = Request(goal_id=goal_id,
                          time=request.form['time'],
                          name=request.form['name'],
                          phone=request.form['phone'])
    db.session.add(request_row)
    db.session.commit()

    request_dict = {}
    for key, val in request.form.items():
        request_dict.update({key: val})

    goals = get_goals()
    return render_template('request_done.html', form=request_dict, goals=goals)


@app.route('/booking/<teacher_id>/<week>/<time>')
def render_booking(teacher_id, week, time):
    teacher = get_teacher(teacher_id)
    form = BookingForm(week=week, time=time, teacher=teacher_id)
    return render_template('booking.html', teacher=teacher, days=days, form=form)


@app.route('/submit', methods=['POST'])
def submit():
    form = BookingForm()

    if form.validate_on_submit():
        save_application(form)
        return render_template('booking_done.html', form=form, days=days)
    else:
        form.name.data = None
        form.phone.data = None
        teacher = get_teacher(form.teacher.data)
        return render_template('booking.html', teacher=teacher, days=days, form=form)


if __name__ == '__main__':
    app.run()
