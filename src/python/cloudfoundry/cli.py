import json
import logging
import re
import time
from scdf_at.shell import Shell
from cloudfoundry.domain import Service
from cloudfoundry.config import TestConfig

logger = logging.getLogger(__name__)


class CloudFoundry:
    initialized = False

    @classmethod
    def connect(cls, deployer_config):
        logger.debug("ConnectionConfig:" + json.dumps(deployer_config))
        cf = CloudFoundry(deployer_config)

        if not CloudFoundry.initialized:
            logger.debug("logging in to CF - api: %s org: %s space: %s" % (
                deployer_config.api_endpoint, deployer_config.org, deployer_config.space))
            proc = cf.login()
            if proc.returncode != 0:
                logger.error("CF login failed: " + Shell.stdout_to_s(proc))
                cf.logout()
                raise RuntimeError(
                    "cf login failed for some reason. Verify the username/password and that org %s and space %s exist"
                    % (deployer_config.org, deployer_config.space))
            logger.info("\n" + json.dumps(cf.current_target()))
            CloudFoundry.initialized = True
        else:
            logger.debug("Already logged in. Call 'cf logout'")
        return cf

    def __init__(self, deployer_config, test_config=TestConfig(), shell=Shell()):
        if not deployer_config:
            raise ValueError("'deployer_config' is required")
        if not test_config:
            raise ValueError("'test_config' is required")
        if not shell:
            raise ValueError("'shell' is required")

        self.test_config = test_config
        self.deployer_config = deployer_config

        self.shell = shell
        try:
            self.shell.exec('cf --version')
        except Exception:
            raise RuntimeError('cf cli is not installed')

        target = self.current_target()

        if target and not target.get('api endpoint') == deployer_config.api_endpoint:
            raise RuntimeError("Already logged in to " + target.get('api endpoint'))
        # Might be logged in with no space and org
        if target and target.get('api endpoint') == deployer_config.api_endpoint and not (
                target.get('org') == deployer_config.org and target.get('space') == deployer_config.space):
            logger.info(
                "targeting configured environment: org = %s space = %s" % (deployer_config.org, deployer_config.space))
            proc = self.target(org=deployer_config.org, space=deployer_config.space)
            if proc.returncode:
                raise RuntimeError("unable to log in to CF environment")
            target = self.current_target()
        elif target and target.get('api endpoint') == deployer_config.api_endpoint and \
                target.get('org') == deployer_config.org and target.get('space') == deployer_config.space:
            CloudFoundry.initialized = True

    def current_target(self):
        proc = self.shell.exec("cf target")
        contents = self.shell.stdout_to_s(proc)
        print(contents)
        target = {}
        for line in contents.split('\n'):
            if line and ':' in line:
                key = line[0:line.index(':')].strip()
                value = line[line.index(':') + 1:].strip()
                target[key] = value
        logger.debug("current context:" + str(target))
        return target

    def target(self, org=None, space=None):
        cmd = "cf target"
        if org is not None:
            cmd = cmd + " -o %s" % (org)
        if space is not None:
            cmd = cmd + " -s %s" % (space)
        return self.shell.exec(cmd)

    def push(self, args):
        cmd = 'cf push ' + args
        return self.shell.exec(cmd)

    def is_logged_in(self):
        proc = self.shell.exec("cf target")
        return proc.returncode == 0

    def logout(self):
        proc = self.shell.exec("cf logout")
        if proc.returncode == 0:
            CloudFoundry.initialized = False
        return proc

    def login(self):
        skip_ssl = ""
        if self.deployer_config.skip_ssl_validation:
            skip_ssl = "--skip-ssl-validation"

        cmd = "cf login -a %s -o %s -s %s -u %s -p %s %s" % \
              (self.deployer_config.api_endpoint,
               self.deployer_config.org,
               self.deployer_config.space,
               self.deployer_config.username,
               self.deployer_config.password,
               skip_ssl)
        print(cmd)
        return self.shell.exec(cmd)

    def create_service(self, service_config):
        logger.info("creating service " + json.dumps(service_config))

        proc = self.shell.exec("cf create-service %s %s %s %s" %
                               (service_config.service, service_config.plan, service_config.name,
                                "-c '%s'" % service_config.config if service_config.config else ""))
        self.shell.log_stdout(proc)
        if self.shell.dry_run:
            return proc

        if proc.returncode:
            logger.error(self.shell.stdout_to_s(proc))
            return proc

        if not self.wait_for(success_condition=lambda: self.service(service_config.name).status == 'create succeeded',
                             failure_condition=lambda: self.service(service_config.name).status == 'create failed',
                             wait_message="waiting for service status 'create succeeded'"):
            raise SystemExit("FATAL: unable to create service %s" % service_config)
        else:
            logger.info("created service %s" % service_config.name)
        return proc

    def delete_service(self, service_name):
        logger.info("deleting service %s" % service_name)

        proc = self.shell.exec("cf delete-service -f %s" % service_name)
        self.shell.log_stdout(proc)
        if self.shell.dry_run:
            return proc
        if proc.returncode:
            logger.error(self.shell.stdout_to_s(proc))
            return proc

        if not self.wait_for(success_condition=lambda: self.service(service_name) is None,
                             failure_condition=lambda: self.service(service_name).status == 'delete failed',
                             wait_message="waiting for %s to be deleted" % service_name):
            raise SystemExit("FATAL: %s " % str(self.service(service_name)))
        else:
            logger.info("deleted service %s" % service_name)
        return proc

    def create_service_key(self):
        pass

    def delete_service_key(self):
        pass

    def apps(self):
        appnames = []
        proc = self.shell.exec("cf apps")
        contents = self.shell.stdout_to_s(proc)
        i = 0
        for line in contents.split("\n"):
            if i > 3 and line:
                appnames.append(line.split(' ')[0])
            i = i + 1
        return appnames

    def delete_app(self, app_id):
        pass

    def delete_all(self, apps):
        for app in apps:
            proc = self.shell.exec("cf delete -f %s" % app)
            self.shell.log_command(proc, "executed");

    def service(self, service_name):
        proc = self.shell.exec("cf service " + service_name)
        if proc.returncode != 0:
            logger.debug("service %s does not exist, or there is some other issue." % service_name)
            return None

        contents = self.shell.stdout_to_s(proc)
        pattern = re.compile('(.+)\:\s+(.*)')
        s = {}
        for line in contents.split('\n'):
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                s[match[1].strip()] = match[2].strip()

        return Service(name=s.get('name'),
                       service=s.get('service'),
                       plan=s.get('plan'),
                       status=s.get('status'),
                       message=s.get('message'))

    def services(self):
        logger.debug("getting services")
        proc = self.shell.exec("cf services")
        contents = self.shell.stdout_to_s(proc)
        services = []
        parse_line = False
        for line in contents.split('\n'):
            # Brittle to scrape the text output directly, just grab the name and call `cf service` for each.
            # See self.service().
            if line.strip():
                if line.startswith('name'):
                    parse_line = True

                elif parse_line:
                    row = line.split(' ')
                    services.append(self.service(row[0]))

        logger.debug("services:\n" + json.dumps(services, indent=4))
        return services

    def wait_for(self, success_condition=True, args=[],
                 failure_condition=False,
                 wait_sec=None,
                 max_retries=None,
                 wait_message="waiting for condition to be satisfied",
                 success_message="condition satisfied",
                 fail_message="FAILED: condition not satisfied"):
        tries = 0
        if not wait_sec:
            wait_sec = self.test_config.deploy_wait_sec
        if not max_retries:
            max_retries = self.test_config.max_retries

        predicate = success_condition(*args)
        while not predicate and tries < max_retries:
            time.sleep(wait_sec)
            tries = tries + 1
            logger.info("%d/%d %s" % (tries, max_retries, wait_message))
            predicate = success_condition(*args)
            if failure_condition(*args):
                break
        if predicate:
            logger.info(success_message)
        else:
            logger.error(fail_message)
        return predicate