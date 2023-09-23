from typing import Union
from fastapi import FastAPI

#models
from models.message_model import MessageApi


#data conection Mysql
from config.mysql_conection import hostMysql
from config.mysql_conection import userMysql
from config.mysql_conection import passwordMysql
from config.mysql_conection import dbMysql

#data conection Openai
from config.openai_conf import openai_apikey

#quita problema cors
from fastapi.middleware.cors import CORSMiddleware


import MySQLdb

#AGREGA CARACTERES DE ESCAPE EN SQL
from sqlescapy import sqlescape


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

openai.api_key  = openai_apikey

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

def get_completion_from_messages(messages, model="gpt-3.5-turbo", temperature=0):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature, # this is the degree of randomness of the model's output
    )
#     print(str(response.choices[0].message))
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

    #BUSCA LA EMPRESA
    mycursor.execute("SELECT id, empresa, promp1 FROM iar2_empresas WHERE empresa = '%s'" % (messagedata.enterprise))

    idempresa = 0
    promp1 = ''
    for row_empresa in mycursor.fetchall():
        idempresa = row_empresa[0]
        promp1 = row_empresa[2]


    ###########################################################################################################

    ## LIMPIAR REGISTRO EN CASO DE PROBAR NUEVAMENTE


    if messagedata.message == 'Limpiar registro':
         mycursor.execute("DELETE FROM iar2_captura WHERE typemessage = '%s' AND valuetype = '%s' AND identerprise = '%d' AND created_at BETWEEN DATE_ADD(NOW(), INTERVAL -1 HOUR) AND NOW()" % (messagedata.typemessage,messagedata.valuetype,idempresa))
         miConexion.commit()
         responsecustomer = 'Limpieza Realizada'
         
    else:
        #EVALUA LOS MENSAJES EXISTENTES EN LA ÚLTIMA HORA
        mycursor.execute("SELECT identification, typemessage, valuetype, message, messageresponseia, messageresponsecustomer, classification, sla, isclaim FROM iar2_captura WHERE typemessage = '%s' AND valuetype = '%s' AND identerprise = '%d' AND created_at BETWEEN DATE_ADD(NOW(), INTERVAL -1 HOUR) AND NOW() ORDER BY created_at" % (messagedata.typemessage,messagedata.valuetype,idempresa))

        mensajes_previos = 0
        messages = []
        content_line = {}

        content_line = {'role':'system', 'content':promp1}
        messages.append(content_line)
        for row in mycursor.fetchall():
            mensajes_previos = mensajes_previos + 1

            content_line = {'role':'user', 'content':row[3]}
            messages.append(content_line)

            content_line = {'role':'assistant', 'content':row[5]}
            messages.append(content_line)

        content_line = {'role':'user', 'content':messagedata.message}
        messages.append(content_line)
        #messagesjson = json.dumps(messages)
        ########################################################################################################

        # GUARDADO MENSAJE ENTRANTE
        sql = "INSERT INTO iar2_captura (typemessage, valuetype, message, identerprise) VALUES (%s, %s, %s, %s)"
        val = (messagedata.typemessage, messagedata.valuetype, sqlescape(messagedata.message), idempresa)
        mycursor.execute(sql, val)   
        miConexion.commit()

        idrow = mycursor.lastrowid
        idrowstr = str(idrow)

        
        if mensajes_previos > 0:
            response = get_completion_from_messages(messages,temperature=1)
        else:
            response = 'Sin Respuesta'
        
        classification = "Área de Ventas"
        sla = "48 Horas"
        isclaim = 'Si'
        today = date.today()
        identification = "R-" + today.strftime("%y%m%d"+str(idrowstr.zfill(4)))

        if response == 'Sin Respuesta':
            responsecustomer = 'Hola! soy el asistente virtual del servicio de Reclamos Iars2!.😎. Soy un asistente creado con Inteligencia Artificial preparado para atender a tus necesidades. Puedes indicar tu situación, y gestionaremos correctamente para dar una respuesta oportuna.  Para comenzar, favor indícame tu nombre'
            typeresponse = 'Saludo'
        else:
            responsecustomer = "Su reclamo identificado como " + identification + " ha sido generado con éxito.  Su solicitud fue derivada al " + classification + ", y será resuelta en un plazo máximo de " + sla + "."
            typeresponse = 'Interaccion'
            responsecustomer = response


    # response = ''
        # GUARDADO RESPUESTA
        sqlresponse =  "UPDATE iar2_captura SET identification = '%s', messageresponseia = '%s', messageresponsecustomer = '%s', typeresponse = '%s', classification ='%s', sla = '%s', isclaim = '%s' WHERE id = %d" % (identification, sqlescape(response), sqlescape(responsecustomer), typeresponse, classification, sla, isclaim, idrow)
        #valresponse = (messagedata.typemessage, messagedata.valuetype, messagedata.message, messagedata.enterprise)
        mycursor.execute(sqlresponse)   
        miConexion.commit()

    
    #return {'respuesta': promp1}
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
