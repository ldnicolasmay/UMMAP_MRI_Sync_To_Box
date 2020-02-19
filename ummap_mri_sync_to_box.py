#!/usr/bin/env Python3

##################
# Import Modules #

import os
import re
import argparse

import ummap_mri_sync_to_box_helpers as hlps
import dir_entry_node as den


def str2bool(val):
    if isinstance(val, bool):
        return val
    elif val.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif val.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

########
# Main #

def main():

    ##############
    # Parse Args #

    parser = argparse.ArgumentParser(description="Sync `madcbrain` MRI DICOMs to Box.")

    parser.add_argument('-m', '--mri_path', required=True,
                        help=f"required: " +
                             f"absolute path to local directory containing source MRI folders")

    parser.add_argument('-j', '--jwt_cfg', required=True,
                        help=f"required: absolute path to local JWT config file")

    parser.add_argument('-b', '--box_folder_id', required=True,
                        help=f"required: destination Box Folder ID")

    parser.add_argument('-f', '--subfolder_regex', nargs='+', required=True,
                        help=f"quoted regular expression strings to use for subfolder matches")

    parser.add_argument('-s', '--sequence_regex', nargs='+', required=True,
                        help=f"quoted regular expression strings to use for "
                             f"MRI Series Description matches")

    parser.add_argument('-u', '--update_files',
                        type=str2bool, nargs='?', const=True, default=False,
                        help=f"time consuming: update older Box files with new local copies")

    parser.add_argument('-r', '--remove_items',
                        type=str2bool, nargs='?', const=True, default=False,
                        help=f"danger: remove items not in model tree of folders/files defined by `subfolder_regex`")

    parser.add_argument('-v', '--verbose',
                        type=str2bool, nargs='?', const=True, default=False,
                        help=f"print actions to stdout")

    args = parser.parse_args()

    #################
    # Configuration #

    # Access args.update_files, args.remove_items, and args.verbose once
    update_files = args.update_files
    remove_items = args.remove_items
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
        print(f"Path to MRI folders:", f"{mri_dir_entry.path}")

    # Set the path to your JWT app config JSON file
    jwt_cfg_path = args.jwt_cfg
    if is_verbose:
        print(f"Path to Box JWT config:", f"{jwt_cfg_path}")

    # Set the path to the folder that will hold the upload
    box_folder_id = args.box_folder_id

    # Set regexes of subfolders and subfiles to sync
    rgx_subfolder = re.compile(r'^hlp17umm\d{5}_\d{5}$|^dicom$|^s\d{5}$')  # e.g., hlp17umm00700_06072, dicom, s00003
    args_subfolder_regex = args.subfolder_regex
    if args_subfolder_regex:
        rgx_subfolder = re.compile("|".join(args_subfolder_regex))
    if is_verbose:
        print(f"Folder regex(es):", f"{rgx_subfolder}")

    rgx_subfile = re.compile(r'^i\d+\.MRDC\.\d+$')  # e.g., 'i53838914.MRDC.3'

    # Set regexes of dicom dataset sequence series descriptions to sync
    rgx_sequence = re.compile(r'^t1sag.*$|^t2flairsag.*$')
    args_sequence_regex = args.sequence_regex
    if args_sequence_regex:
        rgx_sequence = re.compile("|".join(args_sequence_regex))
    if is_verbose:
        print(f"Sequence regex(es):", f"{rgx_sequence}")

    ############################
    # Establish Box Connection #

    # Get authenticated Box client
    box_client = hlps.get_box_authenticated_client(jwt_cfg_path, is_verbose=is_verbose)

    # Create Box Folder object with authenticated client
    box_folder = box_client.folder(folder_id=box_folder_id).get()

    #########################################################
    # Recurse Through Directories to Sync Files/Directories #

    print(f"Building DirEntryNode tree from root node...")
    root_node = den.DirEntryNode(mri_dir_entry, depth=0)
    # Traverse local source directory to build tree object
    root_node.build_tree_from_node(rgx_subfolder, rgx_subfile)

    print(f"Pruning nodes...")
    root_node.prune_nodes_without_dicom_dataset_series_descrip(rgx_sequence)

    print(f"Syncing nodes to Box...")
    root_node.sync_tree_object_items(box_folder,
                                     update_files=update_files,
                                     remove_items=remove_items,
                                     is_verbose=is_verbose)
    print(f"Done.\n")


if __name__ == "__main__":
    main()
