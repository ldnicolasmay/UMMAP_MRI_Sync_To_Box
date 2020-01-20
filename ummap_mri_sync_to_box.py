#!/usr/bin/env Python3

##################
# Import Modules #

import os
import re
import argparse

import ummap_mri_sync_to_box_helpers as hlps


########
# Main #

def main():

    ##############
    # Parse Args #

    parser = argparse.ArgumentParser(description="Sync `madcbrain` MRI DICOMs to Box.")
    parser.add_argument('-p', '--path', required=True,
                        help='REQUIRED: absolute path to directory containing MRI folders')
    parser.add_argument('-j', '--jwt_cfg', required=True,
                        help='REQUIRED: absolute path to JWT config file')
    parser.add_argument('-b', '--box_folder_id', required=True,
                        help='REQUIRED: destination Box Folder ID')
    parser.add_argument('-u', '--update_files', action='store_true',
                        help='update older Box files with new local copies; VERY TIME CONSUMING')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='print actions to stdout')
    args = parser.parse_args()
    # print(args)

    #################
    # Configuration #

    # Access args.verbose once
    is_verbose = args.verbose

    # Set the path of the folder whose contents should be copied to Box
    path_split = args.path.split('/')
    if path_split[-1] == '':
        del path_split[-1]
    base_path = '/'.join(path_split[:-1] + [''])
    mri_dir = path_split[-1]
    # Using os.DirEntry object initially b/c os.scandir is better directory iterator.
    # See https://www.python.org/dev/peps/pep-0471/ for details
    dir_entries = os.scandir(base_path)
    mri_dir_entry = list(filter(lambda dir_entry: dir_entry.name == mri_dir, dir_entries))[0]
    if is_verbose:
        print()
        print("Path to MRI folders:", mri_dir_entry.path, "\n")

    # Set the path to your JWT app config JSON file
    jwt_cfg_path = args.jwt_cfg
    if is_verbose:
        print("Path to Box JWT config:", jwt_cfg_path, "\n")

    # Set the path to the folder that will hold the upload
    # box_folder_id = "100650703184"
    box_folder_id = args.box_folder_id

    ############################
    # Establish Box Connection #

    # Get authenticated Box client
    box_client = hlps.get_box_authenticated_client(jwt_cfg_path, is_verbose=is_verbose)

    # Create Box Folder object with authenticated client
    box_folder = box_client.folder(folder_id=box_folder_id).get()

    #########################################################
    # Recurse Through Directories to Sync Files/Directories #

    rgx_subfolders = re.compile(r'^hlp17umm\d{5}_\d{5}$|^s\d{5}$')  # e.g., 'hlp17umm00700_06072', 's00003'
    rgx_subfiles = re.compile(r'^i\d+\.MRDC\.\d+$')                 # e.g., 'i53838914.MRDC.3'

    hlps.walk_local_dir_tree_sync_contents(mri_dir_entry, box_client, box_folder,
                                           rgx_subfolders, rgx_subfiles,
                                           update_subfiles=args.update_files, is_verbose=is_verbose)


if __name__ == "__main__":
    main()
