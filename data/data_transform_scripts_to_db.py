import os

path_parent = os.path.dirname(os.getcwd())
os.chdir(path_parent)

from app import Goal, db, Teacher
from data import goals, teachers


def transform_goals():
    for slug, name in goals.items():
        record = Goal(slug=slug, name=name)
        db.session.add(record)

    db.session.commit()


def transform_teachers():
    for teacher in teachers:
        goals_bd = []
        for ggoal in teacher['goals']:
            goals_bd.append(db.session.query(Goal).filter_by(slug=ggoal).first())
        record = Teacher(name=teacher['name'], about=teacher['about'], rating=teacher['rating'],
                         picture=teacher['picture'], price=teacher['price'], free=teacher['free'],
                         goals=goals_bd)
        db.session.add(record)

    db.session.commit()


if __name__ == "__main__":
    transform_goals()
    transform_teachers()
