__copyright__ = '''
Copyright 2022 the original author or authors.
  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at
      http://www.apache.org/licenses/LICENSE-2.0
  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
'''

__author__ = 'David Turanski'

import logging
import time
import requests

logger = logging.getLogger(__name__)


class Poller:
    def __init__(self, wait_sec, max_retries):
        self.wait_sec = wait_sec
        self.max_retries = max_retries

    def wait_for(self, success_condition=lambda x: True, args=[],
                 failure_condition=lambda x: False,
                 wait_message="waiting for condition to be satisfied",
                 success_message="condition satisfied",
                 fail_message="FAILED: condition not satisfied"):
        tries = 0

        predicate = success_condition(*args)
        while not predicate and tries < self.max_retries:
            time.sleep(self.wait_sec)
            tries = tries + 1
            logger.info("%d/%d %s" % (tries, self.max_retries, wait_message))
            predicate = success_condition(*args)
            if failure_condition(*args):
                break
        if predicate:
            logger.info(success_message)
        else:
            logger.error(fail_message)
        return predicate


def wait_for_200(poller, url):
    return poller.wait_for(success_condition=lambda url: requests.get(url).status_code == 200,
                           args=[url],
                           success_message=url + " is up!",
                           fail_message=url + " is down")
