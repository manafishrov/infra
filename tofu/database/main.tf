resource "postgresql_role" "nextcloud" {
  name                = "manafishrov_nextcloud_app"
  login               = true
  password_wo         = var.nextcloud_db_password
  password_wo_version = 1
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

resource "postgresql_role" "twenty" {
  name                = "manafishrov_twenty_app"
  login               = true
  password_wo         = var.twenty_db_password
  password_wo_version = 1
}

resource "postgresql_database" "twenty" {
  name  = "manafishrov_twenty"
  owner = postgresql_role.twenty.name
}

resource "postgresql_grant" "twenty_revoke_public_database_access" {
  database    = postgresql_database.twenty.name
  role        = "public"
  object_type = "database"
  privileges  = []
}

resource "postgresql_grant" "twenty_connect" {
  database    = postgresql_database.twenty.name
  role        = postgresql_role.twenty.name
  object_type = "database"
  privileges  = ["CONNECT", "CREATE", "TEMPORARY"]
}
