import os, json, logging
from cloudfoundry.domain import JSonEnabled

logger = logging.getLogger(__name__)


def env_vars(prefix):
    if not prefix:
        logger.warning("no environment variable prefix is set")
    if not prefix:
        return os.environ
    env = {}
    for (key, value) in os.environ.items():
        if key.startswith(prefix):
            env[key] = value
    return env


class TestConfig(JSonEnabled):
    def __init__(self, env=None):
        self.deploy_wait_sec = 20,
        self.max_retries = 150
        self.buildpacks = ['java_buildpack_offline']
        self.maven_repos = ['https://repo.spring.io/libs-snapshot']
        self.env = env


class CloudFoundryDeployerConfig(JSonEnabled):
    prefix = "SPRING_CLOUD_DEPLOYER_CLOUDFOUNDRY_"
    url_key = prefix + "URL"
    org_key = prefix + "ORG"
    space_key = prefix + "SPACE"
    app_domain_key = prefix + "DOMAIN"
    username_key = prefix + "USERNAME"
    password_key = prefix + "PASSWORD"
    skip_ssl_validation_key = prefix + "SKIP_SSL_VALIDATION"

    @classmethod
    def from_env_vars(cls):
        env = env_vars(cls.prefix)
        if not env.get(cls.url_key):
            raise ValueError(cls.url_key + " is not configured in environment")

        return CloudFoundryDeployerConfig(api_endpoint=env.get(cls.url_key),
                                          org=env.get(cls.org_key),
                                          space=env.get(cls.space_key),
                                          app_domain=env.get(cls.app_domain_key),
                                          username=env.get(cls.username_key),
                                          password=env.get(cls.password_key),
                                          skip_ssl_validation=env.get(cls.skip_ssl_validation_key),
                                          env=env)

    def __init__(self, api_endpoint, org, space, app_domain, username, password, skip_ssl_validation=True,
                 env=None):
        # Besides the required props,we will put these in the scdf_server manifest
        self.env = env
        self.api_endpoint = api_endpoint
        self.org = org
        self.space = space
        self.app_domain = app_domain
        self.username = username
        self.password = password
        self.skip_ssl_validation = skip_ssl_validation
        self.env = env
        self.validate()

    def connection(self):
        return {'url': self.api_endpoint, 'org': self.org, 'space': self.space, 'domain': self.app_domain,
                'username': self.username, 'password': self.password}

    def validate(self):
        if not self.api_endpoint:
            raise ValueError("'api_endpoint' is required")
        if not self.org:
            raise ValueError("'org' is required")
        if not self.space:
            raise ValueError("'space' is required")
        if not self.app_domain:
            raise ValueError("'app_domain' is required")
        if not self.username:
            raise ValueError("'username' is required")
        if not self.password:
            raise ValueError("'password' is required")


class DBConfig(JSonEnabled):
    prefix = "SQL_"

    @classmethod
    def from_env_vars(cls):
        env = env_vars(cls.prefix)
        if not env.get(cls.prefix + 'HOST'):
            logger.warning("%s is not defined in the OS environment" % (cls.prefix + 'HOST'))
            return None

        return DBConfig(host=env.get(cls.prefix + 'HOST'),
                        port=env.get(cls.prefix + 'PORT'),
                        username=env.get(cls.prefix + 'USERNAME'),
                        password=env.get(cls.prefix + 'PASSWORD'),
                        provider=env.get(cls.prefix + 'PROVIDER'),
                        index=env.get(cls.prefix + 'INDEX'))

    def __init__(self, host, port, username, password, provider, index='0'):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.provider = provider
        self.index = index


class DatasourceConfig(JSonEnabled):
    prefix = "SPRING_DATASOURCE_"
    url_key = prefix + "URL"
    username_key = prefix + "USERNAME"
    password_key = prefix + "PASSWORD"
    driver_class_name_key = prefix + 'DRIVER_CLASS_NAME'

    def __init__(self, url, username, password, driver_class_name, host, port, provider):
        self.url = url
        self.username = username
        self.password = password
        self.driver_class_name = driver_class_name
        self.host = host
        self.port = port
        self.provider = provider

    def validate(self):
        if not self.url:
            raise ValueError("'url' is required")
        if not self.username:
            raise ValueError("'username' is required")
        if not self.password:
            raise ValueError("'password' is required")
        if not self.driver_class_name:
            raise ValueError("'driver_class_name' is required")
        if not self.host:
            raise ValueError("'host' is required")
        if not self.port:
            raise ValueError("'port' is required")
        p = int(self.port)
        if not self.provider:
            raise ValueError("'provider' is required")


class KafkaConfig(JSonEnabled):
    prefix = "KAFKA_"

    @classmethod
    def from_env_vars(cls):
        env = env_vars(cls.prefix)
        if not env.get(cls.prefix + 'BROKER_ADDRESS'):
            logger.debug(
                "%s is not defined in the OS environment. Skipping Kafka config" % (cls.prefix + 'BROKER_ADDRESS'))
            return None

        return KafkaConfig(broker_address=os.getenv(cls.prefix + 'BROKER_ADDRESS'),
                           username=os.getenv(cls.prefix + 'USERNAME'),
                           password=os.getenv(cls.prefix + 'PASSWORD'))

    def __init__(self, broker_address, username, password):
        self.broker_address = broker_address
        self.username = username
        self.password = password

    def validate(self):
        if not self.broker_address:
            raise ValueError("'broker_address' is required")
        if not self.username:
            raise ValueError("'username' is required")
        if not self.password:
            raise ValueError("'password' is required")


