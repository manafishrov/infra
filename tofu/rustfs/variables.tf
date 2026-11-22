variable "rustfs_endpoint" {
  type    = string
  default = "http://rustfs-svc.rustfs.svc.cluster.local:9000"
}

variable "rustfs_access_key" {
  type      = string
  sensitive = true
}

variable "rustfs_secret_key" {
  type      = string
  sensitive = true
}

variable "manafishrov_firmware_ci_secret_key" {
  type      = string
  sensitive = true
}
