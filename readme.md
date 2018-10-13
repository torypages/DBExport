# db_sync

Not even close to polished.

Script to dump your db to remote storage and import it again.


```json
{
  "remotes": {
    "googledrive": {
      "type": "googledrive",
      "settings_file": "~/.config/db_sync_g_drive.yaml"
    }
  },
  "dbs": {
    "thm_dev": {
      "type": "mysql",
      "username": "root",
      "password": "pass",
      "hostname": "hostname",
      "db_name": "db",
      "port": 3306,
      "db_table_data_ignore": [
        "some_table_name"
      ],
      "dump_name": "db_dump",
      "dump_path": "/tmp/",
      "remote": "googledrive",
      "remote_config": {
        "folder": "db_backup"
      }
    }
  }
}

```

~/.config/db_sync_g_drive.yaml see pydrive conf, ex

```yaml
client_config_backend: settings
client_config:
  client_id: sadlkfsladkjsladkjf
  client_secret: asdlkfsadlfk

save_credentials: True
save_credentials_backend: file
save_credentials_file: /home/f/.config/db_sync_g_drive_credentials.json

get_refresh_token: True

oauth_scope:
  - https://www.googleapis.com/auth/drive.file
  - https://www.googleapis.com/auth/drive.install
  - https://www.googleapis.com/auth/drive.metadata
```
