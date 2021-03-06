#!/usr/bin/env python

import os.path
import requests
import sys
import json

from argparse import ArgumentParser
from datetime import datetime

__author__ = "Lisa Zangrando"
__email__ = "lisa.zangrando[AT]pd.infn.it"
__copyright__ = """Copyright (c) 2015 INFN - INDIGO-DataCloud
All Rights Reserved

Licensed under the Apache License, Version 2.0;
you may not use this file except in compliance with the
License. You may obtain a copy of the License at:

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied.
See the License for the specific language governing
permissions and limitations under the License."""


class Token(object):

    def __init__(self, token, data):
        self.id = token

        data = data["token"]
        self.roles = data["roles"]
        self.catalog = data["catalog"]
        self.issued_at = datetime.strptime(data["issued_at"],
                                           "%Y-%m-%dT%H:%M:%S.%fZ")
        self.expires_at = datetime.strptime(data["expires_at"],
                                            "%Y-%m-%dT%H:%M:%S.%fZ")
        self.project = data["project"]
        self.user = data["user"]

        if "extras" in data:
            self.extras = data["extras"]

    def getCatalog(self, service_name=None, interface="public"):
        if service_name:
            for service in self.catalog:
                if service["name"] == service_name:
                    for endpoint in service["endpoints"]:
                        if endpoint["interface"] == interface:
                            return endpoint
            return None
        else:
            return self.catalog

    def getExpiration(self):
        return self.expires_at

    def getId(self):
        return self.id

    def getExtras(self):
        return self.extras

    def getProject(self):
        return self.project

    def getRoles(self):
        return self.roles

    def getUser(self):
        return self.user

    def isAdmin(self):
        if not self.roles:
            return False

        for role in self.roles:
            if role["name"] == "admin":
                return True

        return False

    def issuedAt(self):
        return self.issued_at

    def isExpired(self):
        return self.getExpiration() < datetime.utcnow()

    def save(self, filename):
        # save to file
        with open(filename, 'w') as f:
            token = {}
            token["catalog"] = self.catalog
            token["extras"] = self.extras
            token["user"] = self.user
            token["project"] = self.project
            token["roles"] = self.roles
            token["roles"] = self.roles
            token["issued_at"] = self.issued_at.isoformat()
            token["expires_at"] = self.expires_at.isoformat()

            data = {"id": self.id, "token": token}

            json.dump(data, f)

    @classmethod
    def load(cls, filename):
        if not os.path.isfile(".auth_token"):
            return None

        # load from file:
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
                return Token(data["id"], data)
            # if the file is empty the ValueError will be thrown
            except ValueError as ex:
                raise ex

    def isotime(self, at=None, subsecond=False):
        """Stringify time in ISO 8601 format."""
        if not at:
            at = datetime.utcnow()

        if not subsecond:
            st = at.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            st = at.strftime('%Y-%m-%dT%H:%M:%S.%f')

        if at.tzinfo:
            tz = at.tzinfo.tzname(None)
        else:
            tz = 'UTC'

        st += ('Z' if tz == 'UTC' else tz)
        return st

    """The trustor or grantor of a trust is the person who creates the trust.
    The trustor is the one who contributes property to the trust.
    The trustee is the person who manages the trust, and is usually appointed
    by the trustor. The trustor is also often the trustee in living trusts.
    """
    def trust(self, trustee_user, expires_at=None,
              project_id=None, roles=None, impersonation=True):
        if self.isExpired():
            raise Exception("token expired!")

        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "User-Agent": "python-novaclient",
                   "X-Auth-Token": self.getId()}

        if roles is None:
            roles = self.getRoles()

        if project_id is None:
            project_id = self.getProject().get("id")

        data = {}
        data["trust"] = {"impersonation": impersonation,
                         "project_id": project_id,
                         "roles": roles,
                         "trustee_user_id": trustee_user,
                         "trustor_user_id": self.getUser().get("id")}

        if expires_at is not None:
            data["trust"]["expires_at"] = self.isotime(expires_at, True)

        endpoint = self.getCatalog(service_name="keystone")

        if not endpoint:
            raise Exception("keystone endpoint not found!")

        if "v2.0" in endpoint["url"]:
            endpoint["url"] = endpoint["url"].replace("v2.0", "v3")

        response = requests.post(url=endpoint["url"] + "/OS-TRUST/trusts",
                                 headers=headers,
                                 data=json.dumps(data))

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        if not response.text:
            raise Exception("trust token failed!")

        return Trust(response.json())


