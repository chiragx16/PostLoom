import redis
from config import config

redis_client = redis.Redis.from_url(config.REDIS_URL)