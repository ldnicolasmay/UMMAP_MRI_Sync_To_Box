#!/usr/bin/env Python3

##################
# Import Modules #

import os
import re
from importlib import reload

import ummap_mri_copy_to_box_helpers as hlps


#################
# Configuration #

# Set the path of the folder whose contents should be copied to Box
path_mri = "/Users/ldmay/MRI/"

# Get DirEntry object of "/Users/ldmay/MRI/consensus_downloads" directory
dir_entries_top = os.scandir(path_mri)
for dir_entry in dir_entries_top:
    if (dir_entry.name == "consensus_downloads"):
        local_folder = dir_entry


# Set the path to your JWT app config JSON file here!
path_box_json_config = "/Users/ldmay/PycharmProjects/BoxPythonSDK/81663_ldlfw6r6_config.json"

# Set the path to the folder that will hold the upload
box_folder_id = "100650703184"


############################
# Establish Box Connection #

# Get authenticated Box client
box_client = hlps.get_box_authenticated_client(path_box_json_config)

# Create Box Folder object with authenticated client
box_folder = box_client.folder(folder_id=box_folder_id).get()


#########################################################
# Recurse Through Directories to Sync Files/Directories #

rgx_subfolders = re.compile(r'^hlp17umm\d{5}_\d{5}$|^s\d{5}$')  # e.g., 'hlp17umm00700_06072', 's00003'
rgx_subfiles = re.compile(r'^i\d+\.MRDC\.\d+$')                 # e.g., 'i53838914.MRDC.3'

reload(hlps)
hlps.walk_local_dir_tree_sync_contents(local_folder, box_client, box_folder, rgx_subfolders, rgx_subfiles)
