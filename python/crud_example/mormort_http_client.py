"""
Author: Eduardo Shibukawa

This module contais the authenticated client http class of a mORMot server.
    - Authentication and connection to a mormot server.
    - Create valid requests to a authenticated mormot server.
"""
import urllib.parse
import hashlib
import binascii
import requests
import secrets

from session import Session
from utils_duh import to_hex8_str


class AutheticatedHTTPClient:
    """
    Class AutheticatedHTTPClient manage the login and the session_signature generation.

    Attributes:
        host (str): host name, example: 'localhost'
        port (str): port, example: '888'
        root (str): root name, example: 'root'
        base_url (str): concatenation of host and port, example: 'http://localhost:888'
        session (Session): The current logged session, if no session is logged then it's None.
    """

    def __init__(self, host, port, root):
        self.host = host
        self.port = port
        self.root = root
        self.base_url = "http://{}:{}".format(host, port)
        self.session = None        

    def __get_server_nonce__(self, user):
        url = "{}/{}/Auth?Username={}".format(self.base_url, self.root, user)
        return requests.get(url).json()['result']

    @staticmethod
    def __generate_client_nonce__():
        return secrets.token_hex(32).upper()

    def login(self, user, password_hash):
        """
        Login function authenticate the user
        and creates a new session

        Args:
            user (str): login user name.
            password_hash (str): hashed password of the user.

        Returns:
            A session if successful, None otherwise.
        """
        server_nonce = self.__get_server_nonce__(user)
        client_nonce = self.__generate_client_nonce__()

        sha256password = ''.join([
            self.root,
            server_nonce,
            client_nonce,
            user,
            password_hash,
        ]).encode()

        sha256password = hashlib.sha256(sha256password).hexdigest().upper()

        url = "{}/{}/Auth?Username={}&Password={}&ClientNonce={}".format(
            self.base_url, self.root, user, sha256password, client_nonce)

        resp = requests.get(url)
        if resp.status_code == 200:
            self.session = Session(resp.json()['result'], password_hash)
            return self.session
        return None

    def add_session_signature(self, method, parameters):
        """
        add_session_signature function add the session_signature to the URL,
        it's needed to authenticated the session.

        Args:
            method (str): method of the URL, example: MyMethod.
            parameters (dic): the parameters of the method, example: {'param1': 1}
        Returns:
            The mehod URL with the sesssion_signature parameter.

        >> Binary Right Shift
        https://www.tutorialspoint.com/python/bitwise_operators_example.html
        """
        url_without_sesssion_signature = "/".join([
            self.root,
            "?".join([method, urllib.parse.urlencode(parameters)]) if parameters else method
        ])

        nonce = to_hex8_str(self.session.get_tick_count() >> 8)

        crc = binascii.crc32(nonce.encode(), self.session.private_salt_hash)
        crc = binascii.crc32(url_without_sesssion_signature.encode(), crc)

        parameters['session_signature'] = "".join([
            self.session.id_hex, nonce,
             to_hex8_str(crc)
        ])

        return "/".join([
            self.root,
            "?".join([method, urllib.parse.urlencode(parameters)])
        ])

    def request(self, method, parameters):
        """
        requests function request the method with the parameteres

        Args:
            method (str): method of the URL, example: MyMethod.
            parameters (dic): the parameters of the method, example: {'param1': 1}
        Returns:
            The mehod request.
        """
        url = "/".join([
            self.base_url,
            self.add_session_signature(method, parameters)
        ])
        
        return requests.get(url)

    def post(self, method, json_value):
        """
        post function submits the data using POST HTTP method with the parameteres
        Args:
            method (str): method of the URL, example: MyMethod.
            json_value: json value to post, example '{id: 1}'
        Returns:
            The post response.
        """
        url = "/".join([
            self.base_url,
            self.add_session_signature(method, {})
        ])
        
        return requests.post(url, data=json_value)  
    
    def put(self, method, json_value):
        """
        put function submits the data using POST HTTP method with the parameteres

        Args:
            method (str): method of the URL, example: MyMethod.
            json_value: json value to PUT, example '{id: 1}'
        Returns:
            The post response.
        """
        url = "/".join([
            self.base_url,
            self.add_session_signature(method, {})
        ])        
        return requests.put(url, data=json_value)  

    def delete(self, method):
        """
        delete function submits the data using DELETE HTTP method with the parameteres

        Args:
            method (str): method of the URL, example: MyMethod.
        Returns:
            The post response.
        """
        url = "/".join([
            self.base_url,
            self.add_session_signature(method, {})
        ])
        
        return requests.delete(url)  

    def xget(self, data):
        """
        xget function request the method using GET HTTP method with a body parameter 
        Args:
            method (str): method of the URL, example: MyMethod.
            data (str): the body data value, example 'select Dest from DestList'
        Returns:
            The mehod request.
        """
        url = "/".join([
            self.base_url, 
            self.add_session_signature('', {})
        ])

        return requests.Session().send(
            requests.Request('GET', url, data=data).prepare()
        )