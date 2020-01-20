##################
# Import Modules #

import re
import os.path
# from typing import List
from boxsdk import JWTAuth, Client
from datetime import datetime
from pytz import timezone


###########
# Globals #

# https://opensource.box.com/box-python-sdk/tutorials/intro.html
box_folder_attrs = [
    "type",
    "id",
    "sequence_id",
    "etag",
    "name",
    "created_at",
    "modified_at",
    "description",
    "size",
    "path_collection",
    "created_by",
    "modified_by",
    # "trashed_at",
    # "purged_at",
    # "content_created_at",
    # "content_modified_at",
    # "owned_by",
    # "shared_link",
    # "folder_upload_email",
    # "parent",
    # "item_status",
    # "item_collection"
]

tz_east = timezone("US/Eastern")


######################
# Local OS Functions #


def get_local_subitems(local_folder):
    """Get a collection of all immediate folder items

    Arguments:
        folder {DirEntry} -- The DirEntry folder whose contents we want to fetch

    Returns:
        items {list} -- A list collection of DirEntry objects
    """
    items = []
    # fetch folder items and add subitems to list
    for item in os.scandir(local_folder):
        items.append(item)
    return items


def get_local_subfolders(local_subitems, regex_pattern=None):
    """"""
    if not regex_pattern:
        filter_obj = \
            filter(lambda local_subitem: os.DirEntry.is_dir(local_subitem),
                   local_subitems)
    else:
        filter_obj = \
            filter(lambda local_subitem: os.DirEntry.is_dir(local_subitem) and
                                         re.match(regex_pattern, local_subitem.name),
                   local_subitems)
    return list(filter_obj)


def get_local_subfiles(local_subitems, regex_pattern=None):
    """"""
    if not regex_pattern:
        filter_obj = \
            filter(lambda local_subitem: os.DirEntry.is_file(local_subitem),
                   local_subitems)
    else:
        filter_obj = \
            filter(lambda local_subitem: os.DirEntry.is_file(local_subitem) and
                                         re.match(regex_pattern, local_subitem.name),
                   local_subitems)
    return list(filter_obj)


########################
# Box Client Functions #


def get_box_authenticated_client(box_json_config_path):
    """Get an authenticated Box client for a JWT service account

    Arguments:
        configPath {str} -- Path to the JSON config file for your Box JWT app

    Returns:
        Client -- A Box client for the JWT service account

    Raises:
        ValueError -- if the configPath is empty or cannot be found
    """
    if not os.path.isfile(box_json_config_path):
        raise ValueError(f"`box_json_config_path` must be a path to the JSON config file for your Box JWT app")
    auth = JWTAuth.from_settings_file(box_json_config_path)
    print("Authenticating...")
    auth.authenticate_instance()
    return Client(auth)


def print_box_user_info(box_client):
    """Print the name and login of the current authenticated Box user

    Arguments:
        box_client {Client} -- An authenticated Box client
    """
    user = box_client.user('me').get()
    print("")
    print("Authenticated User")
    print(f"Name: {user.name}")
    print(f"Login: {user.login}")


def get_box_subitems(box_client, box_folder, fields=box_folder_attrs):
    """Get a collection of all immediate folder items

    Arguments:
        client {Client} -- An authenticated Box client
        folder {Folder} -- The Box folder whose contents we want to fetch

    Keyword Arguments:
        fields {list} -- An optional list of fields to include with each item

    Returns:
        items {list} -- A list collection of Box files and folders.
    """
    items = []
    # fetch folder items and add subfolders to list
    for item in box_client.folder(folder_id=box_folder['id']).get_items(fields=fields):
        items.append(item)
    return items


def get_box_subfolders(box_subitems):
    """"""
    return list(filter(lambda box_subitem: box_subitem.type == "folder", box_subitems))


def get_box_subfiles(box_subitems):
    """"""
    return list(filter(lambda box_subitem: box_subitem.type == "file", box_subitems))


def get_corresponding_box_subfolder(local_subfolder, box_client, box_folder):
    """Get box subfolder that corresponds BY NAME to local subfolder

    Arguments:
        local_subfolder {DirEntry} -- The DirEntry subfolder whose corresponding Box subfolder we want to find
        box_client {Client} -- An authenticated Box client
        box_folder {Folder} -- The Box folder whose contents may hold the corresponding Box subfolder

    Returns:
        box_subfolder {Folder} -- The Box Folder object we want to return
    """
    box_subitems = get_box_subitems(box_client, box_folder)
    box_subfolders = get_box_subfolders(box_subitems)

    box_subfolder_target = None
    for box_subfolder in box_subfolders:
        if local_subfolder.name == box_subfolder.name and local_subfolder.is_dir():
            box_subfolder_target = box_subfolder

    return box_subfolder_target