class KeystoneClient(object):

    def __init__(self, auth_url, username, password,
                 user_domain_id=None,
                 user_domain_name="default", project_id=None,
                 project_name=None, project_domain_id=None,
                 project_domain_name="default", timeout=None,
                 default_trust_expiration=None,
                 ca_cert=None):
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.user_domain_id = user_domain_id
        self.user_domain_name = user_domain_name
        self.project_id = project_id
        self.project_name = project_name
        self.project_domain_id = project_domain_id
        self.project_domain_name = project_domain_name
        self.ca_cert = ca_cert
        self.timeout = timeout
        self.token = None

        if default_trust_expiration:
            self.default_trust_expiration = default_trust_expiration
        else:
            self.default_trust_expiration = 24

    def authenticate(self):
        if self.token is not None:
            if self.token.isExpired():
                try:
                    self.deleteToken(self.token.getId())
                except requests.exceptions.HTTPError:
                    pass
            else:
                return

        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "User-Agent": "python-novaclient"}

        user_domain = {}
        if self.user_domain_id is not None:
            user_domain["id"] = self.user_domain_id
        else:
            user_domain["name"] = self.user_domain_name

        project_domain = {}
        if self.project_domain_id is not None:
            project_domain["id"] = self.project_domain_id
        else:
            project_domain["name"] = self.project_domain_name

        identity = {"methods": ["password"],
                    "password": {"user": {"name": self.username,
                                          "domain": user_domain,
                                          "password": self.password}}}

        data = {"auth": {}}
        data["auth"]["identity"] = identity

        if self.project_name:
            data["auth"]["scope"] = {"project": {"name": self.project_name,
                                                 "domain": project_domain}}

        if self.project_id:
            data["auth"]["scope"] = {"project": {"id": self.project_id,
                                                 "domain": project_domain}}
        response = requests.post(url=self.auth_url + "/auth/tokens",
                                 headers=headers,
                                 data=json.dumps(data),
                                 timeout=self.timeout,
                                 verify=self.ca_cert)

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        if not response.text:
            raise Exception("authentication failed!")

        # print(response.__dict__)

        token_subject = response.headers["X-Subject-Token"]
        token_data = response.json()

        self.token = Token(token_subject, token_data)

    def getUser(self, id):
        try:
            response = self.getResource("users/%s" % id, "GET")
        except requests.exceptions.HTTPError as ex:
            response = ex.response.json()
            raise Exception("error on retrieving the user info (id=%r): %s"
                            % (id, response["error"]["message"]))

        if response:
            response = response["user"]

        return response

    def getUsers(self):
        try:
            response = self.getResource("users", "GET")
        except requests.exceptions.HTTPError as ex:
            response = ex.response.json()
            raise Exception("error on retrieving the users list: %s"
                            % response["error"]["message"])

        if response:
            response = response["users"]

        return response

    def getUserProjects(self, id):
        try:
            response = self.getResource("users/%s/projects" % id, "GET")
        except requests.exceptions.HTTPError as ex:
            response = ex.response.json()
            raise Exception("error on retrieving the users's projects "
                            "(id=%r): %s" % (id, response["error"]["message"]))

        if response:
            response = response["projects"]

        return response

    def getUserRoles(self, user_id, project_id):
        try:
            response = self.getResource("/projects/%s/users/%s/roles"
                                        % (project_id, user_id), "GET")
        except requests.exceptions.HTTPError as ex:
            response = ex.response.json()
            raise Exception("error on retrieving the user's roles (usrId=%r, "
                            "prjId=%r): %s" % (user_id,
                                               project_id,
                                               response["error"]["message"]))

        if response:
            response = response["roles"]

        return response

    def getProject(self, id):
        try:
            response = self.getResource("/projects/%s" % id, "GET")
        except requests.exceptions.HTTPError as ex:
            response = ex.response.json()
            raise Exception("error on retrieving the project (id=%r, "
                            % (id, response["error"]["message"]))

        if response:
            response = response["project"]

        return response

    def getProjects(self):
        try:
            response = self.getResource("/projects", "GET")
        except requests.exceptions.HTTPError as ex:
            response = ex.response.json()
            raise Exception("error on retrieving the projects list: %s"
                            % response["error"]["message"])

        if response:
            response = response["projects"]

        return response

    def getRole(self, id):
        try:
            response = self.getResource("/roles/%s" % id, "GET")
        except requests.exceptions.HTTPError as ex:
            response = ex.response.json()
            raise Exception("error on retrieving the role info (id=%r): %s"
                            % (id, response["error"]["message"]))

        if response:
            response = response["role"]

        return response

    def getRoles(self):
        try:
            response = self.getResource("/roles", "GET")
        except requests.exceptions.HTTPError as ex:
            response = ex.response.json()
            raise Exception("error on retrieving the roles list: %s"
                            % response["error"]["message"])

        if response:
            response = response["roles"]

        return response

    def getToken(self):
        self.authenticate()
        return self.token

    def deleteToken(self, id):
        if self.token is None:
            return

        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "User-Agent": "python-novaclient",
                   "X-Auth-Project-Id": self.token.getProject()["name"],
                   "X-Auth-Token": self.token.getId(),
                   "X-Subject-Token": id}

        response = requests.delete(url=self.auth_url + "/auth/tokens",
                                   headers=headers,
                                   timeout=self.timeout)

        self.token = None

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

    def validateToken(self, id):
        self.authenticate()

        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "User-Agent": "python-novaclient",
                   "X-Auth-Project-Id": self.token.getProject()["name"],
                   "X-Auth-Token": self.token.getId(),
                   "X-Subject-Token": id}

        response = requests.get(url=self.auth_url + "/auth/tokens",
                                headers=headers,
                                timeout=self.timeout)

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        if not response.text:
            raise Exception("token not found!")

        token_subject = response.headers["X-Subject-Token"]
        token_data = response.json()

        return Token(token_subject, token_data)

    def getEndpoint(self, id=None, service_id=None):
        if id:
            try:
                response = self.getResource("/endpoints/%s" % id, "GET")
            except requests.exceptions.HTTPError as ex:
                response = ex.response.json()
                raise Exception("error on retrieving the endpoint (id=%r): %s"
                                % (id, response["error"]["message"]))
            if response:
                response = response["endpoint"]

            return response
        elif service_id:
            try:
                endpoints = self.getEndpoints()
            except requests.exceptions.HTTPError as ex:
                response = ex.response.json()
                raise Exception("error on retrieving the endpoints list"
                                "(serviceId=%r): %s"
                                % response["error"]["message"])

            if endpoints:
                for endpoint in endpoints:
                    if endpoint["service_id"] == service_id:
                        return endpoint

        return None

    def getEndpoints(self):
        try:
            response = self.getResource("/endpoints", "GET")
        except requests.exceptions.HTTPError as ex:
            response = ex.response.json()
            raise Exception("error on retrieving the endpoints list: %s"
                            % response["error"]["message"])

        if response:
            response = response["endpoints"]

        return response

    def getService(self, id=None, name=None):
        if id:
            try:
                response = self.getResource("/services/%s" % id, "GET")
            except requests.exceptions.HTTPError as ex:
                response = ex.response.json()
                raise Exception("error on retrieving the service info (id=%r)"
                                ": %s" % (id, response["error"]["message"]))

            if response:
                response = response["service"]
            return response
        elif name:
            services = self.getServices()

            if services:
                for service in services:
                    if service["name"] == name:
                        return service

        return None

    def getServices(self):
        try:
            response = self.getResource("/services", "GET")
        except requests.exceptions.HTTPError as ex:
            response = ex.response.json()
            raise Exception("error on retrieving the services list: %s"
                            % response["error"]["message"])

        if response:
            response = response["services"]

        return response

    def getResource(self, resource, method, data=None):
        self.authenticate()

        url = self.auth_url + "/" + resource

        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "User-Agent": "python-novaclient",
                   "X-Auth-Project-Id": self.token.getProject()["name"],
                   "X-Auth-Token": self.token.getId()}

        if method == "GET":
            response = requests.get(url,
                                    headers=headers,
                                    params=data,
                                    timeout=self.timeout,
                                    verify=self.ca_cert)
        elif method == "POST":
            response = requests.post(url,
                                     headers=headers,
                                     data=json.dumps(data),
                                     timeout=self.timeout,
                                     verify=self.ca_cert)
        elif method == "PUT":
            response = requests.put(url,
                                    headers=headers,
                                    data=json.dumps(data),
                                    timeout=self.timeout,
                                    verify=self.ca_cert)
        elif method == "HEAD":
            response = requests.head(url,
                                     headers=headers,
                                     data=json.dumps(data),
                                     timeout=self.timeout,
                                     verify=self.ca_cert)
        elif method == "DELETE":
            response = requests.delete(url,
                                       headers=headers,
                                       data=json.dumps(data),
                                       timeout=self.timeout,
                                       verify=self.ca_cert)
        else:
            raise Exception("wrong HTTP method: %s" % method)

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        if response.text:
            return response.json()
        else:
            return None



