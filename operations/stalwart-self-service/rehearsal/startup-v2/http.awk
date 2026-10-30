/^[0-5][0-9][0-9]$/ { counts[$0]++ }
END {
  printf "{"
  separator=""
  for (code in counts) {
    printf "%s\"%s\":%d", separator, code, counts[code]
    separator=","
  }
  printf "}"
}
