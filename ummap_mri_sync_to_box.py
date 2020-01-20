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
    parser.add_argument('-m', '--mri_path', required=True,
                        help='REQUIRED: absolute path to directory containing MRI folders')
    parser.add_argument('-j', '--jwt_cfg', required=True,
                        help='REQUIRED: absolute path to JWT config file')
    parser.add_argument('-b', '--box_folder_id', required=True,
                        help='REQUIRED: destination Box Folder ID')
    parser.add_argument('-u', '--update_files', action='store_true',
                        help='update older Box files with new local copies; VERY TIME CONSUMING')
    parser.add_argument('-r', '--regex_subfolder', nargs='+',
                        help='regular expression strings to use for subfolder matches')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='print actions to stdout')
    args = parser.parse_args()
    #  print(args)

    #################
    # Configuration #

    # Access args.verbose once
    is_verbose = args.verbose

    # Set the path of the folder whose MRI contents should be copied to Box
    mri_path_split = args.mri_path.split('/')
    if mri_path_split[-1] == '':
        del mri_path_split[-1]
    mri_base_path = '/'.join(mri_path_split[:-1] + [''])
    mri_dir = mri_path_split[-1]
    # Using os.DirEntry object initially b/c os.scandir is better directory iterator.
    # See https://www.python.org/dev/peps/pep-0471/ for details
    dir_entries = os.scandir(mri_base_path)
    mri_dir_entry = list(filter(lambda dir_entry: dir_entry.name == mri_dir, dir_entries))[0]
    if is_verbose:
        print()
        print("Path to MRI folders:", mri_dir_entry.path, "\n")

    # Set the path to your JWT app config JSON file
    jwt_cfg_path = args.jwt_cfg
    if is_verbose:
        print("Path to Box JWT config:", jwt_cfg_path, "\n")

    # Set the path to the folder that will hold the upload
    box_folder_id = args.box_folder_id

    # Set regexes of subfolders and subfiles to sync
    rgx_subfolder = re.compile(r'^hlp17umm\d{5}_\d{5}$|^s\d{5}$')  # e.g., 'hlp17umm00700_06072', 's00003'
    if args.regex_subfolder:
        rgx_subfolder = re.compile("|".join(args.regex_subfolder))
    if is_verbose:
        print(rgx_subfolder)
    rgx_subfile = re.compile(r'^i\d+\.MRDC\.\d+$')                 # e.g., 'i53838914.MRDC.3'

    ############################
    # Establish Box Connection #

    # Get authenticated Box client
    box_client = hlps.get_box_authenticated_client(jwt_cfg_path, is_verbose=is_verbose)

    # Create Box Folder object with authenticated client
    box_folder = box_client.folder(folder_id=box_folder_id).get()

    #########################################################
    # Recurse Through Directories to Sync Files/Directories #

    hlps.walk_local_dir_tree_sync_contents(mri_dir_entry, box_client, box_folder,
                                           rgx_subfolder, rgx_subfile,
                                           update_subfiles=args.update_files, is_verbose=is_verbose)


if __name__ == "__main__":
    main()
