#!/usr/bin/env python3

import configparser
import requests
import sys
import mysql.connector
from configparser import ConfigParser
from datetime import date
from influxdb import InfluxDBClient

def main():
    config = ConfigParser()
    try:
        config.read("/config.ini")
    except Exception as e:
        print("Can not read config file - exit")
        sys.exit()

    url=config['general']['url']

    # get pv data
    res={}
    data=GetData(url)
    try:
        res['inverter_day_energy_wh'] = data['Body']['Data']['DAY_ENERGY']['Values']['1']
        res['inverter_poc_w'] = data['Body']['Data']['PAC']['Values']['1']
        res['inverter_total_energy_wh'] = data['Body']['Data']['TOTAL_ENERGY']['Values']['1']
        res['inverter_year_energy_wh'] = data['Body']['Data']['TOTAL_ENERGY']['Values']['1']
    except Exception as e:
        print("Unable to assign values ... maybe element missing. Exception: {}".format(str(e)))
        sys.exit()

    #verify that we have only integers in dict
    try:
        for k,v in res.items():
            if not isinstance(v, int):
                print("{} is not an integer. value: {}".format(str(k),str(v)))
                sys.exit()
    except Exception as e:
        print("Something went wrong. Exception: {}".format(str(e)))
        sys.exit()

    #insert data into mysql
    if 'mysql' in config.sections():
        status=MySQLInsert(res,config)
        if not status:
            print("Something went wrong during MySQL insert")
            sys.exit()

    #insert data into influxdb
    if 'influxdb' in config.sections():
        status=InfluxDBInsert(res,config)
        if not status:
            print("Something went wrong during InfluxDB insert")
            sys.exit()

def GetData(url:str)->dict:
    try:
        r = requests.get(url, timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Unable to request data. Exception: {}".format(str(e)))
        sys.exit()

def InfluxDBInsert(res:dict,config:configparser)->bool:
    datalist = []
    data = {}
    data["measurement"] = "power"
    data["fields"] = {}

    for k,v in res.items():
        data["fields"][k] = v

    datalist.append(data.copy())

    client = InfluxDBClient(
        config['influxdb']['influxdbhost'],
        config['influxdb']['influxdbport'],
        config['influxdb']['influxdbuser'],
        config['influxdb']['influxdbpassword'],
        config['influxdb']['influxdbdb'])
    try:
        client.write_points(datalist)
        client.close()
    except Exception as e:
        print("Error during InfluxDB connection. Exception: {}".format(str(e)))
        return False
    return True

def MySQLInsert(res:dict,config:configparser)->bool:
    mysqltable="power_{}{}".format(date.today().year,date.today().month)
    sql='INSERT INTO {} (inverter_day_energy_wh, inverter_poc_w, inverter_total_energy_wh, inverter_year_energy_wh) VALUES (%s, %s, %s, %s)'.format(mysqltable)
    val=res['inverter_day_energy_wh'],res['inverter_poc_w'],res['inverter_total_energy_wh'],res['inverter_year_energy_wh']

    #establish mysql connection
    try:
        mydb = mysql.connector.connect(host=config['mysql']['mysqlhost'],user=config['mysql']['mysqluser'],password=config['mysql']['mysqlpassword'],database=config['mysql']['mysqldb'])
        mycursor = mydb.cursor()
    except mysql.connector.Error as e:
        print("Error during MySQL connection. Exception: {}".format(str(e)))
        return False

    # #insert into db
    try:
        mycursor.execute(sql, val)
        mydb.commit()
        mydb.close()
    except Exception as e:
        print("Error during inserting data into MySQL. Exception: {}".format(str(e)))
        return False

    return True

if __name__ == "__main__":
    main()