def main():
    try:
        parser = ArgumentParser(prog="synergy",
                                epilog="Command-line interface to the"
                                       " OpenStack Synergy API.")

        # Global arguments
        parser.add_argument("--version", action="version", version="v1.0")

        parser.add_argument("--debug",
                            default=False,
                            action="store_true",
                            help="print debugging output")

        parser.add_argument("--os-username",
                            metavar="<auth-user-name>",
                            default=os.environ.get("OS_USERNAME"),
                            help="defaults to env[OS_USERNAME]")

        parser.add_argument("--os-password",
                            metavar="<auth-password>",
                            default=os.environ.get("OS_PASSWORD"),
                            help="defaults to env[OS_PASSWORD]")

        parser.add_argument("--os-user-domain-id",
                            metavar="<auth-user-domain-id>",
                            default=os.environ.get("OS_USER_DOMAIN_ID"),
                            help="defaults to env[OS_USER_DOMAIN_ID]")

        parser.add_argument("--os-user-domain-name",
                            metavar="<auth-user-domain-name>",
                            default=os.environ.get("OS_USER_DOMAIN_NAME"),
                            help="defaults to env[OS_USER_DOMAIN_NAME]")

        parser.add_argument("--os-project-name",
                            metavar="<auth-project-name>",
                            default=os.environ.get("OS_PROJECT_NAME"),
                            help="defaults to env[OS_PROJECT_NAME]")

        parser.add_argument("--os-project-id",
                            metavar="<auth-project-id>",
                            default=os.environ.get("OS_PROJECT_ID"),
                            help="defaults to env[OS_PROJECT_ID]")

        parser.add_argument("--os-project-domain-id",
                            metavar="<auth-project-domain-id>",
                            default=os.environ.get("OS_PROJECT_DOMAIN_ID"),
                            help="defaults to env[OS_PROJECT_DOMAIN_ID]")

        parser.add_argument("--os-project-domain-name",
                            metavar="<auth-project-domain-name>",
                            default=os.environ.get("OS_PROJECT_DOMAIN_NAME"),
                            help="defaults to env[OS_PROJECT_DOMAIN_NAME]")

        parser.add_argument("--os-auth-token",
                            metavar="<auth-token>",
                            default=os.environ.get("OS_AUTH_TOKEN", None),
                            help="defaults to env[OS_AUTH_TOKEN]")

        parser.add_argument('--os-auth-token-cache',
                            default=os.environ.get("OS_AUTH_TOKEN_CACHE",
                                                   False),
                            action='store_true',
                            help="Use the auth token cache. Defaults to False "
                                 "if env[OS_AUTH_TOKEN_CACHE] is not set")

        parser.add_argument("--os-auth-url",
                            metavar="<auth-url>",
                            default=os.environ.get("OS_AUTH_URL"),
                            help="defaults to env[OS_AUTH_URL]")

        parser.add_argument("--os-auth-system",
                            metavar="<auth-system>",
                            default=os.environ.get("OS_AUTH_SYSTEM"),
                            help="defaults to env[OS_AUTH_SYSTEM]")

        parser.add_argument("--bypass-url",
                            metavar="<bypass-url>",
                            dest="bypass_url",
                            help="use this API endpoint instead of the "
                                 "Service Catalog")

        parser.add_argument("--os-ca-cert",
                            metavar="<ca-certificate>",
                            default=os.environ.get("OS_CACERT", None),
                            help="Specify a CA bundle file to use in verifying"
                                 " a TLS (https) server certificate. Defaults "
                                 "to env[OS_CACERT]")
        """
        parser.add_argument("--insecure",
                            default=os.environ.get("INSECURE", False),
                            action="store_true",
                            help="explicitly allow Synergy's client to perform"
                                 " \"insecure\" SSL (https) requests. The "
                                 "server's certificate will not be verified "
                                 "against any certificate authorities. This "
                                 "option should be used with caution.")
        """

        args = parser.parse_args(sys.argv[1:])

        os_username = args.os_username
        os_password = args.os_password
        os_user_domain_id = args.os_user_domain_id
        os_user_domain_name = args.os_user_domain_name
        os_project_name = args.os_project_name
        os_project_domain_id = args.os_project_domain_id
        os_project_domain_name = args.os_project_domain_name
        os_auth_token = args.os_auth_token
        os_auth_token_cache = args.os_auth_token_cache
        os_auth_url = args.os_auth_url
        os_ca_cert = args.os_ca_cert
        bypass_url = args.bypass_url

        if not os_username:
            raise Exception("'os-username' not defined!")

        if not os_password:
            raise Exception("'os-password' not defined!")

        if not os_project_name:
            raise Exception("'os-project-name' not defined!")

        if not os_auth_url:
            raise Exception("'os-auth-url' not defined!")

        if not os_user_domain_name:
            os_user_domain_name = "default"

        if not os_project_domain_name:
            os_project_domain_name = "default"

        client = KeystoneClient(
            auth_url=os_auth_url,
            username=os_username,
            password=os_password,
            user_domain_id=os_user_domain_id,
            user_domain_name=os_user_domain_name,
            project_name=os_project_name,
            project_domain_id=os_project_domain_id,
            project_domain_name=os_project_domain_name,
            ca_cert=os_ca_cert)


        client.authenticate()
        token = client.getToken()

        result = {"apiVersion": "client.authentication.k8s.io/v1beta1",
                  "kind": "ExecCredential",
                  "status": {
                      "token": token.getId()
                  }
                 }
        print(json.dumps(result))
    except Exception as e:
        print("ERROR: %s" % e)
        sys.exit(1)


if __name__ == "__main__":
    main()
