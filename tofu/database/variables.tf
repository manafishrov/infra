variable "pg_admin_user" {
  description = "Shared Postgres admin user"
  type        = string
  sensitive   = true
}

variable "pg_admin_password" {
  description = "Shared Postgres admin password"
  type        = string
  sensitive   = true
}

variable "nextcloud_db_password" {
  description = "Nextcloud application role password"
  type        = string
  sensitive   = true
}

variable "twenty_db_password" {
  description = "Twenty CRM application role password"
  type        = string
  sensitive   = true
}
