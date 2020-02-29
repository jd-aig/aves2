import pika


def get_connection(rabbitmq_host, rabbitmq_user, rabbitmq_pass):
    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
    parameters = pika.ConnectionParameters(rabbitmq_host,
                                           5672,
                                           '/',
                                           credentials)
    connection = pika.BlockingConnection(parameters)
    return connection
