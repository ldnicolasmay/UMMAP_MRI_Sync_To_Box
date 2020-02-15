#!/usr/bin/env Python3

##################
# Import Modules #

import os
import re
import argparse
from colored import fg, attr

import ummap_mri_sync_to_box_helpers as hlps
import dir_entry_node as den


########
# Main #

def main():

    #####################
    # Print Color Setup #

    clr_blu = fg('blue')
    clr_bld = attr('bold')
    clr_wrn = fg('red') + attr('bold')
    clr_rst = attr('reset')

    ##############
    # Parse Args #

    parser = argparse.ArgumentParser(description="Sync `madcbrain` MRI DICOMs to Box.")
    parser.add_argument('-m', '--mri_path', required=True,
                        help=f"{clr_bld}required{clr_rst}: " +
                             f"absolute path to local directory containing source MRI folders")
    parser.add_argument('-j', '--jwt_cfg', required=True,
                        help=f"{clr_bld}required{clr_rst}: absolute path to local JWT config file")
    parser.add_argument('-b', '--box_folder_id', required=True,
                        help=f"{clr_bld}required{clr_rst}: destination Box Folder ID")
    parser.add_argument('-f', '--subfolder_regex', nargs='+', required=True,
                        help=f"{clr_bld}quoted{clr_rst} regular expression strings to use for subfolder matches")
    parser.add_argument('-s', '--sequence_regex', nargs='+', required=True,
                        help=f"{clr_bld}quoted{clr_rst} regular expression strings to use for "
                             f"MRI Series Description matches")
    parser.add_argument('-u', '--update_files', action='store_true',
                        help=f"{clr_wrn}time consuming{clr_rst}: update older Box files with new local copies")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help=f"print actions to stdout")
    args = parser.parse_args()

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
        print(f"{clr_blu}Path to MRI folders{clr_rst}:", f"{mri_dir_entry.path}")

    # Set the path to your JWT app config JSON file
    jwt_cfg_path = args.jwt_cfg
    if is_verbose:
        print(f"{clr_blu}Path to Box JWT config{clr_rst}:", f"{jwt_cfg_path}")

    # Set the path to the folder that will hold the upload
    box_folder_id = args.box_folder_id

    # Set regexes of subfolders and subfiles to sync
    rgx_subfolder = re.compile(r'^hlp17umm\d{5}_\d{5}$|^dicom$|^s\d{5}$')  # e.g., hlp17umm00700_06072, dicom, s00003
    args_subfolder_regex = args.subfolder_regex
    if args_subfolder_regex:
        rgx_subfolder = re.compile("|".join(args_subfolder_regex))
    if is_verbose:
        print(f"{clr_blu}Folder regex(es){clr_rst}:", f"{rgx_subfolder}")

    rgx_subfile = re.compile(r'^i\d+\.MRDC\.\d+$')  # e.g., 'i53838914.MRDC.3'

    # Set regexes of dicom dataset sequence series descriptions to sync
    rgx_sequence = re.compile(r'^t1sag.*$|^t2flairsag.*$')
    args_sequence_regex = args.sequence_regex
    if args_sequence_regex:
        rgx_sequence = re.compile("|".join(args_sequence_regex))
    if is_verbose:
        print(f"{clr_blu}Sequence regex(es){clr_rst}:", f"{rgx_sequence}", "\n")

    ############################
    # Establish Box Connection #

    # Get authenticated Box client
    box_client = hlps.get_box_authenticated_client(jwt_cfg_path, is_verbose=is_verbose)

    # Create Box Folder object with authenticated client
    box_folder = box_client.folder(folder_id=box_folder_id).get()

    #########################################################
    # Recurse Through Directories to Sync Files/Directories #

    # hlps.walk_local_dir_tree_sync_contents(mri_dir_entry, box_client, box_folder,
    #                                        rgx_subfolder, rgx_subfile,
    #                                        update_subfiles=args.update_files, is_verbose=is_verbose)

    # Traverse local source directory to build tree object
    root_node = den.DirEntryNode(mri_dir_entry, depth=0)
    root_node.build_tree_from_node(rgx_subfolder, rgx_subfile)
    # root_node.print_node()
    root_node.prune_nodes_without_dicom_dataset_series_descrip(rgx_sequence)
    # root_node.print_node()
    root_node.write_tree_object_items(box_folder, is_verbose=True)


if __name__ == "__main__":
    main()
