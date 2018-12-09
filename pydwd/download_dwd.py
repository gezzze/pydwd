import os

from .classes import FTP
from .functions import correct_folder_path, create_dwd_folder, determine_type

from .credentials import SERVER, PATH

"""
################################
### Function 'download_data' ###
################################
This function is used to download the stationdata for which the link is
provided by the 'select_dwd' function. It checks the shortened filepath (just
the zipfile) for its parameters, creates the full filepath and downloads the
file(s) according to the set up folder.
"""


def download_data(files, folder="./dwd_data"):
    # Correct possible slashes at the end
    folder = correct_folder_path(folder)

    # Get server information for the ftp download function
    server = SERVER
    path = PATH

    # Check the files input for its type (should be list)
    if not isinstance(files, list):
        raise NameError("The 'files' argument is not a list.")

    # Create folder for storing the downloaded data
    create_dwd_folder(subfolder="stationdata", folder=folder)

    # Determine var, res and per from first filename (needed for creating full
    # filepath)
    var, res, per = determine_type(files[0])

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
                file_local = "{}_{}_{}_{}".format(
                    var, res, per, file.split("/")[-1])

                # Then the local path is added to the file
                file_local = "{}/{}/{}".format(folder,
                                               "stationdata",
                                               file_local)
                # This final local path is stored in the list
                files_local.append(file_local)

                # Open connection with ftp server
                ftp = FTP(server)

                # Login
                ftp.login()

                # Now the download happens with the filepath to the server and
                # the local path
                ftp.download(filepath_server=file_server,
                             filepath_local=file_local)

                # Close
                ftp.close()
            else:
                # Print a statement according to the empty filename
                print("Empty file is skipped.")

        return files_local

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
            "One of the files\n {} \n couldn't be downloaded!".format(
                "\n".join(files)))

    return None