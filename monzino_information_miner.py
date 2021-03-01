import argparse
import glob
import os
import traceback
from collections import defaultdict
from pathlib import Path
import pydicom
import pandas as pd
import json


"""Script to mine information from structured report of Monzino """

###to run the script write: python monzino_information_miner.py -d "R:\daniela\MATTEO_Ferrante\DOSI CCM\2021" -o ccm_report

print(f"[INFO] Dose information miner for structured dose report of TC scans and angiography scans")
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--directory",required=True,help="dir where are placed all dicom structured reports")
parser.add_argument("-o", "--output",required=True,help="name of the output csv file")

args = vars(parser.parse_args())



path=args["directory"]


def mine_ct_information(test):
    """Takes the header and return a dict of information"""
    c = str(test)  # to string to split on RelationShip

    # Anagraphics
    name = test.PatientName
    sex = test.PatientSex
    age = test.PatientAge
    birthday = test.PatientBirthDate
    patient_ID = test.PatientID

    # study information
    study_date = test.StudyDate
    study_time = test.StudyTime
    study_id = test.StudyID
    study_description = test.StudyDescription

    model = test.ManufacturerModelName

    # Dose Infomration Mining

    chunks = c.split('Relationship Type')

    # filtering
    ctdi_chunks = []
    dlp_chunks = []
    phantom_chunks = []
    acquisition = []
    target_regions = []
    KV = []
    mAs = []
    for c in chunks:
        if "CTDIw Phantom Type" in c:
            phantom_chunks.append(c)
        elif ("mGy" in c) and ("DLP" in c):
            dlp_chunks.append(c)
        elif ("mGy" in c) and ("CTDI" in c):
            ctdi_chunks.append(c)
        elif "CT Acquisition Type" in c:
            x = c.split("\n")
            for i in x:
                if ("Code Meaning" in i) and not ("CT Acquisition Type" in i):
                    f = i.split(" ")
                    acquisition.append(" ".join(f[-2:]))
        elif "Target Region" in c:
            ex = c.split("\n")
            for i in ex:
                if ("Code Meaning" in i) and ("Target Region" not in i):
                    r = i.split(" ")
                    target_regions.append(r[-1])

        elif "kV" in c:
            x = c.split("\n")
            for i in x:
                if "Numeric Value" in i:
                    s = i.split(" ")
                    KV.append(float(s[-1].replace("'", "").replace('"', '')))  # to remove quotes and make it a number

        elif "mA" in c and "Maximum" not in c:
            x = c.split("\n")
            for i in x:
                if "Numeric Value" in i:
                    s = i.split(" ")
                    mAs.append(float(s[-1].replace("'", "").replace('"', '')))

    # drop out the scout -> search for "Angle Acquisition"
    idx_to_remove = []
    for i in range(len(acquisition)):
        if "Angle Acquisition" in acquisition[i]:
            idx_to_remove.append(i)

    # acquisition = [i for i in acquisition if "Angle Acquisition" not in i]
    for r in sorted(idx_to_remove, reverse=True):
        del acquisition[r]
        del KV[r]
        del target_regions[r]
        del mAs[r]

    ctdi_report = []
    for ctdi in ctdi_chunks:
        if "Alert" in ctdi:
            continue
        x = ctdi.split("\n")
        for i in x:
            if "Numeric Value" in i:
                sub = i.split(" ")
                value = float(sub[-1].replace("'", "").replace('"', ''))

                ctdi_report.append(value)

    dlp_report = []
    for dlp in dlp_chunks:
        if "Alert" in dlp:
            continue
        x = dlp.split("\n")
        for i in x:
            if "Numeric Value" in i:
                sub = i.split(" ")
                value = float(sub[-1].replace("'", "").replace('"', ''))
                dlp_report.append(value)

    total_dlp = sum(dlp_report)

    phantom_report = []
    for pht in phantom_chunks:
        x = pht.split("\n")
        for i in x:
            if "Body" in i:
                phantom_report.append("Body")
            elif "Head" in i:
                phantom_report.append("Head")

    print(f"[INFO] found {len(acquisition)} for this patient, reportig retrieved info..")
    info = []
    for i in range(len(acquisition)):
        dict_info = {"PatientID": patient_ID, "PatientName": name, "PatientSex": sex, "PatientAge": age,
                     "PatientBirthDate": birthday, "StudyDate": study_date, "StudyTime": study_time,
                     "StudyID": study_id, "StudyDescription": study_description, "TargetRegion": target_regions[i],
                     "ManufacturerModelName": model,
                     "kV": KV[i], "mAs": mAs[i], "CTDIw (mGy)": ctdi_report[i], "DLP (mGy.cm)": dlp_report[i],
                     "Total DLP (mGy.cm)": total_dlp,
                     "Acquisition": acquisition[i]}
        info.append(dict_info)
    return info


def get_unit_description(n):
    #this code take part of the DCM header (the Relationship Type block in tag 0040A300) and gives out the description Code Meaning
    descr=""
    l=n["004008EA"]["Value"]
    for i in l:
        try:
            descr=i["00080104"]["Value"]
        except:
            pass
    return descr


def get_description(m):
    #this code take part of the DCM header (the Relationship Type block in tag 0040A043) and gives out the description Code Meaning
    return m["00080104"]["Value"]


