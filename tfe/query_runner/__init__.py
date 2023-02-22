import logging

logger = logging.getLogger(__name__)

query_runners = {}


def register(query_runner_class):
    global query_runners

    logger.debug(
        "Registering %s (%s) query runner.",
        query_runner_class.name(),
        query_runner_class.type(),
    )
    query_runners[query_runner_class.type()] = query_runner_class
