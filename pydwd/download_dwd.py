from ftputil import FTPHost as FTP
import os

import pydwd_functions


"""
#####################
### download_data ###
#####################
This function is used to download the stationdata for which the link is
provided by the 'select_dwd' function. It checks the shortened filepath (just
the zipfile) for its parameters, creates the full filepath and downloads the
file(s) according to the set up folder.
"""


def download_data(files, folder="./dwd_data"):
    # Correct possible slashes at the end
    folder = pydwd_functions.correct_folder_path(folder)

    # Get server information for the ftp download function
    server, path, user, password = pydwd_functions.get_dwd_credentials()

    # Check the files input for its type (should be list)
    if not isinstance(files, list):
        raise NameError("The 'files' argument is not a list.")

    # Create folder for storing the downloaded data
    pydwd_functions.create_dwd_folder(
        subfolder="stationdata", folder=folder)

    # Determine var, res and per from first filename (needed for creating full
    # filepath)
    var, res, per = pydwd_functions.determine_type(files[0])

    # Try to download the corresponding file to the folder
    try:
        # Create an empty list in which the local filepaths are stored
        files_local = []

        # Loop over files list where every file is formatted (path) and
        # downloaded
        for file in files:
            # Only if the length of one filename is longer then zero it will be
            # examined
            if len(file) > 0:
                # The filepath to the server is created with the filename,
                # the parameters and the path
                file_server = "/{}/{}/{}/{}/{}".format(
                    path, res, var, per, file)
                # The local filename consists of the set of parameters (easier
                # to analyse when looking at the filename) and the original
                file
                file_local = "{}_{}_{}_{}".format(
                    var, res, per, file.split("/")[-1])
                # Then the local path is added to the file
                file_local = "{}/{}/{}".format(folder,
                                               "stationdata",
                                               file_local)
                # This final local path is stored in the list
                files_local.append(file_local)
                # Now the download happens with the filepath to the server and
                # the local path
                FTP(server, user, password).download(
                    source=file_server,
                    target=file_local)
            else:
                # Print a statement according to the empty filename
                print("Empty file is skipped.")

        return(files_local)
    # If anything goes wrong in between every file in the respective folder is
    # deleted. This should prevent a chunk of file from not being run
    # completely and instead should throw an error.
    except Exception:
        # List files in the download folder
        old_files = os.listdir("{}/{}/".format(folder, "stationdata"))
        # For every file in the folder list...
        for old_file in old_files:
            # For every file in the download list...
            for file in files:
                # If the file of the download list is in the folder list
                if file in old_file:
                    # Remove the corresponding file.
                    os.remove("{}/{}/{}".format(folder,
                                                "stationdata",
                                                old_file))
                # If any file is removed it returns to checking the file from
                # download folder.
                break

        # In the end raise an error naming the files that couldn't be loaded.
        raise NameError(
            "One of the files\n {} \n couldn't be downloaded. Check!".format(
                "\n".join(files)))

    return(None)