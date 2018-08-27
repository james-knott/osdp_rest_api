"""
Open Source Development Platform.

"""
import osdpbase
import logging
import sys
#from ruamel.yaml import YAML
import argparse
from flask import Flask, jsonify, request
from flask_restful import Resource, Api
from flask_jwt import JWT, jwt_required
from security import authenticate, identity
from user import UserRegister
from git import Repo
from git import RemoteProgress
import sqlite3
import socket
import multiprocessing
import gunicorn.app.base
from gunicorn.six import iteritems

__author__ = "James Knott (@Ghettolabs)"
__copyright__ = "Copyright 2018 James Knott"
__credits__ = ["James Knott"]
__license__ = "Apache License, 2.0"
__version__ = "0.0.3"
__maintainer__ = "James Knott"
__email__ = "devops@ghettolabs.io"
__status__ = "Development"

"""
post this json to endpoint to create project
    {
        "platform": "vagrant",
        "linux": "amazon",
        "username": "jknott",
        "password": "password",
        "project": "osdp",
        "github": "https://github.com/james-knott/amazon.git"
    }
"""
REMOTE_SERVER = "www.github.com"


def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1


def setup_logging():
    logger = logging.getLogger()
    for h in logger.handlers:
        logger.removeHandler(h)
    h = logging.StreamHandler(sys.stdout)
    FORMAT = "[%(levelname)s %(asctime)s %(filename)s:%(lineno)s - %(funcName)21s() ] %(message)s"
    h.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)
    return logger

def is_connected(REMOTE_SERVER):
    try:
        host = socket.gethostbyname(REMOTE_SERVER)
        s = socket.create_connection((host, 80), 2)
        print("Here is the ip address the server is running on {} ".format([l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] \
        if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]))
        return True
    except:
        print("Not connected to the internet")
    return False
def init_db():
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    create_table = "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username text, password text)"
    cursor.execute(create_table)
    create_table = "CREATE TABLE IF NOT EXISTS projects (name text PRIMARY KEY, platform text, linux text, username text, password text, project text, github text)"
    cursor.execute(create_table)
    try:
        cursor.execute("INSERT INTO projects VALUES ('ahead', 'vagrant', 'amazon', 'jknott', 'password', 'osdp', 'https://github.com/james-knott/amazon.git')")
    except:
        pass
    connection.commit()
    connection.close()

class MyProgressPrinter(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message='Pulling config file from github'):
        print(op_code, cur_count, max_count, cur_count / (max_count or 100.0), message or "Downloading....")


