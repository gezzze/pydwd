import pandas as pd
from ftputil import FTPHost as FTP

import pydwd_functions


"""
Function to receive current files on server as list excluding description files
"""


def create_fileslist(var,
                     res,
                     per,
                     folder="./dwd_data"):
    # Check for the combination of requested parameters
    pydwd_functions.check_dwd_structure(var=var, res=res, per=per)

    # Folders on FTP with files
    server, path, user, password = pydwd_functions.get_dwd_credentials()

    folder = pydwd_functions.correct_folder_path(folder)

    # Check for folder and create if necessary
    pydwd_functions.create_dwd_folder(subfolder="metadata", folder=folder)

    # Create filename for local metadata file containing information of date
    filelist_local = "{}_{}_{}_{}".format("filelist", var, res, per)

    # Create filename
    filelist_local_path = "{}/{}/{}{}".format(folder,
                                              "metadata",
                                              filelist_local,
                                              ".csv")

    # Try downloading metadata file under given local link
    try:
        # Get files for set of paramters
        files_server = FTP(server, user, password).walk(
            "/{}/{}/{}/{}/".format(path, res, var, per))

    # If not possible raise an error
    except Exception:
        print("Download of fileslist file currently not possible. Try again!")
        raise Exception()

    # Put together dirs and filenames
    files_server = ["{}/{}".format(root, single_file)
                    for root, dir, file in files_server
                    for single_file in file]

    # Select zip files (which contain the measured data) from server
    filelist = [
        file for file in files_server if ".zip" in file]

    filelist = [file.replace("//", "/") for file in filelist]

    # Define length of beginning filenamepath which should be removed to
    # get a clean filename
    path_remove_length = len("/" + path + "/" + res
                             + "/" + var + "/" + per + "/")

    # Remove the first part of the file to just get the "clean" filename
    filelist = [file[path_remove_length:] for file in filelist]

    # Seperate filenames by underscore
    # filelist = [file.split("_") for file in filelist]
    #
    # # Paste together again several parts of the filenames
    # filelist = [["_".join(file[:-4]) + "_",
    #              file[-4],
    #              "_" + "_".join(file[-3:])]
    #             for file in filelist]

    if per == "historical":
        statid_col = -4
    elif per == "recent":
        statid_col = -2
    elif per == "now":
        statid_col = -2
    else:
        statid_col = None

    filelist_df = pd.DataFrame(
        {"FILEID": range(len(filelist)),
         "STATID": [int(file.split("_")[statid_col]) for file in filelist],
         "FILENAME": filelist})

    # Remove old file
    pydwd_functions.remove_dwdfile(
        file_type="filelist", var=var, res=res, per=per, folder=folder)

    # Write new file
    pd.DataFrame.to_csv(
        filelist_df, filelist_local_path, header=True, index=False)

    return(None)


"""
Function for selecting datafile for given statid, var, res, per
"""


def select_dwd(statid,
               var,
               res,
               per,
               folder="./dwd_data",
               create_new_filelist=False):
    # Check for the combination of requested parameters
    pydwd_functions.check_dwd_structure(var=var, res=res, per=per)

    folder = pydwd_functions.correct_folder_path(folder)

    # Create name of fileslistfile
    filelist_local = "{}_{}_{}_{}".format("filelist", var, res, per)

    filelist_local_path = "{}/{}/{}{}".format(
        folder, "metadata", filelist_local, ".csv")

    # Try to read in file
    try:
        # Except if a new one should be created
        if create_new_filelist:
            raise Exception

        # Try to read in file
        filelist = pd.read_csv(
            filelist_local_path)
    except Exception:
        # If there was an error with reading in the fileslist get a new
        # fileslist
        create_fileslist(var=var, res=res, per=per,
                         folder=folder)

        # Try to read in file
        filelist = pd.read_csv(
            filelist_local_path)

    files_statid_id = [id for id, statid_file in enumerate(
        filelist["STATID"]) if statid_file == statid]

    filelist = filelist.iloc[files_statid_id, 2]

    filelist = list(filelist)

    return(filelist)