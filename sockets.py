#!/usr/bin/env python
# coding: utf-8

# Code for Client class, read_ws, and subscribe_socket were based on code from the Cmput 404 slides WebSocket examples: https://github.com/uofa-cmput404/cmput404-slides/blob/master/examples/WebSocketsExamples/chat.py
# This project was forked from: https://github.com/abramhindle/CMPUT404-assignment-websockets

# Copyright 2021 Michael Boisvert
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, redirect
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()

    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())

    def world(self):
        return self.space

class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()

clients = list()

myWorld = World()

def set_listener( entity, data ):
    ''' do something with the update ! '''
    for client in clients:
        client.put(json.dumps({entity:data}))

myWorld.add_set_listener( set_listener )

@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return redirect("/static/index.html")

def read_ws(ws, client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    try:
        while True:
            msg = ws.receive()
            print("WS RECV: %s" % msg)
            if (msg is not None):
                #print(msg)
                object = json.loads(msg)
                # Update the world
                for entity, data in object.items():
                    if entity in myWorld.world():
                        #print("update")
                        if "colour" in entity:
                            myWorld.update(entity, "colour", data["colour"])
                        if "radius" in entity:
                            myWorld.update(entity, "radius", data["radius"])
                        if "x" in entity:
                            myWorld.update(entity, "x", data["x"])
                        if "y" in entity:
                            myWorld.update(entity, "y", data["y"])
                    else:
                        myWorld.set(entity, data)
                # Update the clients
                myWorld.update_listeners(entity)

            else:
                print("no message")
                pass
    except Exception as e:
        print("EXCEPTION")
        print(e)
        '''Done'''

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    client = Client()
    clients.append(client)
    # Tell client about current world
    for entity in myWorld.world():
        myWorld.update_listeners(entity)
    g = gevent.spawn(read_ws, ws, client) # read from websocket
    try:
        while True:
            # notify client of update
            msg = client.get()
            ws.send(msg)
    except Exception as e:
        print("WS Error %s" % e)
    finally:
        print("ENDING CONNECTION")
        clients.remove(client)
        gevent.kill(g)


# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    entity_data = flask_post_json()
    if request.method == "POST":
        if entity in myWorld.world():
            print("update")
            myWorld.update(entity, "colour", entity_data["colour"])
            myWorld.update(entity, "radius", entity_data["radius"])
            myWorld.update(entity, "x", entity_data["x"])
            myWorld.update(entity, "y", entity_data["y"])
        else:
            myWorld.set(entity, entity_data)
            print("set")
    elif request.method == "PUT":
        myWorld.set(entity, entity_data)
    return myWorld.get(entity)

@app.route("/world", methods=['POST','GET'])
def world():
    '''you should probably return the world here'''
    if request.method == "POST":
        new_world = flask_post_json()
        myWorld.clear()
        for key in new_world:
            myWorld.set(key, new_world[key])
    return myWorld.world()

@app.route("/entity/<entity>")
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return myWorld.get(entity)


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    myWorld.clear()
    return myWorld.world()



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