def get_corresponding_box_subfile(local_subfile, box_client, box_folder):
    """Get box subfolder that corresponds BY NAME to local subfolder

    Arguments:
        local_subfile {DirEntry} -- The DirEntry subfile whose corresponding Box file we want to find
        box_client {Client} -- An authenticated Box client
        box_folder {Folder} -- The Box folder whose contents may hold the corresponding Box subfile

    Returns:
        box_subfile {File} -- The Box File object we want to return
    """
    box_subitems = get_box_subitems(box_client, box_folder)
    box_subfiles = get_box_subfiles(box_subitems)

    box_subfile_target = None
    for box_subfile in box_subfiles:
        if local_subfile.name == box_subfile.name and local_subfile.is_file():
            box_subfile_target = box_subfile

    return box_subfile_target


def delete_box_subfolders_not_found_in_local(local_subfolders, box_subfolders):
    """"""
    local_subfolders_names = [local_subfolder.name for local_subfolder in local_subfolders]
    subfolders_not_in_local_in_box = \
        list(filter(lambda box_subfolder: box_subfolder.name not in local_subfolders_names, box_subfolders))
    deleted_box_subfolders_ids = []
    # print("folders not in local, in box", "\n  ", subfolders_not_in_local_in_box)
    for box_subfolder in subfolders_not_in_local_in_box:
        box_subfolder_id, box_subfolder_name = box_subfolder.id, box_subfolder.name
        box_subfolder_deleted = box_subfolder.delete(recursive=True)
        if box_subfolder_deleted:
            deleted_box_subfolders_ids.append(box_subfolder_id)
            print(f"\tDeleted subfolder '{box_subfolder_name}' with ID '{box_subfolder_id}'")
    return deleted_box_subfolders_ids


def create_box_subfolders_found_in_local(local_subfolders, box_folder, box_subfolders):
    """"""
    box_subfolders_names = [box_subfolder.name for box_subfolder in box_subfolders]
    subfolders_in_local_not_in_box = \
        list(filter(lambda local_subfolder: local_subfolder.name not in box_subfolders_names, local_subfolders))
    created_box_subfolders_ids = []
    # print("folders in local, not in box", "\n  ", subfolders_in_local_not_in_box)
    for local_subfolder in subfolders_in_local_not_in_box:
        box_subfolder = box_folder.create_subfolder(local_subfolder.name)
        created_box_subfolders_ids.append(box_subfolder.id)
        print(f"\tCreated subfolder '{box_subfolder.name}' with ID '{box_subfolder.id}'")
    return created_box_subfolders_ids


def delete_box_subfiles_not_found_in_local(local_subfiles, box_subfiles):
    """"""
    local_subfiles_names = [local_subfile.name for local_subfile in local_subfiles]
    subfiles_not_in_local_in_box = \
        list(filter(lambda box_subfile: box_subfile.name not in local_subfiles_names, box_subfiles))
    deleted_box_subfiles_ids = []
    # print("files not in local, in box", "\n  ", subfiles_not_in_local_in_box)
    for box_subfile in subfiles_not_in_local_in_box:
        box_subfile_id, box_subfile_name = box_subfile.id, box_subfile.name
        box_subfile_deleted = box_subfile.delete()
        if box_subfile_deleted:
            deleted_box_subfiles_ids.append(box_subfile_id)
            print(f"\tDeleted subfile '{box_subfile_name}' with ID '{box_subfile_id}'")
    return deleted_box_subfiles_ids

def create_box_subfiles_found_in_local(local_subfiles, box_folder, box_subfiles):
    """"""
    box_subfiles_names = [box_subfile.name for box_subfile in box_subfiles]
    subfiles_in_local_not_in_box = \
        list(filter(lambda local_subfile: local_subfile.name not in box_subfiles_names, local_subfiles))
    created_box_subfiles_ids = []
    # print("files in local, not in box", "\n  ", subfiles_in_local_not_in_box)
    for local_subfile in subfiles_in_local_not_in_box:
        box_subfile = box_folder.upload(local_subfile.path, preflight_check=True)
        box_subfile_id = box_subfile.id
        created_box_subfiles_ids.append(box_subfile_id)
        print(f"\tCreated subfile '{box_subfile.name}' with ID '{box_subfile_id}'")
    return created_box_subfiles_ids


