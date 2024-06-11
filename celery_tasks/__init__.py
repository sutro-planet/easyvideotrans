import json

from celery import Celery


def load_celery_config():
    with open('./configs/celery.json', 'r') as config_file:
        config = json.load(config_file)
    return config


def load_tasks_route():
    with open('./configs/celery-task-routes.json', 'r') as config_file:
        config = json.load(config_file)
    return config


celery_app = Celery(__name__, include=["celery_tasks.tasks"])
celery_app.conf.update(load_celery_config())
celery_app.conf.task_routes = load_tasks_route()