def mine_angio_information(patient):
    """Takes the header and return a dict of information"""
    c = str(patient)  # to string to split on RelationShip

    # Anagraphics
    name = patient.PatientName
    sex = patient.PatientSex
    age = patient.PatientAge
    birthday = patient.PatientBirthDate
    patient_ID = patient.PatientID

    # study information
    study_date = patient.StudyDate
    study_time = patient.StudyTime
    study_id = patient.StudyID
    study_description = patient.StudyDescription

    model = patient.ManufacturerModelName

    # HERE TRY TO SEPARATE ACQUISITION FOR EACH PATIENT

    j = json.loads(patient.to_json())
    j.keys()

    numeric = []
    units = []
    descriptions = []
    warn=None
    try:
        for i in j["0040A730"]["Value"]:
            # second seq

            try:
                ss = i["0040A730"]["Value"]

                for k in ss:
                    # concept level
                    try:
                        cl = k["0040A300"]["Value"]  # qua ci trovo i numeric value
                        dl = k["0040A043"]["Value"]  # qua ci dovrei trovare i nomi delle procedure

                        for n in cl:
                            ###HERE IS THE RIGHT LEVEL - 004008EA for description and 0040A30A for numeric values
                            numeric_value = n["0040A30A"]["Value"]
                            description = get_unit_description(n)
                            numeric.append(numeric_value)
                            units.append(description)

                        for m in dl:
                            descriptions += get_description(m)

                    except Exception as e:
                        warn=e


            except Exception as e:
                warn=e


        print(f"[INFO] Descriptions: {len(descriptions)} \t Numeric: {len(numeric)}")

        # create a list of dict for pandas
        # info=[]
        d = defaultdict(list)
        for desc, num in zip(descriptions, numeric):
            d.setdefault(desc, []).append(num[0])

        info = d
        # for i in range(0,len(descriptions)-len(set(descriptions)),len(set(descriptions))):
        angio_dict = {"PatientID": patient_ID, "PatientName": name, "PatientSex": sex, "PatientAge": age,
                      "PatientBirthDate": birthday, "StudyDate": study_date, "StudyTime": study_time,"StudyDescription":study_description,"StudyID":study_id,"Model":model}
        #    for j in range(len(set(descriptions))):
        # add acquisition info
        #        angio_dict[descriptions[i+j]]=numeric[i+j]
        #    info.append(angio_dict)
    except:
       # traceback.print_exc()
        info = []
        angio_dict = {}
        print(f"[INFO] Can't find angiographic information for {patient.PatientID}")
    return info, angio_dict,warn

def rearrange_angio_todict(anagraphic,data):
    angio_dict=anagraphic
    #make all list of the same lenght
    l=[len(x) for x in data.values()]
    max_l=max(l)
    new_data={}
    for k,v in data.items():
        new_data[k]=extend(v,max_l)

    #now add
    x=pd.DataFrame(new_data).to_dict('records')
    complete=[{**anagraphic, **i} for i in x]
    return complete


def extend(v, max_l):
    # extend the list with None if is too short

    if len(v) < max_l:
        v += [None] * (max_l - len(v))
    return v

print(f"[INFO] Loading all reports..")
files_list=[]
#path_list = [os.path.join(dirpath,filename) for dirpath, _, filenames in os.walk(path) for filename in filenames if filename.endswith('.dcm')]
for root, dirs, files in os.walk(path):
    for name in files:
        print(root)
        files_list.append(os.path.join(root,name))

print(f"[INFO] Running disambiguation to discriminate CT, RX and Angiography exams..")

dcm_list=[pydicom.dcmread(i) for i in files_list]

altro=[]
altro_path=[]
ct=[]
ct_path=[]
angio=[]
angio_path=[]
for (i,dcm) in enumerate(dcm_list):
    try:
        model=str(dcm[0x0008, 0x1090])
        if "CT" in model:
            ct.append(dcm)
            ct_path.append(files_list[i])
        elif "Artis" in model:
            angio.append(dcm)
            angio_path.append(files_list[i])
        else:
            altro.append(dcm)
            altro_path.append(files_list[i])
    except Exception as e:
        print(e)
print(f"[INFO] Disambiguation based on Manufacturer's Model Name:\nCT:\t {len(ct)}\nAngio:\t {len(angio)}\nOther:\t {len(altro)}")

#START PROCEDURE FOR CT..
print(f"[INFO] Mining information for CT scans..")

ct_info = []
missing_ct_patients=[]
for patient in ct:
    mined=mine_ct_information(patient)
    if len(mined)==0:
        missing_ct_patients.append(patient.PatientID)
    ct_info += mined


df=pd.DataFrame.from_dict(ct_info)

df.to_csv(args["output"]+"_ct.csv")

with open("ct_missing", "w") as outfile:
    outfile.write("\n".join(missing_ct_patients))



print(f"[INFO] Mining information for angio scans..")
angio_data=[]
anagraphics=[]
missing_angio_patient=[]
for (i,patient) in enumerate(angio):
    #angio_data+=mine_angio_information(patient)
    info,anagraphic,warn=mine_angio_information(patient)
    if len(info)==0:
        missing_angio_patient.append(f"{patient.PatientID}\t {angio_path[i]}\t {warn}")
    angio_data.append(info)
    anagraphics.append(anagraphic)

angio_info = []
for a, d in zip(anagraphics, angio_data):
    if len(d):
        angio_info += rearrange_angio_todict(a, d)

df=pd.DataFrame.from_dict(angio_info)

df.to_csv(args["output"]+"_angio.csv")

with open("angio_missing", "w") as outfile:
    outfile.write("\n".join(missing_angio_patient))

print(f"[END]")