def update_box_subfiles_found_in_local(local_subfiles, box_client, box_folder, box_subfiles):
    """"""
    box_subfiles_names = [box_subfile.name for box_subfile in box_subfiles]
    local_subfiles_in_local_in_box = \
        list(filter(lambda local_subfile: local_subfile.name in box_subfiles_names, local_subfiles))
    updated_box_subfiles_ids = []
    for local_subfile in local_subfiles_in_local_in_box:
        corres_box_subfile = get_corresponding_box_subfile(local_subfile, box_client, box_folder)
        # Local subfile modified timestamp
        local_subfile_modified_psx = local_subfile.stat().st_mtime
        local_subfile_modified_dt = datetime.fromtimestamp(local_subfile_modified_psx, tz=tz_east)
        # Corresponding Box subfile modified timestamp
        corres_box_subfile_modified_str = corres_box_subfile.modified_at
        corres_box_subfile_modified_dt = datetime.fromisoformat(corres_box_subfile_modified_str)
        # Update corres_box_subfile with contents of more recent local_subfile
        if local_subfile_modified_dt > corres_box_subfile_modified_dt:
            updated_box_subfile = corres_box_subfile.update_contents(local_subfile.path, preflight_check=True)
            updated_box_subfile_id = updated_box_subfile.id
            updated_box_subfiles_ids.append(updated_box_subfile_id)
            print(f"\tUpdated subfile '{updated_box_subfile.name}' with ID '{updated_box_subfile_id}'")
    return updated_box_subfiles_ids


def sync_box_subfolders(local_subfolders, box_folder, box_subfolders):
    """"""
    # (0,1) Not Found in MADCBrain, Found in Box: Delete subfolder from box_folder
    deleted_box_subfolders_ids = delete_box_subfolders_not_found_in_local(local_subfolders, box_subfolders)
    print("\tDeleted subfolders IDs:", deleted_box_subfolders_ids)

    # (1,0) Found in MADCBrain, Not Found in Box: Create subfolder in box_folder
    created_box_subfolders_ids = create_box_subfolders_found_in_local(local_subfolders, box_folder, box_subfolders)
    print("\tCreated subfolders IDs:", created_box_subfolders_ids)

    return deleted_box_subfolders_ids, created_box_subfolders_ids


def sync_box_subfiles(local_subfiles, box_client, box_folder, box_subfiles):
    """"""
    # (0,1) Not Found in MADCBrain, Found in Box: Delete subfile from box_folder
    deleted_box_subfiles_ids = delete_box_subfiles_not_found_in_local(local_subfiles, box_subfiles)
    print("\tDeleted subfiles IDs:", deleted_box_subfiles_ids)

    # (1,0) Found in MADCBrain, Not Found in Box: Create subfile in box_folder
    created_box_subfiles_ids = create_box_subfiles_found_in_local(local_subfiles, box_folder, box_subfiles)
    print("\tCreated subfiles IDs:", created_box_subfiles_ids)

    # # (1,1) Found in MADCBrain, Found in Box: Update Box subfile with updated local subfile
    updated_box_subfiles_ids = update_box_subfiles_found_in_local(local_subfiles, box_client, box_folder, box_subfiles)
    print("\tUpdated subfiles IDs:", updated_box_subfiles_ids)

    return deleted_box_subfiles_ids, created_box_subfiles_ids, updated_box_subfiles_ids


###################
# Driver Function #

def walk_local_dir_tree_sync_contents(local_folder, box_client, box_folder, rgx_subfolders, rgx_subfiles):
    print("Box Folder ID:", box_folder.id)

    local_subitems = get_local_subitems(local_folder)
    box_subitems = get_box_subitems(box_client, box_folder)

    # Folders #
    local_subfolders = get_local_subfolders(local_subitems, rgx_subfolders)
    box_subfolders = get_box_subfolders(box_subitems)
    deleted_box_subfolders_ids, created_box_subfolders_ids = \
        sync_box_subfolders(local_subfolders, box_folder, box_subfolders)

    # Files #
    local_subfiles = get_local_subfiles(local_subitems, rgx_subfiles)
    box_subfiles = get_box_subfiles(box_subitems)
    deleted_box_subfiles_ids, created_box_subfiles_ids, updated_box_subfiles_ids = \
        sync_box_subfiles(local_subfiles, box_client, box_folder, box_subfiles)

    # Recurse Down #
    for local_subfolder in local_subfolders:
        corres_box_subfolder = get_corresponding_box_subfolder(local_subfolder, box_client, box_folder)
        walk_local_dir_tree_sync_contents(local_subfolder, box_client, corres_box_subfolder,
                                          rgx_subfolders, rgx_subfiles)
