import os
import re
import pydicom
from datetime import datetime
from pytz import timezone
from colored import fg, attr
from boxsdk import JWTAuth, Client

import ummap_mri_sync_to_box_helpers as hlps

###########
# Globals #

# US Eastern timezone for comparing file timestamps
tz_east = timezone("US/Eastern")

#####################
# Print Color Setup #

clr_bgr = fg('green') + attr('bold')
clr_bor = fg('gold_1') + attr('bold')
clr_brd = fg('red') + attr('bold')
clr_rst = attr('reset')


class DirEntryNode:
    """"""

    def __init__(self, dir_entry, depth=0):
        """Instantiation method for DirEntryNode class

        :param dir_entry: A DirEntry folder or file that is the primary data in the node
        :type  dir_entry: DirEntry
        :param depth: A depth of the node within its tree
        :type  depth: int
        """
        self.dir_entry = dir_entry
        self.depth = depth
        self.child_dir_entry_node_folders = []
        self.child_dir_entry_node_files = []

    def add_child(self, dir_entry_node):
        """Add a passed child DirEntryNode object to the calling DirEntryNode object

        :param dir_entry_node: A DirEntryNode object to add as a child
        :type  dir_entry_node: DirEntry Node
        """
        if dir_entry_node.dir_entry.is_dir():
            self.child_dir_entry_node_folders.append(dir_entry_node)
        if dir_entry_node.dir_entry.is_file():
            self.child_dir_entry_node_files.append(dir_entry_node)

    def remove_child(self, dir_entry_node):
        """Remove a padded child DirEntryNode object from the calling DirEntryNode object

        :param dir_entry_node: A DirEntryNode object to remove
        :type  dir_entry_node: DirEntryNode
        """
        if dir_entry_node.dir_entry.is_dir():
            self.child_dir_entry_node_folders = \
                [child for child in self.child_dir_entry_node_folders if child != dir_entry_node]
        elif dir_entry_node.dir_entry.is_file():
            self.child_dir_entry_node_files = \
                [child for child in self.child_dir_entry_node_files if child != dir_entry_node]

    def search_at_or_below_for_file(self, rgx_file=r'^i\d+\.MRDC\.\d+$'):
        """Search for a file matching the passed Regex at or below the calling DirEntryNode object

        :param rgx_file: A Regex for matching a file at or below the calling DirEntryNode object
        :type  rgx_file: Regex

        :return: A boolean whether a file is found at or below the calling DirEntryNode object
        :rtype: boolean
        """

        found_file = False

        for dir_entry_node_folder in self.child_dir_entry_node_folders:
            found_in_this_dir_entry_node_folder = dir_entry_node_folder.search_at_or_below_for_file(rgx_file)
            found_file = found_file or found_in_this_dir_entry_node_folder
            if found_file:  # once True, short circuit return
                return True

        for dir_entry_node_file in self.child_dir_entry_node_files:
            if re.match(rgx_file, dir_entry_node_file.dir_entry.name):
                return True

        return found_file

    def search_at_or_below_for_dicom_dataset_series_descrip(self, rgx_sequence=r'^t1sag.*$|^t2flairsag.*$'):
        """Search for a DICOM Dataset Series Description matching the passed Regex at or below the calling DirEntryNode
        object

        :param rgx_sequence: A Regex for matching a DICOM Dataset at or below the calling DirEntryNode object
        :type  rgx_sequence: Regex

        :return: A boolean whether a DICOM Dataset with passed Regex is found at or below calling DirEntryNode object
        :rtype: boolean
        """
        found_series_descrip = False

        for dir_entry_node_folder in self.child_dir_entry_node_folders:
            found_in_this_dir_entry_node_folder = \
                dir_entry_node_folder.search_at_or_below_for_dicom_dataset_series_descrip(rgx_sequence)
            found_series_descrip = found_series_descrip or found_in_this_dir_entry_node_folder
            if found_series_descrip:  # once True, short circuit return
                return True

        for dir_entry_node_file in self.child_dir_entry_node_files:
            dir_entry_node_dicom_dataset = dir_entry_node_file.get_local_dicom_dataset()
            if re.match(rgx_sequence, dir_entry_node_dicom_dataset.SeriesDescription):
                return True

        return found_series_descrip

    def prune_nodes_without_dicom_dataset_series_descrip(self, rgx_sequence):
        """Prune file nodes from calling DirEntryObject whose DICOM Data Series Descriptions don't match passed Regex

        :param rgx_sequence: A Regex for matching a DICOM Dataset at or below the calling DirEntryNode object
        :type  rgx_sequence: Regex
        """
        for dir_entry_node_folder in self.child_dir_entry_node_folders:
            if dir_entry_node_folder.search_at_or_below_for_dicom_dataset_series_descrip(rgx_sequence):
                dir_entry_node_folder.prune_nodes_without_dicom_dataset_series_descrip(rgx_sequence)
            else:
                self.remove_child(dir_entry_node_folder)

    def build_tree_from_node(self, rgx_folder, rgx_file):
        """Build a DirEntryNode tree by adding children folders and files to the calling DirEntryNode object

        :param rgx_folder: A Regex for filtering which folders to add as children to the calling DirEntryNode
        :type  rgx_folder: Regex
        :param rgx_file: A Regex for filtering which files to add as children to the calling DirEntryNode
        :type  rgx_file: Regex
        """
        if not re.match(r'^s\d{5}$', self.dir_entry.name):
            dir_entries = list(os.scandir(self.dir_entry))  # each item in called twice, so list is needed

            dir_entry_folders = [dir_entry for dir_entry in dir_entries
                                 if dir_entry.is_dir() and re.match(rgx_folder, dir_entry.name)]  # filter
            dir_entry_files = [dir_entry for dir_entry in dir_entries
                               if dir_entry.is_file() and re.match(rgx_file, dir_entry.name)]  # filter

            for dir_entry_folder in dir_entry_folders:
                new_dir_entry_node_folder = DirEntryNode(dir_entry_folder, depth=self.depth + 1)
                self.add_child(new_dir_entry_node_folder)
                new_dir_entry_node_folder.build_tree_from_node(rgx_folder, rgx_file)

            for dir_entry_file in dir_entry_files:
                new_dir_entry_node_file = DirEntryNode(dir_entry_file, depth=self.depth + 1)
                self.add_child(new_dir_entry_node_file)

        if re.match(r'^s\d{5}$', self.dir_entry.name):
            # Ensure there are fewer than 250 files in the directory; T1s and T2 Flairs have no more than ~200 files
            item_count = len(os.listdir(self.dir_entry.path))
            print(f"Number of items in {self.dir_entry.name}: {item_count}")

            if item_count < 250:
                dir_entries = list(os.scandir(self.dir_entry))  # each item in called twice, so list is needed

                dir_entry_folders = [dir_entry for dir_entry in dir_entries
                                     if dir_entry.is_dir() and re.match(rgx_folder, dir_entry.name)]  # filter
                dir_entry_files = [dir_entry for dir_entry in dir_entries
                                   if dir_entry.is_file() and re.match(rgx_file, dir_entry.name)]  # filter

                for dir_entry_folder in dir_entry_folders:
                    new_dir_entry_node_folder = DirEntryNode(dir_entry_folder, depth=self.depth + 1)
                    self.add_child(new_dir_entry_node_folder)
                    new_dir_entry_node_folder.build_tree_from_node(rgx_folder, rgx_file)

                for dir_entry_file in dir_entry_files:
                    new_dir_entry_node_file = DirEntryNode(dir_entry_file, depth=self.depth + 1)
                    self.add_child(new_dir_entry_node_file)

    def print_node(self):
        """Print a hierarchical representation of the calling DirEntryNode object"""
        print("  " * self.depth + self.dir_entry.name)

        for dir_entry_node_folder in self.child_dir_entry_node_folders:  # depth-first
            dir_entry_node_folder.print_node()

        for dir_entry_node_file in self.child_dir_entry_node_files:
            print("  " * dir_entry_node_file.depth + dir_entry_node_file.dir_entry.name)

    def sync_tree_object_items(self, box_folder, update_files=False, is_verbose=False):
        """Sync to box the folders and files in the tree composed of the calling DirEntry object

        :param box_folder: A Box Folder to sync the calling DirEntryNode object's contents into
        :type  box_folder: Box Folder
        :param update_files: A boolean flag for updating Box Files from source based on timestamps
        :type  box_folder: boolean
        :param is_verbose: A boolean flag for verbosity
        :type  is_verbose: boolean
        """
        box_subitems = hlps.get_box_subitems(box_folder)
        box_subfolders = hlps.get_box_subfolders(box_subitems)
        box_subfiles = hlps.get_box_subfiles(box_subitems)

        self.remove_box_subfolders(box_subfolders, is_verbose)
        self.remove_box_subfiles(box_subfiles, is_verbose)
        self.create_box_subfolders(box_folder, box_subfolders, update_files, is_verbose)
        self.create_box_subfiles(box_folder, box_subfiles, is_verbose)
        if update_files:
            self.update_box_subfiles(box_folder, box_subfiles, is_verbose)

    def create_box_subfolders(self, box_folder, box_subfolders, update_files, is_verbose=False):
        """Helper function: Create Box subFolders based on child folders in calling DirEntryNode object

        :param box_folder: A Box Folder to sync the calling DirEntryNode object's contents into
        :type  box_folder: Box Folder
        :param box_subfolders: A list of child Box Folders in the Box Folder corresponding to calling DirEntryNode obj.
        :type  box_subfolders: [Box Folder]
        :param update_files: A boolean flag for updating Box Files from source based on timestamps
        :type  box_folder: boolean
        :param is_verbose: A boolean flag for verbosity
        :type  is_verbose: boolean
        """
        box_subfolder_names = [box_subfolder.name for box_subfolder in box_subfolders]

        subfolders_in_treeobj_not_in_box = \
            [dir_entry_node_subfolder for dir_entry_node_subfolder in self.child_dir_entry_node_folders
             if dir_entry_node_subfolder.dir_entry.name not in box_subfolder_names]  # filter

        subfolders_in_treeobj_in_box = \
            [dir_entry_node_subfolder for dir_entry_node_subfolder in self.child_dir_entry_node_folders
             if dir_entry_node_subfolder.dir_entry.name in box_subfolder_names]  # filter

        for dir_entry_node_folder in subfolders_in_treeobj_not_in_box:  # depth-first
            box_subfolder = box_folder.create_subfolder(dir_entry_node_folder.dir_entry.name)
            if is_verbose:
                dir_entry_node_folder.print_subitem_action(box_subfolder, "Creating", clr_bgr)
            dir_entry_node_folder.sync_tree_object_items(box_subfolder, update_files, is_verbose)

        for dir_entry_node_folder in subfolders_in_treeobj_in_box:
            box_subfolder = hlps.get_corresponding_box_subfolder(dir_entry_node_folder.dir_entry, box_folder)
            dir_entry_node_folder.sync_tree_object_items(box_subfolder, update_files, is_verbose)

    def remove_box_subfolders(self, box_subfolders, is_verbose):
        """Helper function: Remove Box subFolders based on absent child folders in calling DirEntryNode object

        :param box_subfolders: A list of child Box Folders in Box Folder corresponding to calling DirEntryNode object
        :type  box_subfolders: [Box Folder]
        :param is_verbose: A boolean flag for verbosity
        :type  is_verbose: boolean
        """
        dir_entry_node_subfolder_names = \
            [dir_entry_node_subfolder.dir_entry.name for dir_entry_node_subfolder in self.child_dir_entry_node_folders]

        subfolders_in_box_not_in_treeobj = \
            [box_subfolder for box_subfolder in box_subfolders
             if box_subfolder.name not in dir_entry_node_subfolder_names]

        for box_subfolder in subfolders_in_box_not_in_treeobj:
            box_subfolder_id, box_subfolder_name = box_subfolder.id, box_subfolder.name
            box_subfolder_deleted = box_subfolder.delete(recursive=True)
            if box_subfolder_deleted and is_verbose:
                print("  " * (self.depth + 1) +
                      f"{clr_brd}Removed Box subFolder{clr_rst}",
                      f"'{box_subfolder_name}'",
                      f"{clr_brd}with ID{clr_rst}",
                      f"'{box_subfolder_id}'")

    def create_box_subfiles(self, box_folder, box_subfiles, is_verbose=False):
        """

        :param box_folder: A Box Folder to sync the calling DirEntryNode object's contents into
        :type  box_folder: Box Folder
        :param box_subfiles: A list of child Box Files in the Box Folder corresponding to calling DirEntryNode object
        :param is_verbose: A boolean flag for verbosity
        :type  is_verbose: boolean
        """
        box_subfile_names = [box_subfile.name for box_subfile in box_subfiles]

        subfiles_in_treeobj_not_in_box = \
            [dir_entry_node_subfile for dir_entry_node_subfile in self.child_dir_entry_node_files
             if dir_entry_node_subfile.dir_entry.name not in box_subfile_names]  # filter

        for dir_entry_node_file in subfiles_in_treeobj_not_in_box:
            box_subfile = box_folder.upload(dir_entry_node_file.dir_entry.path, preflight_check=True)
            if is_verbose:
                dir_entry_node_file.print_subitem_action(box_subfile, "Creating", clr_bgr)

    def update_box_subfiles(self, box_folder, box_subfiles, is_verbose=False):
        """Helper function: Update Box subFiles based on timestamps of child files in calling DirEntryNode object

        :param box_folder: A Box Folder to sync the calling DirEntryNode object's contents into
        :type  box_folder: Box Folder
        :param box_subfiles: A list of child Box Files in the Box Folder corresponding to calling DirEntryNode object
        :type  box_subfiles: [Box File]
        :param is_verbose: A boolean flag for verbosity
        :type  is_verbose: boolean
        """
        box_subfile_names = [box_subfile.name for box_subfile in box_subfiles]

        subfiles_in_treeobj_in_box = \
            [dir_entry_node_subfile for dir_entry_node_subfile in self.child_dir_entry_node_files
             if dir_entry_node_subfile.dir_entry.name in box_subfile_names]  # filter

        for dir_entry_node_file in subfiles_in_treeobj_in_box:
            den_file_de = dir_entry_node_file.dir_entry
            corres_box_subfile = hlps.get_corresponding_box_subfile(den_file_de, box_folder)

            # Local subfile modified timestamp
            den_file_de_modified_psx = den_file_de.stat().st_mtime
            den_file_de_modified_dt = datetime.fromtimestamp(den_file_de_modified_psx, tz=tz_east)

            # Corresponding Box subFile modified timestamp
            corres_box_subfile_modified_str = corres_box_subfile.modified_at
            corres_box_subfile_modified_dt = datetime.fromisoformat(corres_box_subfile_modified_str)

            # Update corres_box_subfile with contents of more recent local_subfile
            if den_file_de_modified_dt > corres_box_subfile_modified_dt:
                box_subfile = corres_box_subfile.update_contents(den_file_de.path, preflight_check=True)
                if is_verbose:
                    dir_entry_node_file.print_subitem_action(box_subfile, "Updating", clr_bor)

    def remove_box_subfiles(self, box_subfiles, is_verbose):
        """Helper function: Remove Box subFiles based on absent child files in calling DirEntryNode object

        :param box_subfiles: A list of child Box Files in Box Folder corresponding to calling DirEntryNode object
        :type  box_subfiles: [Box File]
        :param is_verbose: A boolean flag for verbosity
        :type  is_verbose: boolean
        """
        dir_entry_node_subfile_names = \
            [dir_entry_node_subfile.dir_entry.name for dir_entry_node_subfile in self.child_dir_entry_node_files]

        subfiles_in_box_not_in_treeobj = \
            [box_subfile for box_subfile in box_subfiles
             if box_subfile.name not in dir_entry_node_subfile_names]

        for box_subfile in subfiles_in_box_not_in_treeobj:
            box_subfile_id, box_subfile_name = box_subfile.id, box_subfile.name
            box_subfile_deleted = box_subfile.delete()
            if box_subfile_deleted and is_verbose:
                print("  " * (self.depth + 1) +
                      f"{clr_brd}Removed Box subFile{clr_rst}",
                      f"'{box_subfile_name}'",
                      f"{clr_brd}with ID{clr_rst}",
                      f"'{box_subfile_id}'")

    def print_subitem_action(self, box_subitem, action_str, color):
        """Helper function: Print info about action taken on Box subItem

        :param box_subitem: A Box Folder or Box File to print info about
        :param action_str: A str of what action is being taken
        :param color: A colored module color for highlighting stdout print
        """
        print("  " * self.depth +
              f"{color}{action_str} sub{box_subitem.type.capitalize()}{clr_rst}",
              f"'{box_subitem.name}'",
              f"{color}with ID{clr_rst}",
              f"'{box_subitem.id}'")

    ###########################
    # DICOM Handler Functions #

    def get_local_dicom_dataset(self, rgx_dicom=re.compile(r'^i\d+\.MRDC\.\d+$')):
        """"Get the DICOM Dataset from the file that matches the provided Regex

        :param rgx_dicom: A Regex for matching a DICOM Dataset file
        :type  rgx_dicom: Regex

        :return: A pydicom Dataset
        :rtype: pydicom Dataset
        """
        dicom_dataseries = pydicom.Dataset()
        if re.match(rgx_dicom, self.dir_entry.name):
            dicom_dataseries = pydicom.dcmread(self.dir_entry.path)

        return dicom_dataseries
