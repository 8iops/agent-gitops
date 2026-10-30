# /proc/net/{tcp,tcp6}: return counts only, never address/socket identifiers.
$1 != "sl" {
  split($2, local_address, ":")
  if ($4 == "0A" && local_address[2] == "01BB") https++
  if ($4 == "0A" && local_address[2] == "1F90") management++
  if ($4 == "02") pending++
}
END { printf "{\"listen443\":%d,\"listen8080\":%d,\"synSent\":%d}", https, management, pending }
