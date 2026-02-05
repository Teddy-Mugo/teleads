import os

import redis
from loguru import logger


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

try:
    redis_client = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=False,
    )

    # Test connection
    redis_client.ping()
    logger.success("Connected to Redis")

except Exception as e:
    logger.exception("Failed to connect to Redis")
    raise
