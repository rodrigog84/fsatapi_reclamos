from typing import Union
from fastapi import FastAPI

#models
from models.message_model import MessageApi


#data conection Mysql
from config.mysql_conection import hostMysql
from config.mysql_conection import userMysql
from config.mysql_conection import passwordMysql
from config.mysql_conection import dbMysql

#quita problema cors
from fastapi.middleware.cors import CORSMiddleware


import MySQLdb


import json
import requests

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from os import getcwd
from datetime import date


import os
import openai
import tiktoken
#from dotenv import load_dotenv, find_dotenv

openai.api_key  = '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'

# Creación de una aplicación FastAPI:
app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_completion(prompt, model="gpt-3.5-turbo"):
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message["content"]


@app.get('/')
def read_root():
    return {'Hello': 'World!!!'}


#recepcion de reclamos
@app.post('/enviareclamo/')
def enviareclamo(messagedata: MessageApi):

    #CONEXION
    miConexion = MySQLdb.connect( host=hostMysql, user= userMysql, passwd=passwordMysql, db=dbMysql )
    mycursor = miConexion.cursor()

    # GUARDADO MENSAJE ENTRANTE
    sql = "INSERT INTO iar2_captura (typemessage, valuetype, message, enterprise) VALUES (%s, %s, %s, %s)"
    val = (messagedata.typemessage, messagedata.valuetype, messagedata.message, messagedata.enterprise)
    mycursor.execute(sql, val)   
    miConexion.commit()

    idrow = mycursor.lastrowid
    idrowstr = str(idrow)
    response = get_completion(messagedata.message)
    
    classification = "Área de Ventas"
    sla = "48 Horas"
    isclaim = 'Si'
    today = date.today()
    identification = "R-" + today.strftime("%y%m%d"+str(idrowstr.zfill(4)))
    responsecustomer = "Su reclamo identificado como " + identification + " ha sido generado con éxito.  Su solicitud fue derivada al " + classification + ", y será resuelta en un plazo máximo de " + sla + "."


   # response = ''
    # GUARDADO RESPUESTA
    sqlresponse =  "UPDATE iar2_captura SET identification = '%s', messageresponseia = '%s', messageresponsecustomer = '%s', classification ='%s', sla = '%s', isclaim = '%s' WHERE id = %d" % (identification, response, responsecustomer, classification, sla, isclaim, idrow)
    #valresponse = (messagedata.typemessage, messagedata.valuetype, messagedata.message, messagedata.enterprise)
    mycursor.execute(sqlresponse)   
    miConexion.commit()


    return {'respuesta': responsecustomer}



#recepcion de reclamos
@app.get('/getreclamos/')
def getreclamos(enterprise: str):

    #CONEXION
    miConexion = MySQLdb.connect( host=hostMysql, user= userMysql, passwd=passwordMysql, db=dbMysql )
    mycursor = miConexion.cursor()

    mycursor.execute("SELECT identification, typemessage, valuetype, message, messageresponseia, messageresponsecustomer, classification, sla, isclaim FROM iar2_captura WHERE enterprise = '%s'" % (enterprise))
    reclamos = []
    content = {}

    #for identification, typemessage, valuetype, message, messageresponseia, messageresponsecustomer, classification, sla, isclaim in mycursor.fetchall():
    #    content = {"Identificador":identification,"Tipo Mensaje":typemessage,"Valor Tipo Mensaje":valuetype,"Mensaje":message,"Mensaje Respuesta IA":messageresponseia,"Mensaje Respuesta Cliente":messageresponsecustomer,"Clasificacion":classification,"SLA":sla,"Es Reclamo":isclaim}
    #    reclamos.append(content)
    for row in mycursor.fetchall():
        content = {"identificador":row[0],"Tipo Mensaje":row[1],"Valor Tipo Mensaje":row[2],"Mensaje":row[3],"Mensaje Respuesta IA":row[4],"Mensaje Respuesta Cliente":row[5],"Clasificacion":row[6],"SLA":row[7],"Es Reclamo":row[8]}
        reclamos.append(content)
    #resultjson = json.dumps(reclamos)
    miConexion.close()
    return {'data' : reclamos}
