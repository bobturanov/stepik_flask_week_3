import json
import logging

from data import goals, teachers


def transform_data() -> None:
    teachers_dict = {}
    for teacher in teachers:
        teachers_dict.update({teacher['id']: teacher})
    with open('data.json', 'w') as json_data_file:
        json.dump({'goals': goals, 'teachers': teachers_dict}, json_data_file, ensure_ascii=False)
    logging.info('transform data: OK')

if __name__ == "__main__":
    transform_data()
