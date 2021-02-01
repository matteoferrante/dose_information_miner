import pydicom
from bs4 import BeautifulSoup
import glob
import os
import codecs
import pandas as pd
import argparse


"""Script to mine information from html report of Angiograph """

###to run the script write: python angio_information_miner.py -d [directory] -o [outputname]

print(f"[INFO] Dose information miner for structured dose report of TC scans")
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--directory",required=True,help="dir where are placed all dicom structured reports")
parser.add_argument("-o", "--output",required=True,help="name of the output csv file")

args = vars(parser.parse_args())


path=args["directory"]


def mine_dose_report_info(rep):
    file = codecs.open(rep, "r", "utf-8")

    soup = BeautifulSoup(file)
    # i nomi delle table sono strani per come è strutturato il report
    patient_table = soup.find('table', {'id': 'table_patient'})
    dose_table = soup.find('table', {'id': 'dose_date'})
    date_table = soup.find('table', {'id': 'dose_procedure'})
    hospital_table = soup.find('table', {'id': 'table_hospital'})

    df_patient = pd.read_html(patient_table.prettify())[0]
    df_dose = pd.read_html(dose_table.prettify())[0]
    df_date = pd.read_html(date_table.prettify())[0]
    df_hospital = pd.read_html(hospital_table.prettify())[0]

    dict_info = {i[0]: i[1] for i in df_patient.values}

    for i in range(len(df_dose)):
        dict_info[df_dose.iloc[i].values[0]] = df_dose.iloc[i].values[1]

    for i in range(len(df_date)):
        dict_info[df_date.iloc[i].values[0]] = df_date.iloc[i].values[1]

    for i in range(len(df_hospital)):
        dict_info[df_hospital.iloc[i].values[0]] = df_hospital.iloc[i].values[1]

    return dict_info




###INFORMATION LOADING

dir_list=os.listdir(path)

dir_list=[os.path.join(path,i) for i in dir_list]
dir_list=[i for i in dir_list if os.path.isdir(i)]

print(f"[INFO] found {len(dir_list)}")


report_list=[glob.glob(os.path.join(i,"*.htm"))[0] for i in dir_list]


print(f"[INFO] Mining dose information from {len(report_list)} report..")
datas=[]
for rep in report_list:
    datas.append(mine_dose_report_info(rep))

df=pd.DataFrame.from_dict(datas)




df.to_csv(args["output"])
print(f"[INFO] Saved information to {args['output']}")
