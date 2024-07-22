import pika

from src.task_manager.celery_tasks import load_celery_config


def get_queue_length(queue_name):
    celery_config = load_celery_config()

    # Setup parameters to connect to RabbitMQ
    parameters = pika.ConnectionParameters(host=celery_config['broker_domain'])
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    # Declare the queue to make sure it exists
    queue = channel.queue_declare(queue=queue_name, durable=True, passive=True)
    queue_length = queue.method.message_count

    connection.close()
    return queue_length
