import os
import re
import ummap_mri_sync_to_box_helpers as hlps


class DirEntryNode:
    """"""

    def __init__(self, dir_entry, depth=0):
        """

        :param dir_entry:
        :param depth:
        """
        self.dir_entry = dir_entry
        self.depth = depth
        self.child_dir_entry_node_folders = []
        self.child_dir_entry_node_files = []

    def add_child(self, dir_entry_node):
        """

        :param dir_entry_node:
        :return:
        """
        if dir_entry_node.dir_entry.is_dir():
            self.child_dir_entry_node_folders.append(dir_entry_node)
        if dir_entry_node.dir_entry.is_file():
            self.child_dir_entry_node_files.append(dir_entry_node)

    def remove_child(self, dir_entry_node):
        """

        :param dir_entry_node:
        :return:
        """
        if dir_entry_node.dir_entry.is_dir():
            self.child_dir_entry_node_folders = \
                [child for child in self.child_dir_entry_node_folders if child != dir_entry_node]
        elif dir_entry_node.dir_entry.is_file():
            self.child_dir_entry_node_files = \
                [child for child in self.child_dir_entry_node_files if child != dir_entry_node]

    def search_below_for_file(self, rgx_file=r'^i\d+\.MRDC\.\d+$'):
        """

        :param rgx_file:
        :return:
        """

        found_file = False

        for dir_entry_node_folder in self.child_folders:
            found_in_this_dir_entry_node_folder = dir_entry_node_folder.search_below_for_file(rgx_file)
            found_file = found_file or found_in_this_dir_entry_node_folder
            if found_file:  # once True, short circuit return
                return True

        for dir_entry_node_file in self.child_dir_entry_node_files:
            if re.match(rgx_file, dir_entry_node_file.dir_entry.name):
                return True

        return found_file

    def search_below_for_dicom_dataset_series_descrip(self, rgx_series_descrip=r'^t1sag.*$|^t2flairsag.*$'):
        """

        :param rgx_series_descrip:
        :return:
        """
        found_series_descrip = False

        for dir_entry_node_folder in self.child_dir_entry_node_folders:
            found_in_this_dir_entry_node_folder = \
                dir_entry_node_folder.search_below_for_dicom_dataset_series_descrip(rgx_series_descrip)
            found_series_descrip = found_series_descrip or found_in_this_dir_entry_node_folder
            if found_series_descrip:  # once True, short circuit return
                return True

        for dir_entry_node_file in self.child_dir_entry_node_files:
            dir_entry_node_dicom_dataset = hlps.get_local_dicom_dataset(dir_entry_node_file.dir_entry)
            if re.match(rgx_series_descrip, dir_entry_node_dicom_dataset.SeriesDescription):
                return True

        return found_series_descrip

    def prune_nodes_without_dicom_dataset_series_descrip(self, rgx_sequence):
        """

        :param rgx_sequence:
        :return:
        """
        for dir_entry_node_folder in self.child_dir_entry_node_folders:
            if dir_entry_node_folder.search_below_for_dicom_dataset_series_descrip(rgx_sequence):
                dir_entry_node_folder.prune_nodes_without_dicom_dataset_series_descrip(rgx_sequence)
            else:
                self.remove_child(dir_entry_node_folder)

    def build_tree_from_node(self, rgx_folder, rgx_file):
        """

        :param rgx_folder:
        :param rgx_file:
        :return:
        """
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
        """

        :return:
        """
        print("  " * self.depth + self.dir_entry.name)

        for dir_entry_node_folder in self.child_dir_entry_node_folders:  # depth-first
            dir_entry_node_folder.print_node()

        for dir_entry_node_file in self.child_dir_entry_node_files:
            print("  " * dir_entry_node_file.depth + dir_entry_node_file.dir_entry.name)

    def write_tree_object_items(self, box_folder, update_files=False, is_verbose=False):
        """

        :param box_folder:
        :param update_files:
        :param is_verbose:
        :return:
        """
        box_subitems = hlps.get_box_subitems(box_folder)
        box_subfolders = hlps.get_box_subfolders(box_subitems)
        box_subfiles = hlps.get_box_subfiles(box_subitems)

        self.remove_box_subfolders(box_subfolders, is_verbose)
        self.create_box_subfolders(box_folder, box_subfolders, update_files, is_verbose)
        self.create_box_subfiles(box_folder, box_subfiles, is_verbose)
        if update_files:
            self.update_box_subfiles(box_folder, box_subfiles, is_verbose)

    def create_box_subfolders(self, box_folder, box_subfolders, update_files, is_verbose=False):
        """

        :param box_folder:
        :param box_subfolders:
        :param update_files:
        :param is_verbose:
        :return:
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
                dir_entry_node_folder.print_subitem_action(box_subfolder, "Creating")
            dir_entry_node_folder.write_tree_object_items(box_subfolder, update_files, is_verbose)

        for dir_entry_node_folder in subfolders_in_treeobj_in_box:
            box_subfolder = hlps.get_corresponding_box_subfolder(dir_entry_node_folder.dir_entry, box_folder)
            dir_entry_node_folder.write_tree_object_items(box_subfolder, update_files, is_verbose)

    def remove_box_subfolders(self, box_subfolders, is_verbose):
        """"""
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
                      f"{hlps.clr_brd}Removed Box subFolder{hlps.clr_rst}",
                      f"'{box_subfolder_name}'",
                      f"{hlps.clr_brd}with ID{hlps.clr_rst}",
                      f"'{box_subfolder_id}'")

    def create_box_subfiles(self, box_folder, box_subfiles, is_verbose=False):
        """

        :param box_folder:
        :param box_subfiles:
        :param is_verbose:
        :return:
        """
        box_subfile_names = [box_subfile.name for box_subfile in box_subfiles]

        subfiles_in_treeobj_not_in_box = \
            [dir_entry_node_subfile for dir_entry_node_subfile in self.child_dir_entry_node_files
             if dir_entry_node_subfile.dir_entry.name not in box_subfile_names]  # filter

        for dir_entry_node_file in subfiles_in_treeobj_not_in_box:
            box_subfile = box_folder.upload(dir_entry_node_file.dir_entry.path, preflight_check=True)
            if is_verbose:
                dir_entry_node_file.print_subitem_action(box_subfile, "Creating")

    def update_box_subfiles(self, box_folder, box_subfiles, is_verbose=False):
        """

        :param box_folder:
        :param box_subfiles:
        :param is_verbose:
        :return:
        """
        box_subfile_names = [box_subfile.name for box_subfile in box_subfiles]

        subfiles_in_treeobj_in_box = \
            [dir_entry_node_subfile for dir_entry_node_subfile in self.child_dir_entry_node_files
             if dir_entry_node_subfile.dir_entry.name in box_subfile_names]  # filter

        for dir_entry_node_file in subfiles_in_treeobj_in_box:
            den_file_de = dir_entry_node_file.dir_entry
            corres_box_subfile = hlps.get_corresponding_box_subfile(den_file_de, box_folder)
            box_subfile = corres_box_subfile.update_contents(den_file_de.path, preflight_check=True)
            if is_verbose:
                dir_entry_node_file.print_subitem_action(box_subfile, "Updating")

    def print_subitem_action(self, box_subitem, action_str):
        """

        :param box_subitem:
        :param action_str:
        :return:
        """
        print("  " * self.depth +
              f"{hlps.clr_bgr}{action_str} sub{box_subitem.type.capitalize()}{hlps.clr_rst}",
              f"'{box_subitem.name}'",
              f"{hlps.clr_bgr}with ID{hlps.clr_rst}",
              f"'{box_subitem.id}'")
