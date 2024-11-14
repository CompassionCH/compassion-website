import json
import re

from lxml import html
from requests import Response
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo.service import wsgi_server
from odoo.tests.common import HttpCase


class TestMyAccountController(HttpCase):
    def setUp(self):
        super(TestMyAccountController, self).setUp()

        self.user_login = "test"
        self.user_password = "password"
        self.user = self.env["res.users"].create(
            {
                "login": self.user_login,
                "password": self.user_password,
                "name": "Test User",
            }
        )

        self.werkzeug_environ = {"REMOTE_ADDR": "127.0.0.1"}
        self.test_client = Client(wsgi_server.application, BaseResponse)
        self.test_client.get("/web/session/logout")
        self.dbname = self.env.cr.dbname

    def html_doc(self, response):
        """Get an HTML LXML document."""
        return html.fromstring(response.data)

    def csrf_token(self, response):
        """Get a valid CSRF token."""
        doc = self.html_doc(response)
        return doc.xpath("//input[@name='csrf_token']")[0].get("value")

    def get_request(self, url, data=None):
        return self.test_client.get(url, query_string=data, follow_redirects=True)

    def post_request(self, url, data=None):
        return self.test_client.post(
            url, data=data, follow_redirects=False, environ_base=self.werkzeug_environ
        )

    def json_post(self, route: str, data: dict, headers: dict) -> Response:
        json_headers = {"Content-Type": "application/json"}
        return self.url_open(
            route, data=json.dumps(data), headers={**headers, **json_headers}
        )

    def get_session_id(self, response):
        self.assertIn("Set-Cookie", response.headers)
        cookie = response.headers["Set-Cookie"]
        print(cookie)
        self.assertIn("session_id", cookie)
        session_id = re.search(r"session_id=([^;]+)", cookie).group(1)
        self.assertNotEqual(session_id, "")
        return session_id

    def login(self):
        # Get login CSRF token
        response = self.get_request("/web/", data={"db": self.dbname})

        data = {
            "login": self.user.login,
            "password": self.user.password,
            "csrf_token": self.csrf_token(response),
            "db": self.dbname,
        }
        response = self.post_request("/web/login/", data=data)

        auth_session_id = self.get_session_id(response)
        return auth_session_id

    def test_my_letter_preview(self):
        session_id = self.login()

        resp = self.json_post(
            "/my/letter/123/send",
            data={"body": "test"},
            headers={"Cookie": f"session_id={session_id}"},
        )
