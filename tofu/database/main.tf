resource "postgresql_role" "nextcloud" {
  name                = "manafishrov_nextcloud_app"
  login               = true
  password_wo         = var.nextcloud_db_password
  password_wo_version = var.nextcloud_db_password_version
}

resource "postgresql_database" "nextcloud" {
  name  = "manafishrov_nextcloud"
  owner = postgresql_role.nextcloud.name
}

resource "postgresql_grant" "nextcloud_revoke_public_database_access" {
  database    = postgresql_database.nextcloud.name
  role        = "public"
  object_type = "database"
  privileges  = []
}

resource "postgresql_grant" "nextcloud_connect" {
  database    = postgresql_database.nextcloud.name
  role        = postgresql_role.nextcloud.name
  object_type = "database"
  privileges  = ["CONNECT", "CREATE", "TEMPORARY"]
}
