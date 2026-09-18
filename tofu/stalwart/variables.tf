# These select PROXY parsing, not workload authorization. The consumer must
# restrict the listener to the exact smtp-edge namespace+app Cilium identity.
variable "smtp_edge_proxy_networks" {
  description = "Consumer pod CIDRs for the identity-restricted private PROXY listener."
  type        = list(string)
  validation {
    condition = length(var.smtp_edge_proxy_networks) > 0 && alltrue([
      for cidr in var.smtp_edge_proxy_networks :
      can(cidrhost(cidr, 0)) && try(tonumber(split("/", cidr)[1]) >= 8, false)
    ])
    error_message = "Provide valid explicit pod CIDRs with prefixes >= 8 (native Stalwart requirement); identity-based network policy is additionally required."
  }
}

# Leave false during preparation. See ACTIVATION.md before setting true.
variable "smtp_edge_activation_ready" {
  description = "Attest that BLOCKED_DOMAIN is Score 1000 at its existing ID, runtime safety/restart is verified, and private listener identity policy is installed. Enables import and new listeners; keep true after activation."
  type        = bool
  default     = false
  nullable    = false
}

# Separate the private trial from the domain-wide recipient-policy cutover.
variable "smtp_edge_exact_recipients_ready" {
  description = "Attest that old ingress is quiesced and both queues are drained before disabling implicit plus addresses. Keep true after cutover."
  type        = bool
  default     = false
  nullable    = false
}

variable "stalwart_endpoint" {
  description = "Internal Stalwart management endpoint."
  type        = string
  default     = "http://stalwart-internal.manafishrov-stalwart.svc.cluster.local:8080"
}
