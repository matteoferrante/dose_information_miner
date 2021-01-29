import argparse
import pydicom
import pandas as pd
import glob
import os


parser = argparse.ArgumentParser()
parser.add_argument("-d", "--directory",required=True,help="dir where are placed all dicom structured reports")
parser.add_argument("-o", "--output",required=True,help="name of the output csv file")

args = vars(parser.parse_args())


path=args["directory"]


report_list=glob.glob(os.path.join(path,"*.DCM"))
report_list=[pydicom.dcmread(i) for i in report_list]


def mine_information(test):
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

    acquisition = [i for i in acquisition if "Angle Acquisition" not in i]

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
                     "StudyID": study_id, "StudyDescription": study_description, "ManufacturerModelName": model,
                     "CTDIw (mGy)": ctdi_report[i], "DLP (mGy.cm)": dlp_report[i], "Total DLP (mGy.cm)": total_dlp,
                     "Acquisition": acquisition[i]}
        info.append(dict_info)
    return info



print(f"[INFO] Mining information from dicom files...")

info = []
for patient in report_list:
    info += mine_information(patient)


df=pd.DataFrame.from_dict(info)

df.to_csv(args["output"])