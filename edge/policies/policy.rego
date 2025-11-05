package edge

default allow := false

# Allowed CPU arches
allowed_arches := {"arm64", "aarch64"}

# --- Policy 1: Image registry must be approved ---
deny contains msg if {
  not approved_registry
  msg := sprintf("Image registry %q is not approved. Allowed: %v",
                 [input.image.registry, data.allowed_registries])
}
approved_registry if {
  data.allowed_registries[_] == input.image.registry
}

# --- Policy 2: Host CPU must be ARM64 ---
deny contains msg if {
  not allowed_arches[input.host.arch]
  msg := sprintf("Host arch %q not allowed. Require arm64/aarch64.",
                 [input.host.arch])
}

# --- Policy 3: CLOUD_API_BASE must be allow-listed ---
deny contains msg if {
  not approved_cloud
  msg := sprintf("CLOUD_API_BASE %q is not approved. Allowed: %v",
                 [input.env.CLOUD_API_BASE, data.allowed_cloud_targets])
}
approved_cloud if {
  data.allowed_cloud_targets[_] == input.env.CLOUD_API_BASE
}

# Final decision: allow only if no denies
allow if { count(deny) == 0 }