class ServiceConfig(JSonEnabled):
    def __init__(self, name, service, plan, config=None):
        self.name = name
        self.service = service
        self.plan = plan
        self.config = config
        self.validate()

    def __eq__(self, other):
        if isinstance(other, ServiceConfig):
            return self.name == other.name and self.service and other.service and \
                   self.plan == other.plan and self.config == other.config

    @classmethod
    def of_service(cls, service):
        return ServiceConfig(name=service.name, service=service.service, plan=service.plan)

    @classmethod
    def rabbit_default(cls):
        return ServiceConfig(name="rabbit", service="p.rabbitmq", plan="single-node")

    @classmethod
    def scheduler_default(cls):
        return ServiceConfig(name="ci-scheduler", service="scheduler-for-pcf", plan="standard")

    def validate(self):
        if not self.name:
            raise ValueError("'name' is required")
        if not self.service:
            raise ValueError("'service' is required")
        if not self.plan:
            raise ValueError("'plan' is required")

        if self.config:
            try:
                json.loads(self.config)
            except BaseException:
                raise ValueError("config is not valid json:" + self.config)


class DataflowConfig(JSonEnabled):
    prefix = 'SPRING_CLOUD_DATAFLOW_'

    @classmethod
    def from_env_vars(cls):
        env = env_vars(cls.prefix)
        streams_enabled = env.get(cls.prefix + "FEATURES_STREAMS_ENABLED") if env.get(
            cls.prefix + "FEATURES_STREAMS_ENABLED") else True
        tasks_enabled = env.get(cls.prefix + "FEATURES_TASKS_ENABLED") if env.get(
            cls.prefix + "FEATURES_TASKS_ENABLED") else True
        schedules_enabled = env.get(cls.prefix + "FEATURES_SCHEDULES_ENABLED") if env.get(
            cls.prefix + "FEATURES_SCHEDULES_ENABLED") else False
        return DataflowConfig(streams_enabled, tasks_enabled, schedules_enabled, env)

    def __init__(self, streams_enabled=True, tasks_enabled=True, schedules_enabled=True, env={}):
        self.streams_enabled = streams_enabled
        self.tasks_enabled = tasks_enabled
        self.schedules_enabled = schedules_enabled
        self.env = env
        if not env.get('SPRING_PROFILES_ACTIVE'):
            env['SPRING_PROFILES_ACTIVE'] = 'cloud'
        if not env.get('JBP_CONFIG_SPRING_AUTO_RECONFIGURATION'):
            env['JBP_CONFIG_SPRING_AUTO_RECONFIGURATION'] = '{enabled: false}'
        if not env.get('SPRING_APPLICATION_NAME'):
            env['SPRING_APPLICATION_NAME'] = 'dataflow-server'

    def validate(self):
        if not self.streams_enabled and not self.tasks_enabled:
            raise ValueError("One 'streams_enabled' or 'tasks_enabled' must be true")
        if self.schedules_enabled and not self.tasks_enabled:
            raise ValueError("'schedules_enabled' requires 'tasks_enabled' to be true")


class SkipperConfig(JSonEnabled):
    prefix = 'SPRING_CLOUD_SKIPPER_'

    @classmethod
    def from_env_vars(cls):
        env = env_vars(cls.prefix)
        return SkipperConfig(env)

    def __init__(self, env={}):
        self.env = env
        if not env.get('SPRING_PROFILES_ACTIVE'):
            env['SPRING_PROFILES_ACTIVE'] = 'cloud'
        if not env.get('JBP_CONFIG_SPRING_AUTO_RECONFIGURATION'):
            env['JBP_CONFIG_SPRING_AUTO_RECONFIGURATION'] = '{enabled: false}'
        if not env.get('SPRING_APPLICATION_NAME'):
            env['SPRING_APPLICATION_NAME'] = 'skipper-server'


class CloudFoundryConfig(JSonEnabled):
    @classmethod
    def from_env_vars(cls):
        deployer_config = CloudFoundryDeployerConfig.from_env_vars()
        dataflow_config = DataflowConfig.from_env_vars()
        db_config = DBConfig.from_env_vars()
        kafka_config = KafkaConfig.from_env_vars()
        return CloudFoundryConfig(deployer_config=deployer_config, dataflow_config=dataflow_config,
                                  db_config=db_config, kafka_config = kafka_config)

    def __init__(self, deployer_config, dataflow_config=None, skipper_config=None, db_config=None,
                 services_config=[ServiceConfig.rabbit_default()], test_config=TestConfig(),kafka_config=None):
        self.deployer_config = deployer_config
        self.dataflow_config = dataflow_config
        self.skipper_config = skipper_config
        self.services_config = services_config
        self.test_config = test_config
        self.db_config = db_config
        self.kafka_config = kafka_config
        # Set later. 1 for dataflow and one for skipper
        self.datasources_config = {}
        self.validate()

    def validate(self):
        if not self.deployer_config:
            raise ValueError("'deployer_config' is required")
        if not self.dataflow_config:
            logger.error("Really? No Dataflow config properties? What's the point")
        if not self.skipper_config and self.dataflow_config and not self.dataflow_config.streams_enabled:
            logger.error("Skipper config is required if streams are enabled")