class StandaloneApplication(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        config = dict([(key, value) for key, value in iteritems(self.options)
                       if key in self.cfg.settings and value is not None])
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def server():
    init_db()

    app = Flask(__name__)
    app.secret_key = 'osdp'
    api = Api(app)
    jwt = JWT(app, authenticate, identity)


    class Project(Resource):
        #@jwt_required()
        def get(self, name):
            connection = sqlite3.connect('data.db')
            cursor = connection.cursor()
            query = "SELECT * FROM projects WHERE name=?"
            result = cursor.execute(query, (name,))
            row = result.fetchone()
            connection.close()

            if row:
                return {'project': {'name': row[0], 'platform': row[1], 'linux': row[2], 'username': row[3], 'password': row[4], 'project': row[5], 'github': row[6]}}
            return {'message': 'Project not found'}, 404

        @classmethod
        def find_by_name(cls, name):
            connection = sqlite3.connect('data.db')
            cursor = connection.cursor()
            query = "SELECT * FROM projects WHERE name=?"
            result = cursor.execute(query, (name,))
            row = result.fetchone()
            connection.close()
            if row:
                return {'project': {'name': row[0], 'platform': row[1], 'linux': row[2], 'username': row[3], 'password': row[4], 'project': row[5], 'github': row[6]}}


        def post(self, name):
            if self.find_by_name(name):
                return {'message': 'The project {} already exists'.format(name)}, 400

            data = request.get_json()
            project = self.find_by_name(name)
            updated_project = {'name': name, 'platform': data['platform'], 'linux': data['linux'], 'username': data['username'], 'password': data['password'], 'project': data['project'], 'github': data['github']}

            if project is None:
                try:
                    self.insert(updated_project)
                except:
                    return {"message": "An error occurred inserting the project."}, 500
            else:
                try:
                    self.update(updated_project)
                except:
                    return {"message": "An error occurred updating the project."}, 500

            return updated_project, 201

        def put(self, name):
            data = request.get_json()
            project = self.find_by_name(name)
            updated_project = {'name': name, 'platform': data['platform'], 'linux': data['linux'], 'username': data['username'], 'password': data['password'], 'project': data['project'], 'github': data['github']}

            if project is None:
                try:
                    self.insert(updated_project)
                except:
                    return {"message": "An error occurred inserting the project."}, 500
            else:
                try:
                    self.update(updated_project)
                except:
                    return {"message": "An error occurred updating the project."}, 500

            return updated_project, 201


        @classmethod
        def insert(cls, project):
            connection = sqlite3.connect('data.db')
            cursor = connection.cursor()
            query = "INSERT INTO projects VALUES (?,?,?,?,?,?,?)"
            cursor.execute(query, (project['name'], project['platform'], project['linux'], project['username'], project['password'], project['project'], project['github']))
            connection.commit()
            connection.close()


        def delete(self, name):
            connection = sqlite3.connect('data.db')
            cursor = connection.cursor()
            query = "DELETE FROM projects WHERE name=?"
            cursor.execute(query, (name,))
            connection.commit()
            connection.close()

            return {'message': 'Project Deleted'}

        def update(cls, project):
            connection = sqlite3.connect('data.db')
            cursor = connection.cursor()
            query = "UPDATE projects SET platform=?, linux=?, username=?, password=?, project=?, github=? WHERE name=?"
            cursor.execute(query, (project['platform'], project['linux'], project['username'], project['password'], project['project'], project['github'], project['name']))
            connection.commit()
            connection.close()





    class ProjectList(Resource):
        def get(self):
            connection = sqlite3.connect('data.db')
            cursor = connection.cursor()
            query = "SELECT * FROM projects"
            result = cursor.execute(query)
            projects = []
            for row in result:
                projects.append({'name': row[0], 'platform': row[1], 'linux': row[2], 'username': row[3], 'password': row[4], 'project': row[5], 'github': row[6]})

            connection.close()

            return {'projects': projects}

    api.add_resource(Project, '/project/<string:name>')
    api.add_resource(ProjectList, '/projects')
    api.add_resource(UserRegister, '/register')


    #app.run(port=5000)
    options = {
        'bind': '%s:%s' % ('127.0.0.1', '8080'),
        'workers': number_of_workers(),
    }
    StandaloneApplication(app, options).run()

if __name__ == "__main__":
    logger = setup_logging() # sets up logging
    logger.info("Welcome to Open Source Development Platform!")
    is_connected(REMOTE_SERVER) # checks to see if connected to the internet
    test = osdpbase.OSDPBase()
    # sets up command line arguments
    parser = argparse.ArgumentParser(description='Open Source Development Platform')
    parser.add_argument("--init","-i", required=False, dest='init',action='store_true',help='Initialize new project folder')
    parser.add_argument("--new","-n", required=False, dest='new',action='store_true',help='Create new project from template file')
    parser.add_argument("--update","-u", required=False, dest='update',action='store_true',help='Update settings')
    parser.add_argument("--backup","-b", required=False,dest='backup',action='store',help='Sync project to backup device')
    parser.add_argument("--destroy","-e", required=False,dest='destroy',action='store',help='Delete project from folder')
    parser.add_argument("--start","-s", required=False,dest='start',action='store',help='Start services')
    parser.add_argument("--stop","-d", required=False,dest='stop',action='store',help='Stop services')
    # run in server mode only
    parser.add_argument("--server","-p", required=False,dest='server',action='store_true',help='Start server mode')
    result = parser.parse_args()

    if result.init:
        logger.info("Pulling down yaml file so you can customize your environment!")
        test.init()
    elif result.new:
        test.new()
    elif result.update:
        test.update()
    elif result.backup:
        logger.info("We are backing up all your projects to S3!")
        test.backup()
    elif result.destroy:
        project = result.destroy
        logger.info("We are destroying your vagrant box now!")
        test.destroy(projectname=project)
    elif result.start:
        project = result.start
        logger.info("We are starting your development environment now!")
        test.start(projectname=project)
    elif result.stop:
        project = result.stop
        logger.info("We are stopping your vagrant box now!")
        test.stop(projectname=project)
    elif result.server:
        server()



