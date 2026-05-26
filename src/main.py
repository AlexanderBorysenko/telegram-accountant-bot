import asyncio
import logging

from src.bot import create_bot
from src.config import settings
from src.db import init_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application):
    await init_db(settings.mongodb_uri, settings.mongodb_db_name)
    logger.info("Database initialized")


def main():
    logger.info("Starting Accounter Bot")
    app = create_bot()
    app.post_init = post_init
    app.run_polling()


if __name__ == "__main__":
    main()
