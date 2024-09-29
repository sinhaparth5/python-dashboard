import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from prometheus_client import generate_latest, Counter, Histogram
from src.couchbase import CouchbaseClient
from flask import Flask, request, render_template, make_response
from flask_restx import Api, Resource, fields
import logging
import time

app = Flask(__name__)

env_path = "./app/src/.env"
load_dotenv(env_path)
REQUEST_COUNT = Counter('app_request_count', 'Application Request Count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'Application Request Latency', ['method', 'endpoint', 'http_status'])

api = Api(app)
nsCourse = api.namespace('/pyuniversity', "CRUD operations for Courses")

courseInsert = api.model(
    "CourseInsert",
    {
        "courseName": fields.String(required=True, description="Course Name"),
        "courseId": fields.String(required=True, description="Course's Unique ID"),
        "duration": fields.Integer(required=True, description="Course Price"),
        "description": fields.String(required=False, description="Description of course"),
        "author": fields.String(required=True, description="Course Author"),
        "url" : fields.String(required=True, description="Url of the Course")
    },
)

course = api.model(
    "Course",
    {
        "id": fields.String(required=True, description="Course's system generated Id"),
        "courseName": fields.String(required=True, description="Course Name"),
        "courseId": fields.String(required=True, description="Course's Unique ID"),
        "duration": fields.Integer(required=True, description="Course Price"),
        "description": fields.String(required=False, description="Description of course"),
        "author": fields.String(required=True, description="Course Author"),
        "url" : fields.String(required=True, description="Url of the Course"),
        "createdAt" : fields.String(required=True, description="Time course is created")
    },
)

@nsCourse.route("/courses")
class Courses(Resource):
    # tag::post[]
    @nsCourse.doc(
        "Create Course",
        reponses={201: "Created", 500: "Unexpected Error"},
    )
    @nsCourse.expect(courseInsert, validate=True)
    @nsCourse.marshal_with(course)
    def post(self):
        status=None
        start_time = time.time()
        try:
            logger.info("Creating Course")
            data = request.json
            id = uuid.uuid4().__str__()
            data["id"] = id
            data["createdAt"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            cb.insert(id,data)
            logger.info("Created Course Successfully")
            status=201
            return data, 201
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            status=500
            return f"Unexpected error: {e}", 500
        finally:
            REQUEST_LATENCY.labels('POST', '/courses',status).observe(time.time() - start_time)

@nsCourse.route("/home")
class CourseHome(Resource):
    @nsCourse.doc(
        "Home Page",
        reponses={200: "Success", 404: "Not Found", 500: "Unexpected Error"},
    )
    def get(self):
        status=None
        try:
            logger.info("Rendering the Home Page")
            headers = {'Content-Type': 'text/html'}
            status=200
            return make_response(render_template('home.html'), 200,headers)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            status=500
            return f"Unexpected error: {e}", 500
        finally:
            REQUEST_COUNT.labels('GET', '/home', status).inc()

    def post(self):
        status=None
        start_time = time.time()
        try:
            logger.info("Searching for the requested course")
            courseName = request.form['courseName']
            logger.info(courseName)
            data = cb.query(courseName)
            data = [x for x in data]
            headers = {'Content-Type': 'text/html'}
            result = len(data)
            if result==0:
                status=404
            else:
                status=200
            return make_response(render_template('result.html',data=data,result=result), 200, headers)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            status=500
            return f"Unexpected error: {e}", 500
        finally:
            REQUEST_COUNT.labels('POST', '/home', status).inc()
            REQUEST_LATENCY.labels('POST', '/home',status).observe(time.time() - start_time)

@app.route("/metrics")
def metrics():
    logger.info("Getting Metrics")
    return generate_latest()

db_info = {
    "host": os.getenv("DB_HOST"),
    "bucket": os.getenv("BUCKET"),
    "collection": os.getenv("COLLECTION"),
    "scope": os.getenv("SCOPE"),
    "username": os.getenv("DB_USERNAME"),
    "password": os.getenv("PASSWORD"),
}

format = '%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s'
logging.basicConfig(filename="./app/logs/audit.log",filemode='a',format=format,datefmt='%H:%M:%S',level = logging.DEBUG)
logger = logging.getLogger()
cb = CouchbaseClient(*db_info.values())
cb.connect()

if __name__ == "__main__":
    logger.debug("Application Started ...")
    app.run(debug=True,port=5000)