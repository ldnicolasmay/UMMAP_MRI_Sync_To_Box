##################
# Import Modules #

import re
import os.path
import pydicom
import functools
from boxsdk import JWTAuth, Client
from datetime import datetime
from pytz import timezone
from colored import fg, attr

###########
# Globals #

# A list of Box subitem fields to include with each item on retrieval
# https://opensource.box.com/box-python-sdk/tutorials/intro.html
box_folder_attrs = [
    "type",
    "id",
    # "sequence_id",
    # "etag",
    "name",
    # "created_at",
    "modified_at",
    # "description",
    "size",
    # "path_collection",
    # "created_by",
    # "modified_by",
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

# US Eastern timezone for comparing file timestamps
tz_east = timezone("US/Eastern")

#####################
# Print Color Setup #

clr_mgn = fg('magenta')
clr_cyn = fg('cyan')
clr_grn = fg('green')
clr_blu = fg('blue')
clr_bld = attr('bold')
clr_bgr = fg('green') + attr('bold')
clr_bor = fg('gold_1') + attr('bold')
clr_brd = fg('red') + attr('bold')
clr_rst = attr('reset')


######################
# Local OS Functions #


def get_local_subitems(local_folder):
    """Get a collection of all immediate folder items

    :param local_folder: A DirEntry folder whose contents we want to fetch
    :type  local_folder: DirEntry

    :return: A list of DirEntry folders
    :rtype: list[DirEntry]
    """
    items = []
    # fetch folder items and add subitems to list
    for item in os.scandir(local_folder):
        items.append(item)
    return items


def get_local_subfolders(local_subitems, regex_subfolder=None):
    """Filter for the DirEntry subfolders from DirEntry subitems

    :param local_subitems: A list of DirEntry objects
    :type  local_subitems: [DirEntry]
    :param regex_subfolder: A Regex by which to filter matching subfolder names
    :type  regex_subfolder: Regex, optional

    :return: A list of DirEntry folders
    :rtype: [DirEntry]
    """
    if regex_subfolder:
        filter_obj = filter(lambda local_subitem: os.DirEntry.is_dir(local_subitem) and
                                                  re.match(regex_subfolder, local_subitem.name),
                            local_subitems)
    else:
        filter_obj = filter(lambda local_subitem: os.DirEntry.is_dir(local_subitem), local_subitems)

    return list(filter_obj)


def get_local_subfiles(local_subitems, regex_subfile=None):
    """Filter for the DirEntry subfiles from DirEntry subitems

    :param local_subitems: A list of DirEntry objects
    :type  local_subitems: [DirEntry]
    :param regex_subfile: A Regex by which to filter matching subfile names
    :type  regex_subfile: Regex, optional

    :return: A list of DirEntry files
    :rtype: [DirEntry]
    """
    if regex_subfile:
        filter_obj = filter(lambda local_subitem: os.DirEntry.is_file(local_subitem) and
                                                  re.match(regex_subfile, local_subitem.name),
                            local_subitems)
    else:
        filter_obj = filter(lambda local_subitem: os.DirEntry.is_file(local_subitem), local_subitems)

    return list(filter_obj)


########################
# Box Client Functions #


def get_box_authenticated_client(box_json_config_path, is_verbose=False):
    """Get an authenticated Box client for a JWT service account

    :param box_json_config_path: A path to the JSON config file for your Box JWT app
    :type  box_json_config_path: str
    :param is_verbose: A flag for turning print statements on/off, optional
    :type  is_verbose: bool, optional

    :raises ValueError: if the box_json_config_path is empty or cannot be found

    :return: A Box client for the JWT service account
    :rtype: Client
    """
    if not os.path.isfile(box_json_config_path):
        raise ValueError(f"`box_json_config_path` must be a path to the JSON config file for your Box JWT app")
    auth = JWTAuth.from_settings_file(box_json_config_path)
    if is_verbose:
        print(f"{clr_blu}Authenticating...{clr_rst}")
    auth.authenticate_instance()
    return Client(auth)


def print_box_user_info(box_client):
    """Print the name and login of the current authenticated Box user

    :param box_client: An authenticated Box client
    :type  box_client: Client
    """
    user = box_client.user('me').get()
    print("")
    print("Authenticated User")
    print(f"Name: {user.name}")
    print(f"Login: {user.login}")


def get_box_subitems(box_folder, fields=box_folder_attrs):
    """Get a collection of all immediate subitems in Box Folder

    :param box_client: An authenticated Box client
    :type  box_client: Client
    :param box_folder: A Box Folder whose contents we want to fetch
    :type  box_folder: Folder
    :param fields: An optional list of Box subitem fields to include with each item
    :type  fields: list, optional

    :return: A list of Box Files and Folders (boxsdk.object.base_object)
    :rtype: list[Folder/File]
    """
    items = []
    # fetch folder items and add subfolders to list
    for item in box_folder.get_items(fields=fields):
        items.append(item)
    return items


def get_box_subfolders(box_subitems):
    """Filter for the Box subFolders from Box subitems

    :param box_subitems: A list of Box Files and Folders (boxsdk.object.base_object)
    :type  box_subitems: list[Folder/File]

    :return: A list of Box Folders
    :rtype: list[Folder]
    """
    return [box_subitem for box_subitem in box_subitems if box_subitem.type == "folder"]


def get_box_subfiles(box_subitems):
    """Filter for the Box subFiles from Box subitems

    :param box_subitems: A list of Box Files and Folders (boxsdk.object.base_object)
    :type  box_subitems: list[Folder/File]

    :return: A list of Box Files
    :rtype: list[File]
    """
    return [box_subitem for box_subitem in box_subitems if box_subitem.type == "file"]


def get_corresponding_box_subfolder(local_subfolder, box_folder):
    """Get box subfolder that corresponds BY NAME to local subfolder

    :param local_subfolder: A DirEntry subfolder whose corresponding Box subfolder we want to find
    :type  local_subfolder: DirEntry
    :param box_client: An authenticated Box Client
    :type  box_client: Client
    :param box_folder: A Box Folder whose contents may hold the corresponding Box subfolder
    :type  box_folder: Folder

    :return: A Box Folder we want to return
    :rtype: Folder
    """
    box_subitems = get_box_subitems(box_folder)
    box_subfolders = get_box_subfolders(box_subitems)
    box_subfolder_target = None
    for box_subfolder in box_subfolders:
        if local_subfolder.name == box_subfolder.name and local_subfolder.is_dir():
            box_subfolder_target = box_subfolder
    return box_subfolder_target


def get_corresponding_box_subfile(local_subfile, box_folder):
    """Get Box subFile that corresponds BY NAME to local subfile

    :param local_subfile: A DirEntry subfile whose corresponding Box subFile we want to find
    :type  local_subfile: DirEntry
    :param box_client: An authenticated Box Client
    :type  box_client: Client
    :param box_folder: A Box Folder whose contents may hold the corresponding Box subFile
    :type  box_folder: Folder

    :return: A Box File we want to return
    :rtype: File
    """
    box_subitems = get_box_subitems(box_folder)
    box_subfiles = get_box_subfiles(box_subitems)
    box_subfile_target = None
    for box_subfile in box_subfiles:
        if local_subfile.name == box_subfile.name and local_subfile.is_file():
            box_subfile_target = box_subfile
    return box_subfile_target


def delete_box_subfolders_not_found_in_local(local_subfolders, box_subfolders, is_verbose=False):
    """Delete Box subFolders that are not found in local subfolders

    :param local_subfolders: A list of DirEntry folders to sync Box against
    :type  local_subfolders: list[DirEntry]
    :param box_subfolders: A list of Box Folders to sync against local folders
    :type  box_subfolders: list[Folder]
    :param is_verbose: A flag for turning print statements on/off
    :type  is_verbose: bool, optional

    :return: A list of Box subFolder ID strings that were deleted
    :rtype: list[str]
    """
    local_subfolders_names = [local_subfolder.name for local_subfolder in local_subfolders]
    subfolders_not_in_local_in_box = \
        list(filter(lambda box_subfldr: box_subfldr.name not in local_subfolders_names, box_subfolders))
    deleted_box_subfolders_ids = []
    for box_subfolder in subfolders_not_in_local_in_box:
        box_subfolder_id, box_subfolder_name = box_subfolder.id, box_subfolder.name
        box_subfolder_deleted = box_subfolder.delete(recursive=True)
        if box_subfolder_deleted:
            deleted_box_subfolders_ids.append(box_subfolder_id)
            if is_verbose:
                print(f"  {clr_brd}Deleted subFolder{clr_rst}", f"'{box_subfolder_name}'",
                      f"{clr_brd}with ID{clr_rst}", f"'{box_subfolder_id}'")
    return deleted_box_subfolders_ids


def create_box_subfolders_found_in_local(local_subfolders, box_folder, box_subfolders, is_verbose=False):
    """Create new Box subFolders that are found in local subfolders

    :param local_subfolders: A list of DirEntry folders to sync Box against
    :type  local_subfolders: list[DirEntry]
    :param box_folder: A Box Folder to put new Box subFolder into
    :type  box_folder: Folder
    :param box_subfolders: A list of Box Folders to sync against local folders
    :type  box_subfolders: list[Folder]
    :param is_verbose: A flag for turning print statements on/off
    :type  is_verbose: bool, optional

    :return: A ist of Box subFolder ID strings that were created
    :rtype: list[str]
    """
    box_subfolders_names = [box_subfolder.name for box_subfolder in box_subfolders]
    subfolders_in_local_not_in_box = \
        list(filter(lambda localsubfolder: localsubfolder.name not in box_subfolders_names, local_subfolders))
    created_box_subfolders_ids = []
    for local_subfolder in subfolders_in_local_not_in_box:
        box_subfolder = box_folder.create_subfolder(local_subfolder.name)
        created_box_subfolders_ids.append(box_subfolder.id)
        if is_verbose:
            print(f"  {clr_bgr}Created subFolder{clr_rst}", f"'{box_subfolder.name}'",
                  f"{clr_bgr}with ID{clr_rst}", f"'{box_subfolder.id}'")
    return created_box_subfolders_ids


def delete_box_subfiles_not_found_in_local(local_subfiles, box_subfiles, is_verbose=False):
    """Delete Box subFiles that are not found in local subfiles

    :param local_subfiles: A list of DirEntry files to sync Box against
    :type  local_subfiles: list[DirEntry]
    :param box_subfiles: A list of Box Files to sync against local files
    :type  box_subfiles: list[File]
    :param is_verbose: An optional flag for turning print statements on/off
    :type  is_verbose: bool, optional

    :return: A list of Box subFile ID strings that were deleted
    :rtype: list[str]
    """
    local_subfiles_names = [local_subfile.name for local_subfile in local_subfiles]
    subfiles_not_in_local_in_box = \
        list(filter(lambda box_subfl: box_subfl.name not in local_subfiles_names, box_subfiles))
    deleted_box_subfiles_ids = []
    for box_subfile in subfiles_not_in_local_in_box:
        box_subfile_id, box_subfile_name = box_subfile.id, box_subfile.name
        box_subfile_deleted = box_subfile.delete()
        if box_subfile_deleted:
            deleted_box_subfiles_ids.append(box_subfile_id)
            if is_verbose:
                print(f"  {clr_brd}Deleted subFile{clr_rst}", f"'{box_subfile_name}'",
                      f"{clr_brd}with ID{clr_rst}", f"'{box_subfile_id}'")
    return deleted_box_subfiles_ids


def create_box_subfiles_found_in_local(local_subfiles, box_folder, box_subfiles, is_verbose=False):
    """Create new Box subFiles that are found in local subfiles

    :param local_subfiles: A list of DirEntry files to sync Box against
    :type  local_subfiles: list[DirEntry]
    :param box_folder: A parent Box Folder to put new Box subFiles into
    :type  box_folder: Folder
    :param box_subfiles: A list of Box Files to sync against local files
    :type  box_subfiles: list[File]
    :param is_verbose: An optional flag for turning print statements on/off
    :type  is_verbose: bool, optional

    :return: A list of Box subFile ID strings that were created
    :rtype: list[str]
    """
    box_subfiles_names = [box_subfile.name for box_subfile in box_subfiles]
    subfiles_in_local_not_in_box = \
        list(filter(lambda localsubfile: localsubfile.name not in box_subfiles_names, local_subfiles))
    created_box_subfiles_ids = []
    for local_subfile in subfiles_in_local_not_in_box:
        box_subfile = box_folder.upload(local_subfile.path, preflight_check=True)
        box_subfile_id = box_subfile.id
        created_box_subfiles_ids.append(box_subfile_id)
        if is_verbose:
            print(f"  {clr_bgr}Created subFile{clr_rst}", f"'{box_subfile.name}'",
                  f"{clr_bgr}with ID{clr_rst}", f"'{box_subfile_id}'")
    return created_box_subfiles_ids


def update_box_subfiles_found_in_local(local_subfiles, box_client, box_folder, box_subfiles, is_verbose=False):
    """Update existing Box subFiles that are found in--but are older than--local subfiles

    :param local_subfiles: A list of DirEntry files to sync Box against
    :type  local_subfiles: list[DirEntry]
    :param box_client: An authenticated Box client
    :type  box_client: Client
    :param box_folder: Parent Box Folder to put updated Box subFiles into
    :type  box_folder: Folder
    :param box_subfiles: A list of Box Files to sync against local files
    :type  box_subfiles: list[File]
    :param is_verbose: An optional flag for turning print statements on/off
    :type  is_verbose: bool, optional

    :return: List of Box subFile ID strings that were updated
    :rtype: list[str]
    """
    box_subfiles_names = [box_subfile.name for box_subfile in box_subfiles]
    local_subfiles_in_local_in_box = \
        list(filter(lambda localsubfile: localsubfile.name in box_subfiles_names, local_subfiles))
    updated_box_subfiles_ids = []
    for local_subfile in local_subfiles_in_local_in_box:
        corres_box_subfile = get_corresponding_box_subfile(local_subfile, box_folder)
        # Local subfile modified timestamp
        local_subfile_modified_psx = local_subfile.stat().st_mtime
        local_subfile_modified_dt = datetime.fromtimestamp(local_subfile_modified_psx, tz=tz_east)
        # Corresponding Box subFile modified timestamp
        corres_box_subfile_modified_str = corres_box_subfile.modified_at
        corres_box_subfile_modified_dt = datetime.fromisoformat(corres_box_subfile_modified_str)
        # Update corres_box_subfile with contents of more recent local_subfile
        if local_subfile_modified_dt > corres_box_subfile_modified_dt:
            updated_box_subfile = corres_box_subfile.update_contents(local_subfile.path, preflight_check=True)
            updated_box_subfile_id = updated_box_subfile.id
            updated_box_subfiles_ids.append(updated_box_subfile_id)
            if is_verbose:
                print(f"  {clr_bor}Updated subFile{clr_rst}", f"'{updated_box_subfile.name}'",
                      f"{clr_bor}with ID{clr_rst}", f"'{updated_box_subfile_id}'")
    return updated_box_subfiles_ids


def sync_box_subfolders(local_subfolders, box_folder, box_subfolders, is_verbose):
    """Run functions to sync Box subFolders

    :param local_subfolders: A list of DirEntry folders to sync Box against
    :type  local_subfolders: list[DirEntry]
    :param box_folder: A parent Box Folder to sync local folders in
    :type  box_folder: Folder
    :param box_subfolders: A list of Box Folders to sync against local folders
    :type  box_subfolders: list[Folder]
    :param is_verbose: An optional flag for turning print statements on/off
    :type  is_verbose: bool, optional

    :return: A tuple of lists of Box subFolder ID Strings that are deleted and created
    :rtype: (list[str], list[str])
    """
    # (0,1) Not Found in MADCBrain, Found in Box: Delete subfolder from box_folder
    deleted_box_subfolders_ids = \
        delete_box_subfolders_not_found_in_local(local_subfolders, box_subfolders, is_verbose)

    # (1,0) Found in MADCBrain, Not Found in Box: Create subfolder in box_folder
    created_box_subfolders_ids = \
        create_box_subfolders_found_in_local(local_subfolders, box_folder, box_subfolders, is_verbose)

    return deleted_box_subfolders_ids, created_box_subfolders_ids


def sync_box_subfiles(local_subfiles, box_client, box_folder, box_subfiles, update_subfiles=False, is_verbose=False):
    """Run functions to sync Box subFiles

    :param local_subfiles: A list of DirEntry files to sync Box against
    :type  local_subfiles: list[DirEntry]
    :param box_client: An authenticated Box client
    :type  box_client: Client
    :param box_folder: A parent Box Folder to sync local files in
    :type  box_folder: Folder
    :param box_subfiles: A list of Box Files to sync against local files
    :type  box_subfiles: list[File]
    :param update_subfiles: An optional flag for turning Box subFile updates on/off
    :type  update_subfiles: bool, optional
    :param is_verbose: An optional flag for turning print statements on/off
    :type  is_verbose: bool, optional

    :return: A tuple of lists of Box subFile ID Strings that are deleted, created, or updated
    :rtype: (list[str], list[str], list[str])
    """
    deleted_box_subfiles_ids, created_box_subfiles_ids, updated_box_subfiles_ids = None, None, None

    # (0,1) Not Found in MADCBrain, Found in Box: Delete subfile from box_folder
    deleted_box_subfiles_ids = \
        delete_box_subfiles_not_found_in_local(local_subfiles, box_subfiles, is_verbose)

    # (1,0) Found in MADCBrain, Not Found in Box: Create subfile in box_folder
    created_box_subfiles_ids = \
        create_box_subfiles_found_in_local(local_subfiles, box_folder, box_subfiles, is_verbose)

    # (1,1) Found in MADCBrain, Found in Box: Update Box subFile with updated local subfile
    if update_subfiles:
        updated_box_subfiles_ids = \
            update_box_subfiles_found_in_local(local_subfiles, box_client, box_folder, box_subfiles, is_verbose)

    return deleted_box_subfiles_ids, created_box_subfiles_ids, updated_box_subfiles_ids


###################
# Driver Function #

def walk_local_dir_tree_sync_contents(local_folder, box_client, box_folder,
                                      regex_subfolder=None, regex_subfile=None,
                                      update_subfiles=False, is_verbose=False):
    """Recursive driver function for syncing source local folder contents to a destination Box Folder

    :param local_folder: A DirEntry folder whose contents we want to fetch
    :type  local_folder: DirEntry
    :param box_client: An authenticated Box client
    :type  box_client: Client
    :param box_folder: A parent Box Folder to sync local files in
    :type  box_folder: Folder
    :param regex_subfolder: A Regex by which to filter matching subfolder names
    :type  regex_subfolder: Regex, optional
    :param regex_subfile: A Regex by which to filter matching subfile names
    :type  regex_subfile: Regex, optional
    :param update_subfiles: An optional flag for turning Box subFile updates on/off
    :type  update_subfiles: bool, optional
    :param is_verbose: An optional flag for turning print statements on/off
    :type  is_verbose: bool, optional
    """
    if is_verbose:
        print(f"{clr_mgn}Box Folder ID{clr_rst}:", box_folder.id)

    local_subitems = get_local_subitems(local_folder)
    # box_subitems = get_box_subitems(box_client, box_folder)
    box_subitems = get_box_subitems(box_folder)

    # Folders #
    local_subfolders = get_local_subfolders(local_subitems, regex_subfolder)
    box_subfolders = get_box_subfolders(box_subitems)
    deleted_box_subfolders_ids, created_box_subfolders_ids = \
        sync_box_subfolders(local_subfolders, box_folder, box_subfolders, is_verbose)

    # Files #
    local_subfiles = get_local_subfiles(local_subitems, regex_subfile)
    box_subfiles = get_box_subfiles(box_subitems)
    deleted_box_subfiles_ids, created_box_subfiles_ids, updated_box_subfiles_ids = \
        sync_box_subfiles(local_subfiles, box_client, box_folder, box_subfiles, update_subfiles, is_verbose)

    if is_verbose:
        print(f"  {clr_mgn}Deleted Box subFolders{clr_rst}:", deleted_box_subfolders_ids)
        print(f"  {clr_mgn}Created Box subFolders{clr_rst}:", created_box_subfolders_ids)
        print(f"  {clr_mgn}Deleted Box subFiles{clr_rst}:", deleted_box_subfiles_ids)
        print(f"  {clr_mgn}Created Box subFiles{clr_rst}:", created_box_subfiles_ids)
        print(f"  {clr_mgn}Updated Box subFiles{clr_rst}:", updated_box_subfiles_ids)

    # Recurse Down #
    for local_subfolder in local_subfolders:
        corres_box_subfolder = get_corresponding_box_subfolder(local_subfolder, box_folder)
        walk_local_dir_tree_sync_contents(local_subfolder, box_client, corres_box_subfolder,
                                          regex_subfolder, regex_subfile,
                                          update_subfiles, is_verbose)


###########################
# DICOM Handler Functions #

def get_local_dicom_dataset(dir_entry_file, rgx_dicom=re.compile(r'^i\d+\.MRDC\.\d+$')):
    """

    :param dir_entry_file: A DirEntry file of a DICOM dataset (where a DICOM "dataset" is a DICOM file)
    :type  dir_entry_file: DirEntry

    :return: A pydicom Dataset
    :rtype: pydicom Dataset
    """
    dicom_dataseries = pydicom.Dataset()
    if re.match(rgx_dicom, dir_entry_file.name):
        dicom_dataseries = pydicom.dcmread(dir_entry_file.path)

    return dicom_dataseries


def get_local_dicom_sequence(dir_entry_folder, rgx_dicom=re.compile(r'^i\d+\.MRDC\.\d+$'), presort=True):
    """

    :param dir_path: A DirEntry folder holding DICOM datasets that will be bundled as a DICOM Sequence
    :type  dir_path: DirEntry
    :param rgx_dicom: A Regex matching the DICOM filenames
    :type  rgx_dicom: Regex

    :return: pydicom Sequence of DICOM datasets (where a DICOM "dataset" is a DICOM file)
    :rtype: pydicom Sequence
    """
    subitems = get_local_subitems(dir_entry_folder)
    dicom_subfiles = get_local_subfiles(subitems, rgx_dicom)
    if presort:
        sorted_dicom_subfiles = sorted(dicom_subfiles, key=lambda f: int(f.name.split(".")[-1]))
        dicom_datasets = map(lambda dicom_subfile: get_local_dicom_dataset(dicom_subfile), sorted_dicom_subfiles)
    else:
        dicom_datasets = map(lambda dicom_subfile: get_local_dicom_dataset(dicom_subfile), dicom_subfiles)

    return pydicom.Sequence(dicom_datasets)


def get_local_dicom_sequence_series_descrip(dicom_sequence):
    """

    :param dicom_sequence: A pydicom Sequence of DICOM datasets (where a DICOM "dataset" is a DICOM file)
    :type  dicom_sequence: pydicom Sequence

    :return: A list of strings of the pydicom Sequence's Series Descriptions (e.g., "t1sag_208")
    :rtype: [str]
    """
    return list(map(lambda ds: ds.SeriesDescription, dicom_sequence))


def all_local_dicom_sequence_series_descrip_match(dicom_sequence, rgx_dicom):
    """

    :param dicom_sequence:
    :type  dicom_sequence:
    :param rgx_dicom:
    :type  rgx_dicom:

    :return:
    :rtype:
    """
    if len(dicom_sequence) == 0:
        return False
    series_descrip_map_obj = map(lambda dataset: dataset.SeriesDescription, dicom_sequence)
    bool_map_obj = map(lambda ser_desc: True if re.match(rgx_dicom, ser_desc) else False, series_descrip_map_obj)
    return functools.reduce(lambda x, y: x and y, bool_map_obj)
