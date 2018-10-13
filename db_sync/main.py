#!/usr/bin/env python3

from pathlib import Path
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import argparse
import gzip
import json
import logging
import ntpath
import os
import shutil
import subprocess

logging.getLogger().setLevel(logging.INFO)


class GoogleDriveClient:
    def __init__(self, remote_config, conf):
        gauth = GoogleAuth(settings_file=os.path.expanduser(conf['settings_file']))
        gauth.LocalWebserverAuth()

        self.drive = GoogleDrive(gauth)
        self.remote_folder = remote_config['folder']

    def _get_folder_id(self):
        file_list = self.drive.ListFile(
            {'q': "'root' in parents and trashed=false"}).GetList()
        for file1 in file_list:
            if file1['title'] == self.remote_folder:
                fid = file1['id']
                break
        else:
            folder_metadata = {
                'title' : self.remote_folder,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.drive.CreateFile(folder_metadata)
            folder.Upload()
            fid = folder['id']
        return fid

    def upload_file(self, file_str):
        folder_id = self._get_folder_id()
        file_name = ntpath.basename(file_str)

        file_list = self.drive.ListFile(
            {'q': f"'{folder_id}' in parents and trashed=false"}).GetList()

        file2 = self.drive.CreateFile(
            {"parents": [{'kind': 'drive#fileLink', 'id': folder_id}]})

        for current_file in file_list:
            if current_file in file_list:
                if current_file['title'] == file_name:
                    file2['id'] = current_file['id']
                    break

        file2.SetContentFile(file_str)
        file2['title'] = file_name
        file2.Upload()

    def download_file(self, file_str):
        folder_id = self._get_folder_id()
        file_name = ntpath.basename(file_str)
        file_list = self.drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
        for current_file in file_list:
            if current_file['title'] == file_name:
                current_file.GetContentFile(file_str)


class MySqlDbConf:
    def __init__(self, conf, db_conf, mode):
        db_conf = conf['dbs'][db_conf]
        self.username = db_conf['username']
        self.password = db_conf['password']
        self.hostname = db_conf['hostname']
        self.db_name = db_conf['db_name']
        self.dump_name = db_conf['dump_name']
        self.dump_path = db_conf['dump_path']
        self.port = str(db_conf['port'])
        self.mode = mode
        self.common_cmd = (
            f'-h {self.hostname} --port {self.port} '
            f'-u {self.username} -p{self.password} '
        )
        self.db_table_data_ignore = db_conf['db_table_data_ignore']
        self.remote_config = db_conf['remote_config']
        self.remote_client = GoogleDriveClient(
            remote_config=self.remote_config,
            conf=conf['remotes'][db_conf['remote']]
        )

    def _log_command(self, command_str):
        logging.info(f'Running: {command_str}')

    def _export(self):
        out_file = os.path.join(self.dump_path, f'{self.dump_name}.sql')
        with open(out_file, "wb", 0) as out:
            to_run = (
                f'mysqldump {self.common_cmd} '
                f' --add-drop-trigger --no-data {self.db_name} '
            )
            self._log_command(to_run)
            subprocess.run(to_run.split(), stdout=out, check=True)

            to_run = (
                f'mysqldump {self.common_cmd} '
                f' --add-drop-trigger --no-create-info '
            )
            for ignore_table in self.db_table_data_ignore:
                to_run = (
                    f'{to_run} --ignore-table={self.db_name}.{ignore_table} ')
            to_run = f' {to_run} {self.db_name}'
            self._log_command(to_run)
            subprocess.run(to_run.split(), stdout=out, check=True)

        out_file_compressed = f'{out_file}.gz'
        with open(out_file, 'rb') as f_in:
            with gzip.open(out_file_compressed, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # gd = GoogleDriveClient(remote_config=self.remote_config)
        self.remote_client.upload_file(out_file_compressed)

    def _import(self):
        out_file = os.path.join(self.dump_path, f'{self.dump_name}.sql')
        out_file_compressed = f'{out_file}.gz'

        # gd = GoogleDriveClient(remote_config=self.remote_config)
        self.remote_client.download_file(out_file_compressed)

        with gzip.open(out_file_compressed, 'rb') as f_in:
            with open(out_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        to_run = (
            f'mysql {self.common_cmd} '
            f' {self.db_name} '
        )

        subprocess.run(to_run.split(), stdin=open(out_file, 'r'))

    def sync(self):
        if self.mode == 'export':
            self._export()
        elif self.mode == 'import':
            self._import()
        else:
            raise Exception(f'Mode {self.mode} is invalid.')

def read_config():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    # config_file = os.path.join(script_dir, 'db_sync.json')
    config_file = os.path.join(Path.home(), '.config', 'db_sync.json')
    logging.info(f'Loading config: {config_file}')
    config = json.load(open(config_file, 'r'))
    return config


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('mode', type=str,
                        help='export|import')
    parser.add_argument('db', type=str,
                        help='name of db config')
    args = parser.parse_args()

    conf = read_config()

    thing = MySqlDbConf(conf, db_conf=args.db, mode=args.mode)
    thing.sync()


