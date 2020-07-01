import asyncio
import logging
import os
from concurrent import futures

import aiohttp
from asgiref.sync import sync_to_async

from abitur.parsers import PirogovaParser, SechenovaParser, SechenovaBVIParser

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(process)d - %(name)s - %(funcName)s - %(message)s', datefmt='[%H:%M:%S]'
)
h = logging.StreamHandler()
h.setFormatter(formatter)
logger.addHandler(h)


class AsyncCrawler:

    def __init__(self):
        self.parsers = [PirogovaParser, SechenovaParser, SechenovaBVIParser]

    async def _get_sources(self):
        logger.debug('Getting sources.')
        tasks = []

        async with aiohttp.ClientSession() as session:
            for _parser in self.parsers:
                parser = _parser()
                task = asyncio.create_task(self._get_source(session, parser))
                tasks.append(task)
                logger.debug(f'Task with name {task.get_name()} added')
                result = await asyncio.gather(*tasks)

        logger.debug('Sources fetched.')

        return result

    async def _get_source(self, session, parser):
        await parser.get_page(session)
        source = await sync_to_async(parser.get_source)()
        logger.debug('Got source')

        return source

    async def _crawl(self):
        logger.debug('Crawler is running')

        tasks = []

        async with aiohttp.ClientSession() as session:
            with futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
                for _parser in self.parsers:
                    parser = _parser()
                    task = asyncio.create_task(parser.run(session, executor),
                                               name=f'{parser.__class__.__name__} task')
                    tasks.append(task)
                    logger.debug(f'Task with name {task.get_name()} added')

                result = await asyncio.gather(*tasks, return_exceptions=True)

        logger.debug('Crawler finished')
        return result

    def crawl(self):
        return asyncio.run(self._crawl())

    def get_sources(self):
        return asyncio.run(self._get_sources())