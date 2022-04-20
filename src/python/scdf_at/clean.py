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
import sys

from cloudfoundry.cli import CloudFoundry
from cloudfoundry.config import CloudFoundryDeployerConfig, CloudFoundryATConfig, DataflowConfig, DatasourceConfig
from optparse import OptionParser
import cloudfoundry.environment
from scdf_at import enable_debug_logging

logger = logging.getLogger(__name__)


def cf_config_from_env():
    deployer_config = CloudFoundryDeployerConfig.from_env_vars()
    db_config = DatasourceConfig.from_spring_env_vars()
    dataflow_config = DataflowConfig.from_env_vars()

    return CloudFoundryATConfig(deployer_config=deployer_config, db_config=db_config,
                                dataflow_config=dataflow_config)


def clean(args):
    parser = OptionParser()
    parser.usage = "%prog clean options"

    parser.add_option('-v', '--debug',
                      help='debug level logging',
                      dest='debug', default=False, action='store_true')
    parser.add_option('-p', '--platform',
                      help='the platform type (cloudfoundry, tile)',
                      dest='platform', default='cloudfoundry')
    parser.add_option('--serverCleanup',
                      help='run the cleanup for the apps, but excluding services',
                      dest='serverCleanup', action='store_true')
    try:
        options, arguments = parser.parse_args(args)
        if options.debug:
            enable_debug_logging()
        cf = CloudFoundry.connect(cf_config_from_env().deployer_config)
        logger.info("cleaning up apps...")
        if not options.serverCleanup:
            logger.info("cleaning services ...")

        cloudfoundry.environment.clean(cf, cf_config_from_env(), options)

    except SystemExit:
        parser.print_help()
        exit(1)


if __name__ == '__main__':
    clean(sys.argv)
