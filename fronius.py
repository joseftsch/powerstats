#!/usr/bin/env python3

import configparser
import requests
import sys
import mysql.connector
from datetime import date
from influxdb import InfluxDBClient
import logging

def main():
    logging.basicConfig(format='%(asctime)s %(module)s %(levelname)s %(funcName)s %(message)s', level=logging.INFO)
    logging.info("Fronius Power gathering startup!")
    config = configparser.ConfigParser()
    try:
        config.read("/config.ini")
        if len(config) < 2:
            raise Exception
    except Exception as e:
        logging.error("Failed to read config file", exc_info=True)
        sys.exit()

    url=config['general']['url']

    # get pv data
    res={}
    data=GetData(url)
    if not data or not isinstance(data, dict):
        logging.error("We did not receive a valid response from Inverter")
        sys.exit()
    try:
        raw_current_pv_watt = data['Body']['Data']['Site']['P_PV']
        if raw_current_pv_watt:
            res['current_pv_watt'] = int(raw_current_pv_watt)
        else:
            res['current_pv_watt'] = 0
        res['current_consumption_from_grid_watt'] = float(data['Body']['Data']['Site']['P_Grid'])
        res['current_consumption_house_watt'] = float(data['Body']['Data']['Site']['P_Load'])
        res['energy_pv_today_wh'] = float(data['Body']['Data']['Site']['E_Day'])
        res['energy_pv_year_wh'] = float(data['Body']['Data']['Site']['E_Year'])
        res['energy_pv_total_wh'] = float(data['Body']['Data']['Site']['E_Total'])
        res['autonomy_percent'] = int(data['Body']['Data']['Site']['rel_Autonomy'])
        raw_selfconsumption_percent = data['Body']['Data']['Site']['rel_SelfConsumption']
        if raw_selfconsumption_percent:
            res['selfconsumption_percent'] = int(raw_selfconsumption_percent)
        else:
            res['selfconsumption_percent'] = 0
    except Exception as e:
        logging.error("Unable to assign values ... maybe element missing. Exception: {}".format(e), exc_info=True)
        sys.exit()

    #verify that we have only integers in dict
    try:
        for k,v in res.items():
            if not isinstance(v, int) and not isinstance(v, float):
                logging.error("{} is not an integer or float. value: {}".format(str(k),str(v)))
                sys.exit()
    except Exception as e:
        logging.error("Something went wrong. Exception: {}".format(e), exc_info=True)
        sys.exit()

    #insert data into mysql
    if 'stdout' in config.sections():
        logging.info("Print to Stdout")
        logging.info(data)
        logging.info(res)

    #insert data into mysql
    if 'mysql' in config.sections():
        logging.info("Insert into MySQL")
        status=MySQLInsert(res,config)
        if not status:
            logging.error("Something went wrong during MySQL insert")
            sys.exit()

    #insert data into influxdb
    if 'influxdb' in config.sections():
        logging.info("Insert into InfluxDB")
        status=InfluxDBInsert(res,config)
        if not status:
            logging.error("Something went wrong during influxdb insert")
            sys.exit()

    logging.info("Fronius Power gathering shutdown!")

def GetData(url:str)->dict:
    try:
        r = requests.get(url, timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.error("Unable to request data. Exception: {}".format(str(e)), exc_info=True)
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
        logging.error("Error during InfluxDB connection. Exception: {}".format(str(e)), exc_info=True)
        return False
    return True

def MySQLInsert(res:dict,config:configparser)->bool:
    mysqltable="power_{}{}".format(date.today().year,date.today().month)
    placeholder = ", ".join(["%s"] * len(res))
    stmt = "INSERT INTO {} ({}) values ({});".format(mysqltable, ",".join(res.keys()), placeholder)

    #establish mysql connection
    try:
        mydb = mysql.connector.connect(host=config['mysql']['mysqlhost'],user=config['mysql']['mysqluser'],password=config['mysql']['mysqlpassword'],database=config['mysql']['mysqldb'])
        mycursor = mydb.cursor()
    except mysql.connector.Error as e:
        logging.error("Error during MySQL connection. Exception: {}".format(str(e)), exc_info=True)
        return False

    # #insert into db
    try:
        mycursor.execute(stmt, list(res.values()))
        mydb.commit()
        mydb.close()
    except Exception as e:
        logging.error("Error during insert of data into MySQL. Exception: {}".format(str(e)), exc_info=True)
        return False

    return True

if __name__ == "__main__":
    main()