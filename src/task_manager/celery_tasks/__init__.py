import os
import json
import logging
import threading

from celery import Celery
from prometheus_client import start_http_server

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def load_celery_config():
    with open('./configs/celery.json', 'r') as config_file:
        config = json.load(config_file)

    config['broker_domain'] = os.getenv('CELERY_BROKER_DOMAIN', config['broker_domain'])
    config['broker_url'] = os.getenv('CELERY_BROKER_URL', config['broker_url'])
    config['result_backend'] = os.getenv('CELERY_RESULT_BACKEND', config['result_backend'])
    config['worker_prefetch_multiplier'] = int(
        os.getenv('CELERY_WORKER_PREFETCH_MULTIPLIER', config['worker_prefetch_multiplier']))
    config['task_acks_late'] = os.getenv('CELERY_TASK_ACKS_LATE', str(config['task_acks_late']).lower()) in ['true',
                                                                                                             '1', 't',
                                                                                                             'y', 'yes']
    config['task_time_limit'] = os.getenv('CELERY_TASK_TIME_LIMIT', config['task_time_limit'])
    config['task_soft_time_limit'] = os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', config['task_soft_time_limit'])
    config['metrics_server_port'] = os.getenv('CELERY_METRICS_SERVER_PORT', config['metrics_server_port'])
    return config


def load_tasks_route():
    with open('./configs/celery-task-routes.json', 'r') as config_file:
        config = json.load(config_file)
    return config


celery_config = load_celery_config()
logger.warning("Celery Configuration: %s", json.dumps(celery_config, indent=4))

celery_app = Celery(__name__, include=["src.task_manager.celery_tasks.tasks"])
celery_app.conf.update(load_celery_config())
celery_app.conf.task_routes = load_tasks_route()


# Start the metrics server in a separate thread
def start_metrics_server():
    metrics_port = celery_config['metrics_server_port']
    logger.warning("Celery Metrics Server running on port: %s", metrics_port)
    start_http_server(port=int(metrics_port))


threading.Thread(target=start_metrics_server).start()
