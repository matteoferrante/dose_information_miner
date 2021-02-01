#!/usr/bin/env python
# coding: utf-8



import pandas as pd
import numpy as np
import unidecode
import argparse

"""Script to integrate the  information from angio report and telemis code """

###to run the script write: python angio_information_miner.py -d [directory] -o [outputname]

print(f"[INFO] Dose information miner for structured dose report of TC scans")
parser = argparse.ArgumentParser()
parser.add_argument("-a", "--angiography_report",required=True,help="path of angiographic csv report obtained using angio_information_miner script")
parser.add_argument("-t", "--telemis_data",required=True,help="path of telemis csv information of angiographic exams")

parser.add_argument("-o", "--output",required=True,help="name of the output csv file")

args = vars(parser.parse_args())



angio_data=args["angiography_report"]
telemis_data=args["telemis_data"]


print(f"[INFO] reading angiographic report from {angio_data} and telemis information from {telemis_data}")


angio=pd.read_csv(angio_data)




telemis=pd.read_csv(telemis_data,encoding = "ISO-8859-1",error_bad_lines=False,sep=";")




angio["Data"]=angio["Study Date"].apply(lambda row: unidecode.unidecode(row).split(" ")[0])




angio["Data"]=pd.to_datetime(angio["Data"],format='%Y/%m/%d')



telemis["Data"]=telemis["Data acquisizione"].apply(lambda row: unidecode.unidecode(row).split(" ")[0])
telemis["Data"]=pd.to_datetime(telemis["Data"],format='%d/%m/%Y')


f=0
for i in range(len(angio)):
    patient_id=angio["Patient ID"].iloc[i]
    study_date=angio["Data"].iloc[i]
    x=telemis[(telemis["ID Paziente"]==patient_id) & (telemis["Data"]==study_date)]
    if len(x):
        angio["Procedure"].iloc[i]=x["Tipo studio"].values[0]
    else:
        angio["Procedure"].iloc[i]=np.nan
        print(f"[ALERT] {patient_id}")
        f+=1
        
print(f)



elenco=angio["Procedure"].value_counts()





with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
    print(elenco)



angio["Peak Skin Dose (mGy)"]=angio["Peak Skin Dose"].apply(lambda row: row.split(" ")[0])
angio["Fluoro Time (min)"]=angio["Fluoro Time"].apply(lambda row: row.split(" ")[0])
angio["Rad Time (min)"]=angio["Rad Time"].apply(lambda row: row.split(" ")[0])



angio.to_csv(args["output"])



print(f"[INFO] saving output to {args['output']}")






